"""Add owner subscriptions and ownership fields

Revision ID: 018_owner_subscriptions
Revises: 017_tiktok_channels
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "018_owner_subscriptions"
down_revision = "017_tiktok_channels"
branch_labels = None
depends_on = None


owner_subscription_status = sa.Enum("ACTIVE", "EXPIRED", "CANCELED", name="ownersubscriptionstatus")
subscription_payment_status = sa.Enum("CREATED", "PENDING", "SUCCEEDED", "FAILED", "CANCELED", name="subscriptionpaymentstatus")


def upgrade():
    op.add_column("channels", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_channels_owner_user_id"), "channels", ["owner_user_id"], unique=False)

    op.add_column("contests", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_contests_owner_user_id"), "contests", ["owner_user_id"], unique=False)

    op.add_column("youtube_channels", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_youtube_channels_owner_user_id"), "youtube_channels", ["owner_user_id"], unique=False)

    op.add_column("tiktok_channels", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_tiktok_channels_owner_user_id"), "tiktok_channels", ["owner_user_id"], unique=False)

    op.add_column("instagram_channels", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_instagram_channels_owner_user_id"), "instagram_channels", ["owner_user_id"], unique=False)

    owner_subscription_status.create(op.get_bind(), checkfirst=True)
    subscription_payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "owner_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", owner_subscription_status, nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("external_charge_id", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_owner_subscriptions_user_id"), "owner_subscriptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_owner_subscriptions_status"), "owner_subscriptions", ["status"], unique=False)
    op.create_index(op.f("ix_owner_subscriptions_ends_at"), "owner_subscriptions", ["ends_at"], unique=False)
    op.create_index(op.f("ix_owner_subscriptions_external_charge_id"), "owner_subscriptions", ["external_charge_id"], unique=False)

    op.create_table(
        "subscription_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_charge_id", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", subscription_payment_status, nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_charge_id"),
    )
    op.create_index(op.f("ix_subscription_payments_user_id"), "subscription_payments", ["user_id"], unique=False)
    op.create_index(op.f("ix_subscription_payments_provider"), "subscription_payments", ["provider"], unique=False)
    op.create_index(op.f("ix_subscription_payments_external_charge_id"), "subscription_payments", ["external_charge_id"], unique=False)
    op.create_index(op.f("ix_subscription_payments_status"), "subscription_payments", ["status"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_subscription_payments_status"), table_name="subscription_payments")
    op.drop_index(op.f("ix_subscription_payments_external_charge_id"), table_name="subscription_payments")
    op.drop_index(op.f("ix_subscription_payments_provider"), table_name="subscription_payments")
    op.drop_index(op.f("ix_subscription_payments_user_id"), table_name="subscription_payments")
    op.drop_table("subscription_payments")

    op.drop_index(op.f("ix_owner_subscriptions_external_charge_id"), table_name="owner_subscriptions")
    op.drop_index(op.f("ix_owner_subscriptions_ends_at"), table_name="owner_subscriptions")
    op.drop_index(op.f("ix_owner_subscriptions_status"), table_name="owner_subscriptions")
    op.drop_index(op.f("ix_owner_subscriptions_user_id"), table_name="owner_subscriptions")
    op.drop_table("owner_subscriptions")

    subscription_payment_status.drop(op.get_bind(), checkfirst=True)
    owner_subscription_status.drop(op.get_bind(), checkfirst=True)

    op.drop_index(op.f("ix_instagram_channels_owner_user_id"), table_name="instagram_channels")
    op.drop_column("instagram_channels", "owner_user_id")
    op.drop_index(op.f("ix_tiktok_channels_owner_user_id"), table_name="tiktok_channels")
    op.drop_column("tiktok_channels", "owner_user_id")
    op.drop_index(op.f("ix_youtube_channels_owner_user_id"), table_name="youtube_channels")
    op.drop_column("youtube_channels", "owner_user_id")
    op.drop_index(op.f("ix_contests_owner_user_id"), table_name="contests")
    op.drop_column("contests", "owner_user_id")
    op.drop_index(op.f("ix_channels_owner_user_id"), table_name="channels")
    op.drop_column("channels", "owner_user_id")
