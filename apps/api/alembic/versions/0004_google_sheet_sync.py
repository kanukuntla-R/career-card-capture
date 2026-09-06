"""Add idempotent Google Sheets synchronization records."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_google_sheet_sync"
down_revision: str | None = "0003_card_removal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sheet_sync_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("sheet_id_hash_or_alias", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("sheet_row_number", sa.Integer(), nullable=True),
        sa.Column("last_synced_payload_hash", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error_safe", sa.Text(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('NOT_REQUIRED', 'PENDING', 'SYNCED', 'ERROR')",
            name="ck_sheet_sync_records_status",
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id"),
        sa.UniqueConstraint("record_id"),
    )
    op.create_index("ix_sheet_sync_records_card_id", "sheet_sync_records", ["card_id"])
    op.create_index("ix_sheet_sync_records_status", "sheet_sync_records", ["status"])


def downgrade() -> None:
    op.drop_index("ix_sheet_sync_records_status", table_name="sheet_sync_records")
    op.drop_index("ix_sheet_sync_records_card_id", table_name="sheet_sync_records")
    op.drop_table("sheet_sync_records")
