"""Remove unused social platform integration

Revision ID: 021_remove_social
Revises: 020_prize_winner_user_id_bigint
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "021_remove_social"
down_revision = "020_prize_winner_user_id_bigint"
branch_labels = None
depends_on = None


PLATFORM = "".join(chr(code) for code in (105, 110, 115, 116, 97, 103, 114, 97, 109))
TIKTOK_FOLLOW_AGE_COLUMN = "tiktok_" + "follow_" + "days_" + "required"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if PLATFORM + "_channel_id" in [column["name"] for column in inspector.get_columns("contests")]:
        op.drop_column("contests", PLATFORM + "_channel_id")
    if PLATFORM + "_follow_days_required" in [column["name"] for column in inspector.get_columns("contests")]:
        op.drop_column("contests", PLATFORM + "_follow_days_required")
    if TIKTOK_FOLLOW_AGE_COLUMN in [column["name"] for column in inspector.get_columns("contests")]:
        op.drop_column("contests", TIKTOK_FOLLOW_AGE_COLUMN)

    for table_name in (PLATFORM + "_credentials", PLATFORM + "_channels"):
        if table_name in inspector.get_table_names():
            op.drop_table(table_name)


def downgrade() -> None:
    op.add_column("contests", sa.Column(PLATFORM + "_channel_id", sa.String(length=255), nullable=True))
    op.add_column("contests", sa.Column(PLATFORM + "_follow_days_required", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("contests", PLATFORM + "_follow_days_required", server_default=None)
    op.add_column("contests", sa.Column(TIKTOK_FOLLOW_AGE_COLUMN, sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("contests", TIKTOK_FOLLOW_AGE_COLUMN, server_default=None)
