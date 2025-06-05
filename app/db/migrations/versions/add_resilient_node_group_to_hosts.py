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
    # Add resilient_node_group_id column to hosts table
    op.add_column('hosts', sa.Column('resilient_node_group_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_hosts_resilient_node_group_id',
        'hosts', 
        'resilient_node_groups',
        ['resilient_node_group_id'], 
        ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for better query performance
    op.create_index('ix_hosts_resilient_node_group_id', 'hosts', ['resilient_node_group_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_hosts_resilient_node_group_id', table_name='hosts')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_hosts_resilient_node_group_id', 'hosts', type_='foreignkey')
    
    # Drop column
    op.drop_column('hosts', 'resilient_node_group_id')
