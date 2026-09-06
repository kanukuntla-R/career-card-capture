import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CardStatus, CardType, SheetSyncStatus


class CardApprove(BaseModel):
    final_type: CardType
    final_text: str = Field(min_length=1, max_length=4000)


class CardEdit(CardApprove):
    reason: str | None = Field(default=None, max_length=500)


class CardRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    card_id: uuid.UUID
    revision_number: int
    previous_final_type: CardType
    previous_final_text: str
    new_final_type: CardType
    new_final_text: str
    reason: str | None
    changed_at: datetime
    changed_by: str | None


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    session_id: uuid.UUID
    sequence_number: int
    status: CardStatus
    suggested_type: CardType | None
    final_type: CardType | None
    raw_ocr: str | None
    final_text: str | None
    ocr_confidence: float | None
    ocr_provider: str | None
    ocr_model: str | None
    was_edited: bool
    has_image: bool
    captured_at: datetime
    approved_at: datetime | None
    removed_at: datetime | None
    removed_reason: str | None
    sync_status: SheetSyncStatus
    created_at: datetime
    updated_at: datetime
