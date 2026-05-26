"""Replace Twitch/Kick contest checks with TikTok

Revision ID: 016_tiktok
Revises: 015_contest_language
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "016_tiktok"
down_revision = "015_contest_language"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contests", sa.Column("tiktok_channel_id", sa.String(length=255), nullable=True))

    op.create_table(
        "tiktok_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("tiktok_user_id", sa.String(length=255), nullable=False),
        sa.Column("tiktok_login", sa.String(length=255), nullable=True),
        sa.Column("tiktok_display_name", sa.String(length=255), nullable=True),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_uri", sa.String(length=255), server_default="https://open.tiktokapis.com/v2/oauth/token/", nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=255), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tiktok_credentials_user_id"), "tiktok_credentials", ["user_id"], unique=True)
    op.create_index(op.f("ix_tiktok_credentials_tiktok_user_id"), "tiktok_credentials", ["tiktok_user_id"], unique=False)


    op.drop_column("contests", "twitch_channel_id")
    op.drop_column("contests", "twitch_follow_days_required")
    op.drop_column("contests", "kick_channel_id")
    op.drop_column("contests", "kick_follow_days_required")
    op.drop_table("twitch_credentials")
    op.drop_table("kick_credentials")
    op.drop_table("kick_channels")


def downgrade():
    op.add_column("contests", sa.Column("twitch_channel_id", sa.String(length=255), nullable=True))
    op.add_column("contests", sa.Column("twitch_follow_days_required", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("contests", sa.Column("kick_channel_id", sa.String(length=255), nullable=True))
    op.add_column("contests", sa.Column("kick_follow_days_required", sa.Integer(), nullable=False, server_default="0"))
    op.drop_index(op.f("ix_tiktok_credentials_tiktok_user_id"), table_name="tiktok_credentials")
    op.drop_index(op.f("ix_tiktok_credentials_user_id"), table_name="tiktok_credentials")
    op.drop_table("tiktok_credentials")
    op.drop_column("contests", "tiktok_channel_id")
