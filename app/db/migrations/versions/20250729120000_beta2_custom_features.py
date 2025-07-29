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
    # Check if resilient_node_groups table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create resilient_node_groups table only if it doesn't exist
    if 'resilient_node_groups' not in existing_tables:
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

    # Create association table only if it doesn't exist
    if 'resilient_node_group_nodes_association' not in existing_tables:
        op.create_table('resilient_node_group_nodes_association',
            sa.Column('resilient_node_group_id', sa.Integer(), nullable=False),
            sa.Column('node_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
            sa.ForeignKeyConstraint(['resilient_node_group_id'], ['resilient_node_groups.id'], ),
            sa.PrimaryKeyConstraint('resilient_node_group_id', 'node_id')
        )

    # Add custom subscription fields to users table if they don't exist
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'custom_subscription_path' not in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('custom_subscription_path', sa.String(length=100), nullable=True))
            batch_op.create_index(batch_op.f('ix_users_custom_subscription_path'), ['custom_subscription_path'], unique=False)
    
    if 'custom_uuid' not in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('custom_uuid', sa.String(length=36), nullable=True))
            batch_op.create_index(batch_op.f('ix_users_custom_uuid'), ['custom_uuid'], unique=False)

    # Add resilient_node_group_id to hosts table if it doesn't exist
    host_columns = [col['name'] for col in inspector.get_columns('hosts')]
    
    if 'resilient_node_group_id' not in host_columns:
        with op.batch_alter_table('hosts', schema=None) as batch_op:
            batch_op.add_column(sa.Column('resilient_node_group_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_hosts_resilient_node_group_id', 'resilient_node_groups', ['resilient_node_group_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # Remove custom subscription fields from users table
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Remove resilient_node_group_id from hosts table
    host_columns = [col['name'] for col in inspector.get_columns('hosts')]
    if 'resilient_node_group_id' in host_columns:
        with op.batch_alter_table('hosts', schema=None) as batch_op:
            batch_op.drop_constraint('fk_hosts_resilient_node_group_id', type_='foreignkey')
            batch_op.drop_column('resilient_node_group_id')
    
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'custom_uuid' in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_users_custom_uuid'))
            batch_op.drop_column('custom_uuid')
    
    if 'custom_subscription_path' in user_columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_users_custom_subscription_path'))
            batch_op.drop_column('custom_subscription_path')

    # Drop tables if they exist
    existing_tables = inspector.get_table_names()
    
    if 'resilient_node_group_nodes_association' in existing_tables:
        op.drop_table('resilient_node_group_nodes_association')
    
    if 'resilient_node_groups' in existing_tables:
        op.drop_index(op.f('ix_resilient_node_groups_name'), table_name='resilient_node_groups')
        op.drop_table('resilient_node_groups')