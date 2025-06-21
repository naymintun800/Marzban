"""add_resilient_node_group_to_hosts

Revision ID: add_resilient_node_group_to_hosts
Revises: merge_resilient_and_load_balancer_heads
Create Date: 2025-06-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_resilient_node_group_to_hosts'
down_revision: str = 'merge_resilient_and_load_balancer_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('hosts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resilient_node_group_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_hosts_resilient_node_group_id',
            'resilient_node_groups',
            ['resilient_node_group_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_hosts_resilient_node_group_id', ['resilient_node_group_id'])


def downgrade() -> None:
    with op.batch_alter_table('hosts', schema=None) as batch_op:
        batch_op.drop_index('ix_hosts_resilient_node_group_id')
        batch_op.drop_constraint('fk_hosts_resilient_node_group_id', type_='foreignkey')
        batch_op.drop_column('resilient_node_group_id')
