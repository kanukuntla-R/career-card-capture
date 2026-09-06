import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.database import get_db
from app.models import CaptureSession, Card, Event
from app.schemas.events import EventCreate, EventDetail, EventPatch, EventRead
from app.services.sheets.sync import mark_card_for_sync

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> Event:
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("", response_model=list[EventRead])
def list_events(
    include_archived: bool = Query(False),
    search: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
) -> list[Event]:
    statement = select(Event)
    if not include_archived:
        statement = statement.where(Event.is_archived.is_(False))
    if search:
        statement = statement.where(Event.title.ilike(f"%{search}%"))
    return list(db.scalars(statement.order_by(Event.updated_at.desc())))


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db)) -> EventDetail:
    event = db.get(Event, event_id)
    if event is None:
        raise api_error(404, "EVENT_NOT_FOUND", "Event not found.")

    session_count = db.scalar(
        select(func.count()).select_from(CaptureSession).where(CaptureSession.event_id == event_id)
    )
    card_count = db.scalar(
        select(func.count())
        .select_from(Card)
        .where(Card.event_id == event_id, Card.status != "REMOVED")
    )
    approved_count = db.scalar(
        select(func.count())
        .select_from(Card)
        .where(Card.event_id == event_id, Card.status == "APPROVED")
    )
    return EventDetail(
        **EventRead.model_validate(event).model_dump(),
        session_count=session_count or 0,
        card_count=card_count or 0,
        approved_count=approved_count or 0,
    )


@router.patch("/{event_id}", response_model=EventRead)
def update_event(
    event_id: uuid.UUID,
    payload: EventPatch,
    request: Request,
    db: Session = Depends(get_db),
) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise api_error(404, "EVENT_NOT_FOUND", "Event not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    approved_cards = db.scalars(
        select(Card).where(Card.event_id == event_id, Card.status == "APPROVED")
    )
    for card in approved_cards:
        mark_card_for_sync(db, card, request.app.state.settings)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", response_model=EventRead)
def archive_event(event_id: uuid.UUID, db: Session = Depends(get_db)) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise api_error(404, "EVENT_NOT_FOUND", "Event not found.")
    event.is_archived = True
    db.commit()
    db.refresh(event)
    return event
