import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.database import get_db
from app.models import CaptureSession, Card, CardRevision, Event, OCRAttempt
from app.schemas.cards import CardApprove, CardEdit, CardRead, CardRevisionRead
from app.schemas.common import CardStatus
from app.services.ocr import OCRContext, OCRProviderError
from app.services.sheets.sync import mark_card_for_sync
from app.services.vision import VisionError, process_card_image

router = APIRouter(tags=["cards"])
MAX_IMAGE_BYTES = 12 * 1024 * 1024


def _card_read(card: Card) -> CardRead:
    return CardRead(
        id=card.id,
        event_id=card.event_id,
        session_id=card.session_id,
        sequence_number=card.sequence_number,
        status=card.status,
        suggested_type=card.suggested_type,
        final_type=card.final_type,
        raw_ocr=card.raw_ocr,
        final_text=card.final_text,
        ocr_confidence=float(card.ocr_confidence) if card.ocr_confidence is not None else None,
        ocr_provider=card.ocr_provider,
        ocr_model=card.ocr_model,
        was_edited=card.was_edited,
        has_image=bool(card.normalized_image_storage_key or card.image_storage_key),
        captured_at=card.captured_at,
        approved_at=card.approved_at,
        removed_at=card.removed_at,
        removed_reason=card.removed_reason,
        sync_status=(card.sheet_sync_record.status if card.sheet_sync_record else "NOT_REQUIRED"),
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


@router.post("/api/v1/sessions/{session_id}/cards", response_model=CardRead, status_code=201)
async def create_card(
    session_id: uuid.UUID,
    request: Request,
    image: UploadFile = File(...),
    mock_text: str | None = Form(None),
    db: Session = Depends(get_db),
) -> CardRead:
    capture_session = db.get(CaptureSession, session_id)
    if capture_session is None:
        raise api_error(404, "SESSION_NOT_FOUND", "Capture session not found.")
    if capture_session.status != "IN_PROGRESS":
        raise api_error(409, "SESSION_NOT_ACTIVE", "Reopen the session before capturing cards.")
    if not (image.content_type or "").startswith("image/"):
        raise api_error(415, "INVALID_IMAGE_TYPE", "Upload a JPEG, PNG, or WebP image.")
    content = await image.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise api_error(413, "INVALID_IMAGE_SIZE", "Image must be between 1 byte and 12 MB.")
    try:
        vision = process_card_image(content)
    except VisionError as exc:
        raise api_error(422, "INVALID_IMAGE", str(exc)) from exc

    sequence = db.scalar(
        select(func.max(Card.sequence_number)).where(Card.session_id == session_id)
    )
    card = Card(
        event_id=capture_session.event_id,
        session_id=session_id,
        sequence_number=(sequence or 0) + 1,
        status="PROCESSING",
    )
    db.add(card)
    db.flush()

    settings = request.app.state.settings
    image_dir = Path(settings.card_image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(image.filename or "capture.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    stored_name = f"{card.id}{suffix}"
    (image_dir / stored_name).write_bytes(content)
    card.image_storage_key = stored_name
    normalized_name = f"{card.id}-normalized.jpg"
    (image_dir / normalized_name).write_bytes(vision.normalized_image)
    card.normalized_image_storage_key = normalized_name

    started = time.perf_counter()
    provider = request.app.state.ocr_provider
    try:
        event = db.get(Event, capture_session.event_id)
        result = await provider.extract(
            vision.ocr_image,
            OCRContext(event_type=event.event_type if event else None, fixture_text=mock_text),
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        card.status = "NEEDS_REVIEW"
        card.raw_ocr = result.raw_text
        card.final_text = result.raw_text
        card.suggested_type = result.suggested_type
        card.final_type = result.suggested_type
        card.ocr_confidence = result.confidence
        card.ocr_provider = result.provider
        card.ocr_model = result.model
        db.add(
            OCRAttempt(
                card_id=card.id,
                attempt_number=1,
                provider=result.provider,
                model=result.model,
                raw_text=result.raw_text,
                suggested_type=result.suggested_type,
                confidence=result.confidence,
                latency_ms=latency_ms,
                provider_metadata={**result.metadata, "vision": vision.metrics},
            )
        )
    except OCRProviderError as exc:
        card.status = "OCR_FAILED"
        card.suggested_type = "UNKNOWN"
        card.final_type = "UNKNOWN"
        card.ocr_provider = provider.provider_id
        db.add(
            OCRAttempt(
                card_id=card.id,
                attempt_number=1,
                provider=provider.provider_id,
                error_code="OCR_FAILED",
                error_message_safe=str(exc),
                provider_metadata={"vision": vision.metrics},
            )
        )
    except Exception:
        card.status = "OCR_FAILED"
        card.suggested_type = "UNKNOWN"
        card.final_type = "UNKNOWN"
        card.ocr_provider = provider.provider_id
        db.add(
            OCRAttempt(
                card_id=card.id,
                attempt_number=1,
                provider=provider.provider_id,
                error_code="OCR_FAILED",
                error_message_safe="The OCR provider failed unexpectedly.",
                provider_metadata={"vision": vision.metrics},
            )
        )

    capture_session.last_activity_at = datetime.now(UTC)
    db.commit()
    db.refresh(card)
    return _card_read(card)


@router.get("/api/v1/cards/{card_id}", response_model=CardRead)
def get_card(card_id: uuid.UUID, db: Session = Depends(get_db)) -> CardRead:
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    return _card_read(card)


@router.patch("/api/v1/cards/{card_id}", response_model=CardRead)
def edit_approved_card(
    card_id: uuid.UUID,
    payload: CardEdit,
    request: Request,
    db: Session = Depends(get_db),
) -> CardRead:
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    if card.status != "APPROVED":
        raise api_error(
            409,
            "CARD_NOT_APPROVED",
            "Only approved cards can be edited from session history.",
        )

    final_text = payload.final_text.strip()
    if not final_text:
        raise api_error(422, "EMPTY_FINAL_TEXT", "Enter the card response before saving.")
    final_type = payload.final_type.value
    if card.final_text == final_text and card.final_type == final_type:
        return _card_read(card)

    revision_number = db.scalar(
        select(func.max(CardRevision.revision_number)).where(CardRevision.card_id == card.id)
    )
    db.add(
        CardRevision(
            card_id=card.id,
            revision_number=(revision_number or 0) + 1,
            previous_final_type=card.final_type or "UNKNOWN",
            previous_final_text=card.final_text or "",
            new_final_type=final_type,
            new_final_text=final_text,
            reason=payload.reason.strip() if payload.reason and payload.reason.strip() else None,
        )
    )
    card.final_type = final_type
    card.final_text = final_text
    card.was_edited = final_text != (card.raw_ocr or "") or final_type != card.suggested_type
    capture_session = db.get(CaptureSession, card.session_id)
    if capture_session:
        capture_session.last_activity_at = datetime.now(UTC)
    mark_card_for_sync(db, card, request.app.state.settings)
    db.commit()
    db.refresh(card)
    return _card_read(card)


@router.get(
    "/api/v1/cards/{card_id}/revisions",
    response_model=list[CardRevisionRead],
)
def list_card_revisions(
    card_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[CardRevision]:
    if db.get(Card, card_id) is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    return list(
        db.scalars(
            select(CardRevision)
            .where(CardRevision.card_id == card_id)
            .order_by(CardRevision.revision_number.desc())
        )
    )


@router.get("/api/v1/cards/{card_id}/image")
def get_card_image(card_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    storage_key = card.normalized_image_storage_key or card.image_storage_key
    if not storage_key:
        raise api_error(404, "CARD_IMAGE_NOT_RETAINED", "Card image is no longer retained.")
    path = Path(request.app.state.settings.card_image_dir) / storage_key
    if not path.is_file():
        raise api_error(404, "CARD_IMAGE_MISSING", "Card image is unavailable.")
    return FileResponse(path)


@router.get("/api/v1/sessions/{session_id}/cards", response_model=list[CardRead])
def list_cards(
    session_id: uuid.UUID,
    status: CardStatus | None = Query(None),
    include_removed: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[CardRead]:
    statement = select(Card).where(Card.session_id == session_id)
    if status:
        statement = statement.where(Card.status == status.value)
    elif not include_removed:
        statement = statement.where(Card.status != "REMOVED")
    cards = db.scalars(statement.order_by(Card.sequence_number.desc()))
    return [_card_read(card) for card in cards]


@router.post("/api/v1/cards/{card_id}/retry-ocr", response_model=CardRead)
async def retry_ocr(
    card_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
) -> CardRead:
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    if card.status == "REMOVED":
        raise api_error(409, "CARD_REMOVED", "Restore the card before running OCR again.")
    if card.status == "APPROVED":
        raise api_error(409, "CARD_ALREADY_APPROVED", "Approved cards are edited from history.")
    storage_key = card.normalized_image_storage_key or card.image_storage_key
    if not storage_key:
        raise api_error(
            409, "CARD_IMAGE_NOT_RETAINED", "OCR cannot retry without a retained image."
        )
    image_path = Path(request.app.state.settings.card_image_dir) / storage_key
    if not image_path.is_file():
        raise api_error(404, "CARD_IMAGE_MISSING", "Card image is unavailable.")

    provider = request.app.state.ocr_provider
    event = db.get(Event, card.event_id)
    started = time.perf_counter()
    attempt_number = db.scalar(
        select(func.max(OCRAttempt.attempt_number)).where(OCRAttempt.card_id == card.id)
    )
    vision = process_card_image(image_path.read_bytes())
    try:
        result = await provider.extract(
            vision.ocr_image,
            OCRContext(event_type=event.event_type if event else None),
        )
        card.status = "NEEDS_REVIEW"
        card.raw_ocr = result.raw_text
        card.final_text = result.raw_text
        card.suggested_type = result.suggested_type
        card.final_type = result.suggested_type
        card.ocr_confidence = result.confidence
        card.ocr_provider = result.provider
        card.ocr_model = result.model
        db.add(
            OCRAttempt(
                card_id=card.id,
                attempt_number=(attempt_number or 0) + 1,
                provider=result.provider,
                model=result.model,
                raw_text=result.raw_text,
                suggested_type=result.suggested_type,
                confidence=result.confidence,
                latency_ms=int((time.perf_counter() - started) * 1000),
                provider_metadata={**result.metadata, "vision": vision.metrics},
            )
        )
    except OCRProviderError as exc:
        card.status = "OCR_FAILED"
        card.ocr_provider = provider.provider_id
        db.add(
            OCRAttempt(
                card_id=card.id,
                attempt_number=(attempt_number or 0) + 1,
                provider=provider.provider_id,
                error_code="OCR_FAILED",
                error_message_safe=str(exc),
                latency_ms=int((time.perf_counter() - started) * 1000),
                provider_metadata={"vision": vision.metrics},
            )
        )
    except Exception:
        card.status = "OCR_FAILED"
        card.ocr_provider = provider.provider_id
        db.add(
            OCRAttempt(
                card_id=card.id,
                attempt_number=(attempt_number or 0) + 1,
                provider=provider.provider_id,
                error_code="OCR_FAILED",
                error_message_safe="The OCR provider failed unexpectedly.",
                latency_ms=int((time.perf_counter() - started) * 1000),
                provider_metadata={"vision": vision.metrics},
            )
        )
    db.commit()
    db.refresh(card)
    return _card_read(card)


@router.post("/api/v1/cards/{card_id}/approve", response_model=CardRead)
def approve_card(
    card_id: uuid.UUID,
    payload: CardApprove,
    request: Request,
    db: Session = Depends(get_db),
) -> CardRead:
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    if card.status == "REMOVED":
        raise api_error(409, "CARD_REMOVED", "Restore the card before approving it.")
    if card.status == "APPROVED":
        raise api_error(409, "CARD_ALREADY_APPROVED", "Approved cards are edited from history.")
    final_text = payload.final_text.strip()
    if not final_text:
        raise api_error(422, "EMPTY_FINAL_TEXT", "Enter the card response before approving.")

    card.final_text = final_text
    card.final_type = payload.final_type.value
    card.was_edited = final_text != (card.raw_ocr or "") or card.final_type != card.suggested_type
    card.status = "APPROVED"
    card.approved_at = datetime.now(UTC)
    capture_session = db.get(CaptureSession, card.session_id)
    if capture_session:
        capture_session.last_activity_at = card.approved_at
    mark_card_for_sync(db, card, request.app.state.settings)

    retained_paths: list[Path] = []
    if request.app.state.settings.card_image_retention == "delete_after_approval":
        if card.image_storage_key:
            retained_paths.append(
                Path(request.app.state.settings.card_image_dir) / card.image_storage_key
            )
        if card.normalized_image_storage_key:
            retained_paths.append(
                Path(request.app.state.settings.card_image_dir) / card.normalized_image_storage_key
            )
        card.image_storage_key = None
        card.normalized_image_storage_key = None

    db.commit()
    db.refresh(card)
    for retained_path in retained_paths:
        if retained_path.is_file():
            retained_path.unlink(missing_ok=True)
    return _card_read(card)


@router.post("/api/v1/cards/{card_id}/skip", response_model=CardRead)
def skip_card(card_id: uuid.UUID, db: Session = Depends(get_db)) -> CardRead:
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    if card.status == "REMOVED":
        raise api_error(409, "CARD_REMOVED", "Restore the card before changing its status.")
    card.status = "SKIPPED"
    db.commit()
    db.refresh(card)
    return _card_read(card)


@router.delete("/api/v1/cards/{card_id}", response_model=CardRead)
def remove_card(
    card_id: uuid.UUID,
    request: Request,
    reason: str | None = Query(None, max_length=500),
    db: Session = Depends(get_db),
) -> CardRead:
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    if card.status == "REMOVED":
        return _card_read(card)
    if card.status not in {"APPROVED", "SKIPPED"}:
        raise api_error(
            409,
            "CARD_NOT_SETTLED",
            "Approve or skip the card before removing it from history.",
        )

    retained_paths = [
        Path(request.app.state.settings.card_image_dir) / storage_key
        for storage_key in (card.image_storage_key, card.normalized_image_storage_key)
        if storage_key
    ]
    card.status_before_removal = card.status
    card.status = "REMOVED"
    card.removed_at = datetime.now(UTC)
    card.removed_reason = reason.strip() if reason and reason.strip() else "Removed by operator."
    card.image_storage_key = None
    card.normalized_image_storage_key = None
    capture_session = db.get(CaptureSession, card.session_id)
    if capture_session:
        capture_session.last_activity_at = card.removed_at
    mark_card_for_sync(db, card, request.app.state.settings)
    db.commit()
    db.refresh(card)

    for retained_path in retained_paths:
        if retained_path.is_file():
            retained_path.unlink(missing_ok=True)
    return _card_read(card)


@router.post("/api/v1/cards/{card_id}/restore", response_model=CardRead)
def restore_card(
    card_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> CardRead:
    card = db.get(Card, card_id)
    if card is None:
        raise api_error(404, "CARD_NOT_FOUND", "Card not found.")
    if card.status != "REMOVED":
        raise api_error(409, "CARD_NOT_REMOVED", "Only removed cards can be restored.")

    card.status = (
        card.status_before_removal
        if card.status_before_removal in {"APPROVED", "SKIPPED"}
        else "SKIPPED"
    )
    card.status_before_removal = None
    card.removed_at = None
    card.removed_reason = None
    capture_session = db.get(CaptureSession, card.session_id)
    if capture_session:
        capture_session.last_activity_at = datetime.now(UTC)
    mark_card_for_sync(db, card, request.app.state.settings)
    db.commit()
    db.refresh(card)
    return _card_read(card)


@router.get("/api/v1/ocr/providers")
async def list_ocr_providers(request: Request) -> list[dict[str, object]]:
    configured = await request.app.state.ocr_provider.health()
    return [
        {
            "id": "mock",
            "enabled": configured.provider_id == "mock",
            "ready": True,
            "model": "deterministic-v1",
        },
        {
            "id": "hunyuan",
            "enabled": configured.provider_id == "hunyuan",
            "ready": configured.ready if configured.provider_id == "hunyuan" else False,
            "model": configured.model if configured.provider_id == "hunyuan" else "HYVL",
            "detail": configured.detail if configured.provider_id == "hunyuan" else None,
        },
    ]
