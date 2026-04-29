"""Set admin action contest FK to null on delete

Revision ID: 010_admin_actions_fk
Revises: 009_admin_actions
Create Date: 2026-04-10 21:05:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '010_admin_actions_fk'
down_revision: Union[str, None] = '009_admin_actions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('admin_actions_contest_id_fkey', 'admin_actions', type_='foreignkey')
    op.create_foreign_key(
        'admin_actions_contest_id_fkey',
        'admin_actions',
        'contests',
        ['contest_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('admin_actions_contest_id_fkey', 'admin_actions', type_='foreignkey')
    op.create_foreign_key(
        'admin_actions_contest_id_fkey',
        'admin_actions',
        'contests',
        ['contest_id'],
        ['id'],
    )
