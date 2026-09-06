"""Add append-only revision history for approved card edits."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_card_revisions"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "card_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_final_type", sa.String(length=20), nullable=False),
        sa.Column("previous_final_text", sa.Text(), nullable=False),
        sa.Column("new_final_type", sa.String(length=20), nullable=False),
        sa.Column("new_final_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "revision_number", name="uq_card_revision_number"),
    )
    op.create_index("ix_card_revisions_card_id", "card_revisions", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_card_revisions_card_id", table_name="card_revisions")
    op.drop_table("card_revisions")
