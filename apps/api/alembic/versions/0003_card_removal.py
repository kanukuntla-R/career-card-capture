"""Add reversible removal state for cards."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_card_removal"
down_revision: str | None = "0002_card_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_CARD_STATUSES = (
    "status IN ('CAPTURED', 'PROCESSING', 'NEEDS_REVIEW', "
    "'APPROVED', 'SKIPPED', 'OCR_FAILED')"
)
CARD_STATUSES_WITH_REMOVED = (
    "status IN ('CAPTURED', 'PROCESSING', 'NEEDS_REVIEW', "
    "'APPROVED', 'SKIPPED', 'OCR_FAILED', 'REMOVED')"
)


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("removed_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("status_before_removal", sa.String(30), nullable=True))
        batch_op.drop_constraint("ck_cards_status", type_="check")
        batch_op.create_check_constraint("ck_cards_status", CARD_STATUSES_WITH_REMOVED)


def downgrade() -> None:
    op.execute(
        "UPDATE cards SET status = COALESCE(status_before_removal, 'SKIPPED') "
        "WHERE status = 'REMOVED'"
    )
    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_constraint("ck_cards_status", type_="check")
        batch_op.create_check_constraint("ck_cards_status", OLD_CARD_STATUSES)
        batch_op.drop_column("status_before_removal")
        batch_op.drop_column("removed_reason")
        batch_op.drop_column("removed_at")
