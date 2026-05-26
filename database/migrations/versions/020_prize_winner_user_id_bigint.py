"""Make prize winner Telegram id bigint

Revision ID: 020_prize_winner_user_id_bigint
Revises: 019_add_contest_captcha
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "020_prize_winner_user_id_bigint"
down_revision = "019_add_contest_captcha"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "prizes",
        "winner_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "prizes",
        "winner_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
