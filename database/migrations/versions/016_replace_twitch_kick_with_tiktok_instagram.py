"""Replace Twitch/Kick contest checks with TikTok/Instagram

Revision ID: 016_tiktok_instagram
Revises: 015_contest_language
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "016_tiktok_instagram"
down_revision = "015_contest_language"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contests", sa.Column("tiktok_channel_id", sa.String(length=255), nullable=True))
    op.add_column("contests", sa.Column("tiktok_follow_days_required", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("contests", sa.Column("instagram_channel_id", sa.String(length=255), nullable=True))
    op.add_column("contests", sa.Column("instagram_follow_days_required", sa.Integer(), nullable=False, server_default="0"))

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

    op.create_table(
        "instagram_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("instagram_user_id", sa.String(length=255), nullable=False),
        sa.Column("instagram_username", sa.String(length=255), nullable=True),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_uri", sa.String(length=255), server_default="https://api.instagram.com/oauth/access_token", nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=255), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_instagram_credentials_user_id"), "instagram_credentials", ["user_id"], unique=True)
    op.create_index(op.f("ix_instagram_credentials_instagram_user_id"), "instagram_credentials", ["instagram_user_id"], unique=False)

    op.create_table(
        "instagram_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id"),
    )

    op.alter_column("contests", "tiktok_follow_days_required", server_default=None)
    op.alter_column("contests", "instagram_follow_days_required", server_default=None)

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
    op.drop_table("instagram_channels")
    op.drop_index(op.f("ix_instagram_credentials_instagram_user_id"), table_name="instagram_credentials")
    op.drop_index(op.f("ix_instagram_credentials_user_id"), table_name="instagram_credentials")
    op.drop_table("instagram_credentials")
    op.drop_index(op.f("ix_tiktok_credentials_tiktok_user_id"), table_name="tiktok_credentials")
    op.drop_index(op.f("ix_tiktok_credentials_user_id"), table_name="tiktok_credentials")
    op.drop_table("tiktok_credentials")
    op.drop_column("contests", "instagram_follow_days_required")
    op.drop_column("contests", "instagram_channel_id")
    op.drop_column("contests", "tiktok_follow_days_required")
    op.drop_column("contests", "tiktok_channel_id")
