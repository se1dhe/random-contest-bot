"""Normalize external channel primary keys

Revision ID: 013_norm_ext_keys
Revises: 012_kick_channels
Create Date: 2026-04-11 20:05:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "013_norm_ext_keys"
down_revision = "012_kick_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE youtube_channels
        DROP CONSTRAINT IF EXISTS youtube_channels_pkey,
        ADD CONSTRAINT youtube_channels_pkey PRIMARY KEY (id);
        """
    )
    op.execute(
        """
        ALTER TABLE youtube_channels
        ADD CONSTRAINT uq_youtube_channels_channel_id UNIQUE (channel_id);
        """
    )

    op.execute(
        """
        ALTER TABLE kick_channels
        DROP CONSTRAINT IF EXISTS kick_channels_pkey,
        ADD CONSTRAINT kick_channels_pkey PRIMARY KEY (id);
        """
    )
    op.execute(
        """
        ALTER TABLE kick_channels
        ADD CONSTRAINT uq_kick_channels_channel_id UNIQUE (channel_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE kick_channels
        DROP CONSTRAINT IF EXISTS uq_kick_channels_channel_id,
        DROP CONSTRAINT IF EXISTS kick_channels_pkey,
        ADD CONSTRAINT kick_channels_pkey PRIMARY KEY (channel_id, id);
        """
    )

    op.execute(
        """
        ALTER TABLE youtube_channels
        DROP CONSTRAINT IF EXISTS uq_youtube_channels_channel_id,
        DROP CONSTRAINT IF EXISTS youtube_channels_pkey,
        ADD CONSTRAINT youtube_channels_pkey PRIMARY KEY (channel_id, id);
        """
    )
