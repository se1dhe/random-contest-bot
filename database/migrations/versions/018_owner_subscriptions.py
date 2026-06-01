"""Add ownership fields

Revision ID: 018_owner_subscriptions
Revises: 017_tiktok_channels
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "018_owner_subscriptions"
down_revision = "017_tiktok_channels"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("channels", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_channels_owner_user_id"), "channels", ["owner_user_id"], unique=False)

    op.add_column("contests", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_contests_owner_user_id"), "contests", ["owner_user_id"], unique=False)

    op.add_column("youtube_channels", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_youtube_channels_owner_user_id"), "youtube_channels", ["owner_user_id"], unique=False)

    op.add_column("tiktok_channels", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_tiktok_channels_owner_user_id"), "tiktok_channels", ["owner_user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_tiktok_channels_owner_user_id"), table_name="tiktok_channels")
    op.drop_column("tiktok_channels", "owner_user_id")
    op.drop_index(op.f("ix_youtube_channels_owner_user_id"), table_name="youtube_channels")
    op.drop_column("youtube_channels", "owner_user_id")
    op.drop_index(op.f("ix_contests_owner_user_id"), table_name="contests")
    op.drop_column("contests", "owner_user_id")
    op.drop_index(op.f("ix_channels_owner_user_id"), table_name="channels")
    op.drop_column("channels", "owner_user_id")
