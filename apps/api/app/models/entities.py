import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('TABLING', 'CLASSROOM_PRESENTATION', 'OTHER')",
            name="ck_events_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    course: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sessions: Mapped[list["CaptureSession"]] = relationship(back_populates="event")


class CaptureSession(TimestampMixin, Base):
    __tablename__ = "capture_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED', 'ARCHIVED')",
            name="ck_capture_sessions_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("events.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="IN_PROGRESS", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    event: Mapped[Event] = relationship(back_populates="sessions")
    cards: Mapped[list["Card"]] = relationship(back_populates="session")


class Card(TimestampMixin, Base):
    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_number", name="uq_cards_session_sequence"),
        CheckConstraint(
            "status IN ('CAPTURED', 'PROCESSING', 'NEEDS_REVIEW', "
            "'APPROVED', 'SKIPPED', 'OCR_FAILED', 'REMOVED')",
            name="ck_cards_status",
        ),
        CheckConstraint(
            "suggested_type IS NULL OR suggested_type IN ('EMPLOYER', 'QUESTION', 'UNKNOWN')",
            name="ck_cards_suggested_type",
        ),
        CheckConstraint(
            "final_type IS NULL OR final_type IN ('EMPLOYER', 'QUESTION', 'UNKNOWN')",
            name="ck_cards_final_type",
        ),
        CheckConstraint(
            "status != 'APPROVED' OR (length(trim(final_text)) > 0 AND final_type IS NOT NULL)",
            name="ck_cards_approved_fields",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("events.id", ondelete="RESTRICT"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("capture_sessions.id", ondelete="RESTRICT"), index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="CAPTURED", index=True)
    suggested_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    final_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_ocr: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    ocr_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    was_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    image_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_image_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_before_removal: Mapped[str | None] = mapped_column(String(30), nullable=True)
    session: Mapped[CaptureSession] = relationship(back_populates="cards")
    ocr_attempts: Mapped[list["OCRAttempt"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    revisions: Mapped[list["CardRevision"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    sheet_sync_record: Mapped["SheetSyncRecord | None"] = relationship(
        back_populates="card", cascade="all, delete-orphan", uselist=False
    )


class CardRevision(Base):
    __tablename__ = "card_revisions"
    __table_args__ = (
        UniqueConstraint("card_id", "revision_number", name="uq_card_revision_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cards.id", ondelete="CASCADE"), index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    previous_final_type: Mapped[str] = mapped_column(String(20))
    previous_final_text: Mapped[str] = mapped_column(Text)
    new_final_type: Mapped[str] = mapped_column(String(20))
    new_final_text: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    changed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    card: Mapped[Card] = relationship(back_populates="revisions")


class OCRAttempt(Base):
    __tablename__ = "ocr_attempts"
    __table_args__ = (
        UniqueConstraint("card_id", "attempt_number", name="uq_ocr_attempt_card_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cards.id", ondelete="CASCADE"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message_safe: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    card: Mapped[Card] = relationship(back_populates="ocr_attempts")


class SheetSyncRecord(TimestampMixin, Base):
    __tablename__ = "sheet_sync_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('NOT_REQUIRED', 'PENDING', 'SYNCED', 'ERROR')",
            name="ck_sheet_sync_records_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cards.id", ondelete="CASCADE"), unique=True, index=True
    )
    sheet_id_hash_or_alias: Mapped[str] = mapped_column(Text)
    record_id: Mapped[str] = mapped_column(Text, unique=True)
    sheet_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_synced_payload_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="NOT_REQUIRED", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error_safe: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    card: Mapped[Card] = relationship(back_populates="sheet_sync_record")
