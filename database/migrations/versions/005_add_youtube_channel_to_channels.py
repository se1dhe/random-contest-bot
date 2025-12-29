"""Add YouTube channel ID to channels table

Revision ID: 005_add_yt_to_channels
Revises: 004_add_youtube_credentials
Create Date: 2025-12-29 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_add_yt_to_channels'
down_revision = '004_add_youtube_credentials'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поле для YouTube канала в таблицу channels
    op.add_column('channels', sa.Column('youtube_channel_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Удаляем поле
    op.drop_column('channels', 'youtube_channel_id')
