"""Remove subscription billing tables

Revision ID: 022_remove_subscription_billing
Revises: 021_remove_social
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa


revision = "022_remove_subscription_billing"
down_revision = "021_remove_social"
branch_labels = None
depends_on = None


def _drop_table_if_exists(inspector, table_name: str) -> None:
    if table_name in inspector.get_table_names():
        op.drop_table(table_name)


def _drop_pg_enum_if_exists(enum_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    _drop_table_if_exists(inspector, "subscription_payments")
    _drop_table_if_exists(inspector, "owner_subscriptions")
    _drop_pg_enum_if_exists("subscriptionpaymentstatus")
    _drop_pg_enum_if_exists("ownersubscriptionstatus")


def downgrade() -> None:
    pass
