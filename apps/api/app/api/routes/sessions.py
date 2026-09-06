import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.database import get_db
from app.models import CaptureSession, Card, Event
from app.schemas.common import SessionStatus
from app.schemas.sessions import SessionCreate, SessionRead

router = APIRouter(tags=["sessions"])


def _session_read(db: Session, capture_session: CaptureSession) -> SessionRead:
    event = db.get(Event, capture_session.event_id)
    counts = db.execute(
        select(
            func.count(Card.id),
            func.sum(case((Card.status.in_(["NEEDS_REVIEW", "OCR_FAILED"]), 1), else_=0)),
            func.sum(case((Card.status == "APPROVED", 1), else_=0)),
            func.sum(case((Card.status == "SKIPPED", 1), else_=0)),
        ).where(Card.session_id == capture_session.id, Card.status != "REMOVED")
    ).one()
    return SessionRead(
        id=capture_session.id,
        event_id=capture_session.event_id,
        name=capture_session.name,
        status=capture_session.status,
        started_at=capture_session.started_at,
        completed_at=capture_session.completed_at,
        archived_at=capture_session.archived_at,
        last_activity_at=capture_session.last_activity_at,
        created_at=capture_session.created_at,
        updated_at=capture_session.updated_at,
        event_title=event.title if event else "Unknown event",
        event_type=event.event_type if event else "OTHER",
        total_cards=counts[0] or 0,
        review_cards=counts[1] or 0,
        approved_cards=counts[2] or 0,
        skipped_cards=counts[3] or 0,
    )


@router.post("/api/v1/events/{event_id}/sessions", response_model=SessionRead, status_code=201)
def create_session(
    event_id: uuid.UUID, payload: SessionCreate, db: Session = Depends(get_db)
) -> SessionRead:
    event = db.get(Event, event_id)
    if event is None:
        raise api_error(404, "EVENT_NOT_FOUND", "Event not found.")
    count = db.scalar(
        select(func.count()).select_from(CaptureSession).where(CaptureSession.event_id == event_id)
    )
    capture_session = CaptureSession(
        event_id=event_id,
        name=payload.name or f"Session {(count or 0) + 1}",
    )
    db.add(capture_session)
    db.commit()
    db.refresh(capture_session)
    return _session_read(db, capture_session)


@router.get("/api/v1/sessions", response_model=list[SessionRead])
def list_sessions(
    status: SessionStatus | None = Query(None),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[SessionRead]:
    statement = select(CaptureSession).join(Event, CaptureSession.event_id == Event.id)
    if status:
        statement = statement.where(CaptureSession.status == status.value)
    if not include_archived:
        statement = statement.where(
            CaptureSession.status != "ARCHIVED",
            Event.is_archived.is_(False),
        )
    capture_sessions = db.scalars(statement.order_by(CaptureSession.last_activity_at.desc()))
    return [_session_read(db, item) for item in capture_sessions]


@router.get("/api/v1/sessions/{session_id}", response_model=SessionRead)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> SessionRead:
    capture_session = db.get(CaptureSession, session_id)
    if capture_session is None:
        raise api_error(404, "SESSION_NOT_FOUND", "Capture session not found.")
    return _session_read(db, capture_session)


def _transition(
    session_id: uuid.UUID, next_status: str, db: Session, *, completed: bool = False
) -> SessionRead:
    capture_session = db.get(CaptureSession, session_id)
    if capture_session is None:
        raise api_error(404, "SESSION_NOT_FOUND", "Capture session not found.")
    now = datetime.now(UTC)
    capture_session.status = next_status
    capture_session.last_activity_at = now
    if next_status == "ARCHIVED":
        capture_session.archived_at = now
    if completed:
        capture_session.completed_at = now
    elif next_status == "IN_PROGRESS":
        capture_session.completed_at = None
        capture_session.archived_at = None
    db.commit()
    db.refresh(capture_session)
    return _session_read(db, capture_session)


@router.post("/api/v1/sessions/{session_id}/complete", response_model=SessionRead)
def complete_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> SessionRead:
    return _transition(session_id, "COMPLETED", db, completed=True)


@router.post("/api/v1/sessions/{session_id}/reopen", response_model=SessionRead)
def reopen_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> SessionRead:
    return _transition(session_id, "IN_PROGRESS", db)


@router.post("/api/v1/sessions/{session_id}/archive", response_model=SessionRead)
def archive_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> SessionRead:
    return _transition(session_id, "ARCHIVED", db)
