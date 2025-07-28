"""add_custom_features_resilient_groups_custom_subscriptions

Revision ID: 481347e36c6a
Revises: 3c466ce2ab63
Create Date: 2025-07-28 22:29:51.415874

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '481347e36c6a'
down_revision = '3c466ce2ab63'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum for client strategy hint (SQLite doesn't need explicit enum creation)
    client_strategy_hint_enum = sa.Enum(
        'url-test', 'fallback', 'load-balance', 'client-default', '',
        name='clientstrategyhint'
    )
    
    # Only create enum if not SQLite
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        client_strategy_hint_enum.create(bind)

    # Create resilient_node_groups table
    op.create_table(
        'resilient_node_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('client_strategy_hint', client_strategy_hint_enum, nullable=False, server_default='client-default'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resilient_node_groups_name'), 'resilient_node_groups', ['name'], unique=True)

    # Create association table for resilient node groups and nodes
    op.create_table(
        'resilient_node_group_nodes_association',
        sa.Column('resilient_node_group_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
        sa.ForeignKeyConstraint(['resilient_node_group_id'], ['resilient_node_groups.id'], ),
        sa.PrimaryKeyConstraint('resilient_node_group_id', 'node_id')
    )

    # Add resilient_node_group_id to hosts table
    with op.batch_alter_table('hosts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resilient_node_group_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_hosts_resilient_node_group_id', 'resilient_node_groups', 
            ['resilient_node_group_id'], ['id']
        )

    # Add custom subscription fields to users table
    op.add_column('users', sa.Column('custom_subscription_path', sa.String(length=256), nullable=True))
    op.add_column('users', sa.Column('custom_uuid', sa.String(length=256), nullable=True))
    
    # Create unique index on custom_uuid
    op.create_index(op.f('ix_users_custom_uuid'), 'users', ['custom_uuid'], unique=True)


def downgrade() -> None:
    # Remove custom subscription fields from users table
    op.drop_index(op.f('ix_users_custom_uuid'), table_name='users')
    op.drop_column('users', 'custom_uuid')
    op.drop_column('users', 'custom_subscription_path')

    # Remove resilient_node_group_id from hosts table
    with op.batch_alter_table('hosts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_hosts_resilient_node_group_id', type_='foreignkey')
        batch_op.drop_column('resilient_node_group_id')

    # Drop association table
    op.drop_table('resilient_node_group_nodes_association')

    # Drop resilient_node_groups table
    op.drop_index(op.f('ix_resilient_node_groups_name'), table_name='resilient_node_groups')
    op.drop_table('resilient_node_groups')

    # Drop enum (only if not SQLite)
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.execute('DROP TYPE clientstrategyhint')
