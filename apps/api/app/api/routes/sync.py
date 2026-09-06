import csv
import io
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.database import get_db
from app.models import Card, SheetSyncRecord
from app.schemas.sync import SheetSyncRunRead, SheetSyncStatusRead, SheetSyncVerifyRead
from app.services.sheets.sync import (
    build_sheet_gateway,
    google_sheets_configured,
    mark_card_for_sync,
    process_pending_syncs,
    queue_existing_approved_cards,
    sheet_row_for_card,
)
from app.services.sheets.types import SHEET_HEADERS, SheetGateway, SheetSyncError, SyncRunCounts

router = APIRouter(tags=["sync"])


def _gateway(request: Request) -> SheetGateway:
    injected = getattr(request.app.state, "sheet_gateway", None)
    if injected is not None:
        return injected
    return build_sheet_gateway(request.app.state.settings)


def _is_configured(request: Request) -> bool:
    return bool(
        getattr(request.app.state, "sheet_gateway", None)
        or google_sheets_configured(request.app.state.settings)
    )


def _status(db: Session, request: Request) -> SheetSyncStatusRead:
    settings = request.app.state.settings
    counts = dict(
        db.execute(
            select(SheetSyncRecord.status, func.count())
            .group_by(SheetSyncRecord.status)
        ).all()
    )
    eligible = db.scalar(
        select(func.count()).select_from(Card).where(Card.status == "APPROVED")
    )
    unqueued_eligible = db.scalar(
        select(func.count())
        .select_from(Card)
        .outerjoin(SheetSyncRecord, SheetSyncRecord.card_id == Card.id)
        .where(
            Card.status == "APPROVED",
            (SheetSyncRecord.id.is_(None)) | (SheetSyncRecord.status == "NOT_REQUIRED"),
        )
    )
    last_error = db.scalar(
        select(SheetSyncRecord.last_error_safe)
        .where(SheetSyncRecord.status == "ERROR")
        .order_by(SheetSyncRecord.updated_at.desc())
        .limit(1)
    )
    spreadsheet_url = (
        f"https://docs.google.com/spreadsheets/d/{settings.google_sheet_id}/edit"
        if settings.google_sheet_id
        else None
    )
    return SheetSyncStatusRead(
        enabled=settings.google_sheets_enabled,
        configured=_is_configured(request),
        tab_name=settings.google_sheet_tab_name,
        spreadsheet_url=spreadsheet_url,
        eligible_cards=eligible or 0,
        pending=counts.get("PENDING", 0)
        + ((unqueued_eligible or 0) if settings.google_sheets_enabled else 0),
        synced=counts.get("SYNCED", 0),
        errors=counts.get("ERROR", 0),
        last_error=last_error,
    )


def _require_enabled_and_configured(request: Request) -> None:
    if not request.app.state.settings.google_sheets_enabled:
        raise api_error(
            409,
            "GOOGLE_SHEETS_DISABLED",
            "Google Sheets sync is disabled. CSV export is still available.",
        )
    if not _is_configured(request):
        raise api_error(
            409,
            "GOOGLE_SHEETS_NOT_CONFIGURED",
            "Add the Sheet ID and service-account credentials before syncing.",
        )


@router.get("/api/v1/sync/status", response_model=SheetSyncStatusRead)
def get_sync_status(request: Request, db: Session = Depends(get_db)) -> SheetSyncStatusRead:
    return _status(db, request)


@router.post("/api/v1/sync/verify", response_model=SheetSyncVerifyRead)
def verify_sync_connection(request: Request) -> SheetSyncVerifyRead:
    _require_enabled_and_configured(request)
    try:
        _gateway(request).ensure_schema()
    except SheetSyncError as exc:
        raise api_error(409, "GOOGLE_SHEETS_UNAVAILABLE", str(exc)) from exc
    return SheetSyncVerifyRead(ready=True, message="Google Sheet connection is ready.")


def _run_response(
    db: Session,
    request: Request,
    counts: SyncRunCounts,
) -> SheetSyncRunRead:
    return SheetSyncRunRead(
        **_status(db, request).model_dump(),
        attempted=counts.attempted,
        succeeded=counts.succeeded,
        failed=counts.failed,
    )


@router.post("/api/v1/sync/retry", response_model=SheetSyncRunRead)
def retry_all_syncs(request: Request, db: Session = Depends(get_db)) -> SheetSyncRunRead:
    _require_enabled_and_configured(request)
    queue_existing_approved_cards(db, request.app.state.settings)
    db.commit()
    counts = process_pending_syncs(db, _gateway(request))
    return _run_response(db, request, counts)


@router.post("/api/v1/sync/cards/{card_id}/retry", response_model=SheetSyncRunRead)
def retry_card_sync(
    card_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> SheetSyncRunRead:
    _require_enabled_and_configured(request)
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    if card.status != "APPROVED" and not (
        card.status == "REMOVED" and card.status_before_removal == "APPROVED"
    ):
        raise api_error(409, "CARD_NOT_SYNCABLE", "Only approved cards can be synced.")
    mark_card_for_sync(db, card, request.app.state.settings)
    db.commit()
    counts = process_pending_syncs(db, _gateway(request), card_ids={card.id}, limit=1)
    return _run_response(db, request, counts)


@router.get("/api/v1/export/cards.csv")
def export_cards_csv(db: Session = Depends(get_db)) -> Response:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(SHEET_HEADERS)
    cards = db.scalars(
        select(Card).where(Card.status == "APPROVED").order_by(Card.approved_at, Card.id)
    )
    for card in cards:
        writer.writerow(sheet_row_for_card(db, card))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="career-cards.csv"'},
    )
