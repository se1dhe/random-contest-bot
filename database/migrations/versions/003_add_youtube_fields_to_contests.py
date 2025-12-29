"""Add YouTube fields to contests

Revision ID: 003_add_youtube_fields
Revises: 001_initial
Create Date: 2025-12-22 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_add_youtube_fields'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поля для YouTube подписки
    op.add_column('contests', sa.Column('youtube_channel_id', sa.String(length=255), nullable=True))
    op.add_column('contests', sa.Column('youtube_subscription_days_required', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Удаляем поля
    op.drop_column('contests', 'youtube_subscription_days_required')
    op.drop_column('contests', 'youtube_channel_id')

