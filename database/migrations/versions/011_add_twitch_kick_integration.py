"""Add Twitch/Kick contest conditions and OAuth credential tables

Revision ID: 011_twitch_kick
Revises: 010_admin_actions_fk
Create Date: 2026-04-11 14:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "011_twitch_kick"
down_revision = "010_admin_actions_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contests", sa.Column("twitch_channel_id", sa.String(length=255), nullable=True))
    op.add_column("contests", sa.Column("twitch_follow_days_required", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("contests", sa.Column("kick_channel_id", sa.String(length=255), nullable=True))
    op.add_column("contests", sa.Column("kick_follow_days_required", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "twitch_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("twitch_user_id", sa.String(length=255), nullable=False),
        sa.Column("twitch_login", sa.String(length=255), nullable=True),
        sa.Column("twitch_display_name", sa.String(length=255), nullable=True),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_uri", sa.String(length=255), server_default="https://id.twitch.tv/oauth2/token", nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=255), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_twitch_credentials_user_id"), "twitch_credentials", ["user_id"], unique=True)
    op.create_index(op.f("ix_twitch_credentials_twitch_user_id"), "twitch_credentials", ["twitch_user_id"], unique=False)

    op.create_table(
        "kick_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("kick_user_id", sa.String(length=255), nullable=False),
        sa.Column("kick_username", sa.String(length=255), nullable=True),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_uri", sa.String(length=255), server_default="https://id.kick.com/oauth/token", nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=255), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kick_credentials_user_id"), "kick_credentials", ["user_id"], unique=True)
    op.create_index(op.f("ix_kick_credentials_kick_user_id"), "kick_credentials", ["kick_user_id"], unique=False)

    op.alter_column("contests", "twitch_follow_days_required", server_default=None)
    op.alter_column("contests", "kick_follow_days_required", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_kick_credentials_kick_user_id"), table_name="kick_credentials")
    op.drop_index(op.f("ix_kick_credentials_user_id"), table_name="kick_credentials")
    op.drop_table("kick_credentials")

    op.drop_index(op.f("ix_twitch_credentials_twitch_user_id"), table_name="twitch_credentials")
    op.drop_index(op.f("ix_twitch_credentials_user_id"), table_name="twitch_credentials")
    op.drop_table("twitch_credentials")

    op.drop_column("contests", "kick_follow_days_required")
    op.drop_column("contests", "kick_channel_id")
    op.drop_column("contests", "twitch_follow_days_required")
    op.drop_column("contests", "twitch_channel_id")
