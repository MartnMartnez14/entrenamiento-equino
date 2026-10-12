"""Persist timing entry mode, preserving existing split data."""
from alembic import op
import sqlalchemy as sa
revision = 'c631final'
down_revision = '265a276adee0'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('training_sessions', sa.Column('timing_mode', sa.String(20), nullable=False, server_default='split'))

def downgrade():
    with op.batch_alter_table('training_sessions') as batch:
        batch.drop_column('timing_mode')
