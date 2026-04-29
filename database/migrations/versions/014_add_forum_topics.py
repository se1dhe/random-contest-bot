"""Add forum topic targeting for contests

Revision ID: 014_forum_topics
Revises: 013_norm_ext_keys
Create Date: 2026-04-28
"""

from alembic import op
import sqlalchemy as sa


revision = "014_forum_topics"
down_revision = "013_norm_ext_keys"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contests", sa.Column("message_thread_id", sa.Integer(), nullable=True))
    op.create_table(
        "forum_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_thread_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("icon_color", sa.Integer(), nullable=True),
        sa.Column("icon_custom_emoji_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", "message_thread_id", name="uq_forum_topics_chat_thread"),
    )
    op.create_index(op.f("ix_forum_topics_chat_id"), "forum_topics", ["chat_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_forum_topics_chat_id"), table_name="forum_topics")
    op.drop_table("forum_topics")
    op.drop_column("contests", "message_thread_id")
