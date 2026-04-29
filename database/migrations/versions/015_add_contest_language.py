"""Add contest language

Revision ID: 015_contest_language
Revises: 014_forum_topics
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa


revision = "015_contest_language"
down_revision = "014_forum_topics"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "contests",
        sa.Column("language", sa.String(length=8), nullable=False, server_default="ru"),
    )
    op.alter_column("contests", "language", server_default=None)


def downgrade():
    op.drop_column("contests", "language")
