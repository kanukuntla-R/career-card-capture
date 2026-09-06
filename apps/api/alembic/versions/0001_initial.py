"""Initial event, session, card, and OCR attempt schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("course", sa.Text(), nullable=True),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('TABLING', 'CLASSROOM_PRESENTATION', 'OTHER')",
            name="ck_events_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_event_date", "events", ["event_date"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_is_archived", "events", ["is_archived"])

    op.create_table(
        "capture_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED', 'ARCHIVED')",
            name="ck_capture_sessions_status",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capture_sessions_event_id", "capture_sessions", ["event_id"])
    op.create_index("ix_capture_sessions_status", "capture_sessions", ["status"])

    op.create_table(
        "cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("suggested_type", sa.String(length=20), nullable=True),
        sa.Column("final_type", sa.String(length=20), nullable=True),
        sa.Column("raw_ocr", sa.Text(), nullable=True),
        sa.Column("final_text", sa.Text(), nullable=True),
        sa.Column("ocr_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("ocr_provider", sa.Text(), nullable=True),
        sa.Column("ocr_model", sa.Text(), nullable=True),
        sa.Column("was_edited", sa.Boolean(), nullable=False),
        sa.Column("image_storage_key", sa.Text(), nullable=True),
        sa.Column("normalized_image_storage_key", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('CAPTURED', 'PROCESSING', 'NEEDS_REVIEW', "
            "'APPROVED', 'SKIPPED', 'OCR_FAILED')",
            name="ck_cards_status",
        ),
        sa.CheckConstraint(
            "suggested_type IS NULL OR suggested_type IN ('EMPLOYER', 'QUESTION', 'UNKNOWN')",
            name="ck_cards_suggested_type",
        ),
        sa.CheckConstraint(
            "final_type IS NULL OR final_type IN ('EMPLOYER', 'QUESTION', 'UNKNOWN')",
            name="ck_cards_final_type",
        ),
        sa.CheckConstraint(
            "status != 'APPROVED' OR (length(trim(final_text)) > 0 AND final_type IS NOT NULL)",
            name="ck_cards_approved_fields",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id"], ["capture_sessions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence_number", name="uq_cards_session_sequence"),
    )
    op.create_index("ix_cards_event_id", "cards", ["event_id"])
    op.create_index("ix_cards_session_id", "cards", ["session_id"])
    op.create_index("ix_cards_status", "cards", ["status"])

    op.create_table(
        "ocr_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("suggested_type", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("provider_metadata", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "attempt_number", name="uq_ocr_attempt_card_number"),
    )


def downgrade() -> None:
    op.drop_table("ocr_attempts")
    op.drop_index("ix_cards_status", table_name="cards")
    op.drop_index("ix_cards_session_id", table_name="cards")
    op.drop_index("ix_cards_event_id", table_name="cards")
    op.drop_table("cards")
    op.drop_index("ix_capture_sessions_status", table_name="capture_sessions")
    op.drop_index("ix_capture_sessions_event_id", table_name="capture_sessions")
    op.drop_table("capture_sessions")
    op.drop_index("ix_events_is_archived", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_event_date", table_name="events")
    op.drop_table("events")
