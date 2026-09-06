import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import CaptureSession, Card, Event, SheetSyncRecord
from app.services.sheets.google import GoogleSheetsGateway
from app.services.sheets.types import SheetGateway, SheetSyncError, SyncRunCounts


def sheet_alias(spreadsheet_id: str | None) -> str:
    if not spreadsheet_id:
        return "not-configured"
    return hashlib.sha256(spreadsheet_id.encode("utf-8")).hexdigest()[:16]


def google_sheets_configured(settings: Settings) -> bool:
    credentials = settings.google_application_credentials
    return bool(
        settings.google_sheets_enabled
        and settings.google_sheet_id
        and credentials
        and Path(credentials).is_file()
    )


def build_sheet_gateway(settings: Settings) -> SheetGateway:
    if not settings.google_sheets_enabled:
        raise SheetSyncError("Google Sheets synchronization is disabled.")
    if not settings.google_sheet_id:
        raise SheetSyncError("A Google Sheet ID has not been configured.")
    if not settings.google_application_credentials:
        raise SheetSyncError("Google service-account credentials have not been configured.")
    return GoogleSheetsGateway(
        spreadsheet_id=settings.google_sheet_id,
        tab_name=settings.google_sheet_tab_name,
        credentials_path=settings.google_application_credentials,
    )


def mark_card_for_sync(db: Session, card: Card, settings: Settings) -> SheetSyncRecord:
    alias = sheet_alias(settings.google_sheet_id)
    record = db.scalar(select(SheetSyncRecord).where(SheetSyncRecord.card_id == card.id))
    if record is None:
        record = SheetSyncRecord(
            card_id=card.id,
            sheet_id_hash_or_alias=alias,
            record_id=str(card.id),
            status="NOT_REQUIRED",
        )
        db.add(record)
    elif record.sheet_id_hash_or_alias != alias:
        record.sheet_id_hash_or_alias = alias
        record.sheet_row_number = None
        record.last_synced_payload_hash = None
        record.synced_at = None

    should_sync = card.status == "APPROVED"
    is_synced_removal = (
        card.status == "REMOVED"
        and card.status_before_removal == "APPROVED"
        and bool(record.sheet_row_number or record.last_synced_payload_hash)
    )
    record.status = (
        "PENDING"
        if settings.google_sheets_enabled and (should_sync or is_synced_removal)
        else "NOT_REQUIRED"
    )
    record.last_error_safe = None
    return record


def queue_existing_approved_cards(db: Session, settings: Settings) -> int:
    cards = db.scalars(select(Card).where(Card.status == "APPROVED"))
    count = 0
    for card in cards:
        mark_card_for_sync(db, card, settings)
        count += 1
    return count


def sheet_row_for_card(db: Session, card: Card) -> list[str]:
    if card.status == "REMOVED":
        return [str(card.id), "", "", "", "", "", "", card.updated_at.isoformat()]
    event = db.get(Event, card.event_id)
    capture_session = db.get(CaptureSession, card.session_id)
    timestamp = card.approved_at or card.captured_at
    return [
        str(card.id),
        timestamp.isoformat(),
        event.title if event else "Unknown event",
        event.event_type if event else "OTHER",
        capture_session.name if capture_session else "Unknown session",
        card.final_type or "UNKNOWN",
        card.final_text or "",
        card.updated_at.isoformat(),
    ]


def _payload_hash(values: list[str]) -> str:
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_failure_message(exc: Exception) -> str:
    if isinstance(exc, SheetSyncError):
        return str(exc)[:500]
    return "Google Sheets could not be updated. Retry after checking the connection."


def process_pending_syncs(
    db: Session,
    gateway: SheetGateway,
    *,
    card_ids: set[uuid.UUID] | None = None,
    limit: int = 100,
) -> SyncRunCounts:
    statement = select(SheetSyncRecord).where(
        SheetSyncRecord.status.in_(["PENDING", "ERROR"])
    )
    if card_ids:
        statement = statement.where(SheetSyncRecord.card_id.in_(card_ids))
    records = list(db.scalars(statement.order_by(SheetSyncRecord.updated_at).limit(limit)))
    if not records:
        return SyncRunCounts()

    try:
        gateway.ensure_schema()
    except Exception as exc:
        now = datetime.now(UTC)
        message = _safe_failure_message(exc)
        for record in records:
            record.status = "ERROR"
            record.attempt_count += 1
            record.last_attempt_at = now
            record.last_error_safe = message
        db.commit()
        return SyncRunCounts(attempted=len(records), failed=len(records))

    succeeded = 0
    failed = 0
    for record in records:
        card = db.get(Card, record.card_id)
        if card is None:
            record.status = "NOT_REQUIRED"
            db.commit()
            continue
        values = sheet_row_for_card(db, card)
        payload_hash = _payload_hash(values)
        record.attempt_count += 1
        record.last_attempt_at = datetime.now(UTC)
        try:
            row_number = gateway.find_record_row(record.record_id, record.sheet_row_number)
            if record.last_synced_payload_hash == payload_hash and row_number is not None:
                record.sheet_row_number = row_number
            elif row_number is None:
                record.sheet_row_number = gateway.append_row(values)
            else:
                gateway.update_row(row_number, values)
                record.sheet_row_number = row_number
            record.last_synced_payload_hash = payload_hash
            record.status = "SYNCED"
            record.last_error_safe = None
            record.synced_at = datetime.now(UTC)
            succeeded += 1
        except Exception as exc:
            record.status = "ERROR"
            record.last_error_safe = _safe_failure_message(exc)
            failed += 1
        db.commit()
    return SyncRunCounts(attempted=len(records), succeeded=succeeded, failed=failed)
