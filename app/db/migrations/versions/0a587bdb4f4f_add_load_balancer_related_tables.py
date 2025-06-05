"""add_resilient_node_groups

Revision ID: 0a587bdb4f4f
Revises: add_custom_subscription_fields
Create Date: 2025-06-04 11:48:11.197507

"""
from alembic import op
import sqlalchemy as sa
from app.models.resilient_node_group import ClientStrategyHint


# revision identifiers, used by Alembic.
revision = '0a587bdb4f4f'
down_revision = 'add_custom_subscription_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the resilient_node_groups table
    op.create_table('resilient_node_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100, collation='NOCASE'), nullable=False),
        sa.Column('client_strategy_hint', sa.Enum(ClientStrategyHint, name='clientstrategyhint'), nullable=False, server_default=ClientStrategyHint.CLIENT_DEFAULT.name),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_resilient_node_group_name')
    )
    op.create_index(op.f('ix_resilient_node_groups_name'), 'resilient_node_groups', ['name'], unique=True)

    # Create the association table for many-to-many relationship
    op.create_table('resilient_node_group_nodes_association',
        sa.Column('resilient_node_group_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['resilient_node_group_id'], ['resilient_node_groups.id'], ),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
        sa.PrimaryKeyConstraint('resilient_node_group_id', 'node_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('resilient_node_group_nodes_association')
    op.drop_index(op.f('ix_resilient_node_groups_name'), table_name='resilient_node_groups')
    op.drop_table('resilient_node_groups')

    # Drop the enum type
    sa.Enum(ClientStrategyHint, name='clientstrategyhint').drop(op.get_bind(), checkfirst=True)
