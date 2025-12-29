"""add image_path and winner_firstname

Revision ID: 006_add_img_firstname
Revises: 005_add_yt_to_channels
Create Date: 2025-12-29 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_img_firstname'
down_revision = '005_add_yt_to_channels'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поле image_path в таблицу contests
    op.add_column('contests', sa.Column('image_path', sa.String(length=500), nullable=True))
    
    # Добавляем поле winner_firstname в таблицу prizes
    op.add_column('prizes', sa.Column('winner_firstname', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Удаляем поле winner_firstname из таблицы prizes
    op.drop_column('prizes', 'winner_firstname')
    
    # Удаляем поле image_path из таблицы contests
    op.drop_column('contests', 'image_path')
