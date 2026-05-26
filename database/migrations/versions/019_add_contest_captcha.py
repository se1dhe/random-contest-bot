"""Add optional contest captcha

Revision ID: 019_add_contest_captcha
Revises: 018_owner_subscriptions
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "019_add_contest_captcha"
down_revision = "018_owner_subscriptions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contests", sa.Column("require_captcha", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("contests", "require_captcha", server_default=None)


def downgrade():
    op.drop_column("contests", "require_captcha")
