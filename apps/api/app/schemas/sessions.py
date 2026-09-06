import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import EventType, SessionStatus


class SessionCreate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    status: SessionStatus
    started_at: datetime
    completed_at: datetime | None
    archived_at: datetime | None
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    event_title: str
    event_type: EventType
    total_cards: int = 0
    review_cards: int = 0
    approved_cards: int = 0
    skipped_cards: int = 0
