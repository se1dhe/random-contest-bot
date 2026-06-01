"""Add Telegram Stars contest entry payments

Revision ID: 023_add_contest_entry_stars
Revises: 022_remove_subscription_billing
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "023_add_contest_entry_stars"
down_revision = "022_remove_subscription_billing"
branch_labels = None
depends_on = None


entry_payment_status = sa.Enum("PENDING", "SUCCEEDED", "FAILED", name="contestentrypaymentstatus")
entry_payment_status_column = postgresql.ENUM(
    "PENDING",
    "SUCCEEDED",
    "FAILED",
    name="contestentrypaymentstatus",
    create_type=False,
)


def upgrade() -> None:
    op.add_column("contests", sa.Column("entry_fee_stars", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("contests", "entry_fee_stars", server_default=None)

    entry_payment_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "contest_entry_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount_stars", sa.Integer(), nullable=False),
        sa.Column("status", entry_payment_status_column, nullable=False),
        sa.Column("invoice_payload", sa.String(length=255), nullable=False),
        sa.Column("telegram_payment_charge_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payment_charge_id", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("invoice_link", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["contest_id"], ["contests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_payload"),
        sa.UniqueConstraint("telegram_payment_charge_id"),
    )
    op.create_index(op.f("ix_contest_entry_payments_contest_id"), "contest_entry_payments", ["contest_id"], unique=False)
    op.create_index(op.f("ix_contest_entry_payments_invoice_payload"), "contest_entry_payments", ["invoice_payload"], unique=True)
    op.create_index(
        op.f("ix_contest_entry_payments_telegram_payment_charge_id"),
        "contest_entry_payments",
        ["telegram_payment_charge_id"],
        unique=True,
    )
    op.create_index(op.f("ix_contest_entry_payments_status"), "contest_entry_payments", ["status"], unique=False)
    op.create_index(op.f("ix_contest_entry_payments_user_id"), "contest_entry_payments", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contest_entry_payments_user_id"), table_name="contest_entry_payments")
    op.drop_index(op.f("ix_contest_entry_payments_status"), table_name="contest_entry_payments")
    op.drop_index(op.f("ix_contest_entry_payments_telegram_payment_charge_id"), table_name="contest_entry_payments")
    op.drop_index(op.f("ix_contest_entry_payments_invoice_payload"), table_name="contest_entry_payments")
    op.drop_index(op.f("ix_contest_entry_payments_contest_id"), table_name="contest_entry_payments")
    op.drop_table("contest_entry_payments")
    entry_payment_status.drop(op.get_bind(), checkfirst=True)
    op.drop_column("contests", "entry_fee_stars")
