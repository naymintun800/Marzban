"""Beta-2 custom features migration

Revision ID: 20250729120000
Revises: 
Create Date: 2025-07-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '20250729120000'
down_revision: Union[str, None] = 'e422f859847f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create resilient_node_groups table
    op.create_table('resilient_node_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('client_strategy_hint', sa.Enum('CLIENT_DEFAULT', 'URL_TEST', 'BALANCE', 'ROUND_ROBIN', name='clientstrategyhint'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_resilient_node_groups_name'), 'resilient_node_groups', ['name'], unique=False)

    # Create resilient_node_group_nodes_association table
    op.create_table('resilient_node_group_nodes_association',
        sa.Column('resilient_node_group_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
        sa.ForeignKeyConstraint(['resilient_node_group_id'], ['resilient_node_groups.id'], ),
        sa.PrimaryKeyConstraint('resilient_node_group_id', 'node_id')
    )

    # Add custom subscription fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('custom_subscription_path', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('custom_uuid', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_custom_subscription_path'), ['custom_subscription_path'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_custom_uuid'), ['custom_uuid'], unique=False)


def downgrade() -> None:
    # Remove custom subscription fields from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_custom_uuid'))
        batch_op.drop_index(batch_op.f('ix_users_custom_subscription_path'))
        batch_op.drop_column('custom_uuid')
        batch_op.drop_column('custom_subscription_path')

    # Drop resilient_node_group_nodes_association table
    op.drop_table('resilient_node_group_nodes_association')
    
    # Drop resilient_node_groups table
    op.drop_index(op.f('ix_resilient_node_groups_name'), table_name='resilient_node_groups')
    op.drop_table('resilient_node_groups')