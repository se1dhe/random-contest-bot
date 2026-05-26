"""Add TikTok channels table

Revision ID: 017_tiktok_channels
Revises: 016_tiktok
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "017_tiktok_channels"
down_revision = "016_tiktok"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tiktok_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id"),
    )


def downgrade():
    op.drop_table("tiktok_channels")
