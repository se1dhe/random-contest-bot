"""Add admin actions, contest publish schedule and participant number uniqueness

Revision ID: 009_admin_actions
Revises: 008_add_participant_names
Create Date: 2026-04-10 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_admin_actions'
down_revision = '008_add_participant_names'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('contests', sa.Column('publish_at', sa.DateTime(), nullable=True))

    op.create_table(
        'admin_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('actor_user_id', sa.BigInteger(), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=255), nullable=True),
        sa.Column('contest_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='success'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_actions_actor_user_id'), 'admin_actions', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_admin_actions_action_type'), 'admin_actions', ['action_type'], unique=False)
    op.create_index(op.f('ix_admin_actions_target_type'), 'admin_actions', ['target_type'], unique=False)
    op.create_index(op.f('ix_admin_actions_contest_id'), 'admin_actions', ['contest_id'], unique=False)

    op.create_index(
        'uq_participants_contest_registration_number',
        'participants',
        ['contest_id', 'registration_number'],
        unique=True
    )


def downgrade() -> None:
    op.drop_index('uq_participants_contest_registration_number', table_name='participants')
    op.drop_index(op.f('ix_admin_actions_contest_id'), table_name='admin_actions')
    op.drop_index(op.f('ix_admin_actions_target_type'), table_name='admin_actions')
    op.drop_index(op.f('ix_admin_actions_action_type'), table_name='admin_actions')
    op.drop_index(op.f('ix_admin_actions_actor_user_id'), table_name='admin_actions')
    op.drop_table('admin_actions')
    op.drop_column('contests', 'publish_at')
