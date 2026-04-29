"""Add first and last name fields to participants

Revision ID: 008_add_participant_names
Revises: 007_add_post_to_sponsors
Create Date: 2026-04-10 23:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_add_participant_names'
down_revision = '007_add_post_to_sponsors'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('participants', sa.Column('first_name', sa.String(length=255), nullable=True))
    op.add_column('participants', sa.Column('last_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('participants', 'last_name')
    op.drop_column('participants', 'first_name')
