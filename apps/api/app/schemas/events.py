import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import EventType


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    event_type: EventType
    event_date: date | None = None
    location: str | None = None
    course: str | None = None
    topic: str | None = None
    notes: str | None = None


class EventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    event_type: EventType | None = None
    event_date: date | None = None
    location: str | None = None
    course: str | None = None
    topic: str | None = None
    notes: str | None = None
    is_archived: bool | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    event_type: EventType
    event_date: date | None
    location: str | None
    course: str | None
    topic: str | None
    notes: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class EventDetail(EventRead):
    session_count: int = 0
    card_count: int = 0
    approved_count: int = 0
