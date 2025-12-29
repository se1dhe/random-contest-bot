"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу channels
    op.create_table(
        'channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('channel_username', sa.String(length=255), nullable=True),
        sa.Column('channel_title', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_id')
    )
    op.create_index(op.f('ix_channels_channel_id'), 'channels', ['channel_id'], unique=False)
    
    # Создаем таблицу contests
    op.create_table(
        'contests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('message_id', sa.BigInteger(), nullable=True),
        sa.Column('results_message_id', sa.BigInteger(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'FINISHED', 'RESULTS_PUBLISHED', name='conteststatus'), nullable=False),
        sa.Column('draw_method', sa.Enum('RANDOM', 'BY_ACTIVITY', name='contestdrawmethod'), nullable=False),
        sa.Column('prize_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contests_channel_id'), 'contests', ['channel_id'], unique=False)
    op.create_index(op.f('ix_contests_status'), 'contests', ['status'], unique=False)
    
    # Создаем таблицу prizes
    op.create_table(
        'prizes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('place', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('winner_user_id', sa.Integer(), nullable=True),
        sa.Column('winner_username', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prizes_contest_id'), 'prizes', ['contest_id'], unique=False)
    
    # Создаем таблицу participants
    op.create_table(
        'participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('registration_number', sa.Integer(), nullable=False),
        sa.Column('registered_at', sa.DateTime(), nullable=False),
        sa.Column('activity_score', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contest_id', 'user_id', name='uq_contest_user')
    )
    op.create_index(op.f('ix_participants_contest_id'), 'participants', ['contest_id'], unique=False)
    op.create_index(op.f('ix_participants_user_id'), 'participants', ['user_id'], unique=False)
    
    # Создаем таблицу sponsors
    op.create_table(
        'sponsors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('channel_username', sa.String(length=255), nullable=True),
        sa.Column('channel_title', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sponsors_contest_id'), 'sponsors', ['contest_id'], unique=False)
    op.create_index(op.f('ix_sponsors_channel_id'), 'sponsors', ['channel_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sponsors_channel_id'), table_name='sponsors')
    op.drop_index(op.f('ix_sponsors_contest_id'), table_name='sponsors')
    op.drop_table('sponsors')
    op.drop_index(op.f('ix_participants_user_id'), table_name='participants')
    op.drop_index(op.f('ix_participants_contest_id'), table_name='participants')
    op.drop_table('participants')
    op.drop_index(op.f('ix_prizes_contest_id'), table_name='prizes')
    op.drop_table('prizes')
    op.drop_index(op.f('ix_contests_status'), table_name='contests')
    op.drop_index(op.f('ix_contests_channel_id'), table_name='contests')
    op.drop_table('contests')
    op.drop_index(op.f('ix_channels_channel_id'), table_name='channels')
    op.drop_table('channels')
    op.execute('DROP TYPE conteststatus')
    op.execute('DROP TYPE contestdrawmethod')

