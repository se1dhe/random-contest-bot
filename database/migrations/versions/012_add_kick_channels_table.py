"""Add kick_channels table

Revision ID: 012_kick_channels
Revises: 011_twitch_kick
Create Date: 2026-04-11 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "012_kick_channels"
down_revision = "011_twitch_kick"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kick_channels",
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("channel_id", "id"),
    )


def downgrade() -> None:
    op.drop_table("kick_channels")
