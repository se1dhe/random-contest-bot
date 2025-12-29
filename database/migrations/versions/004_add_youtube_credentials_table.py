"""Add YouTube credentials table

Revision ID: 004_add_youtube_credentials
Revises: 003_add_youtube_fields
Create Date: 2025-12-22 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_youtube_credentials'
down_revision = '003_add_youtube_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу для хранения YouTube credentials пользователей
    op.create_table(
        'youtube_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('youtube_channel_id', sa.String(length=255), nullable=True),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_uri', sa.String(length=255), nullable=False, server_default='https://oauth2.googleapis.com/token'),
        sa.Column('client_id', sa.String(length=255), nullable=False),
        sa.Column('client_secret', sa.String(length=255), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_youtube_credentials_user_id'), 'youtube_credentials', ['user_id'], unique=True)


def downgrade() -> None:
    # Удаляем таблицу
    op.drop_index(op.f('ix_youtube_credentials_user_id'), table_name='youtube_credentials')
    op.drop_table('youtube_credentials')

