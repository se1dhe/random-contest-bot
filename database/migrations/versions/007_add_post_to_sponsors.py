from alembic import op
import sqlalchemy as sa

revision = '007_add_post_to_sponsors'
down_revision = '3e402fc74e61'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('contests', sa.Column('post_to_sponsors', sa.Boolean(), nullable=False, server_default='false'))

def downgrade() -> None:
    op.drop_column('contests', 'post_to_sponsors')
