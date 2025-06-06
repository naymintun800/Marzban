"""Add node performance tracking

Revision ID: add_node_performance_tracking
Revises: 0a587bdb4f4f
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_node_performance_tracking'
down_revision = '0a587bdb4f4f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add performance tracking fields to nodes table
    op.add_column('nodes', sa.Column('avg_response_time', sa.Float(), nullable=True))
    op.add_column('nodes', sa.Column('success_rate', sa.Float(), nullable=True))
    op.add_column('nodes', sa.Column('last_performance_check', sa.DateTime(), nullable=True))
    op.add_column('nodes', sa.Column('active_connections', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('nodes', sa.Column('total_connections', sa.BigInteger(), nullable=False, server_default='0'))

    # Create node_performance_metrics table
    op.create_table('node_performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('response_time', sa.Float(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('created_at', 'node_id')
    )
    op.create_index(op.f('ix_node_performance_metrics_node_id'), 'node_performance_metrics', ['node_id'], unique=False)

    # Create node_connection_logs table
    op.create_table('node_connection_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subscription_token', sa.String(length=256), nullable=True),
        sa.Column('connected_at', sa.DateTime(), nullable=False),
        sa.Column('disconnected_at', sa.DateTime(), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('client_ip', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_node_connection_logs_node_id'), 'node_connection_logs', ['node_id'], unique=False)
    op.create_index(op.f('ix_node_connection_logs_user_id'), 'node_connection_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_node_connection_logs_connected_at'), 'node_connection_logs', ['connected_at'], unique=False)


def downgrade() -> None:
    # Drop indexes and tables
    op.drop_index(op.f('ix_node_connection_logs_connected_at'), table_name='node_connection_logs')
    op.drop_index(op.f('ix_node_connection_logs_user_id'), table_name='node_connection_logs')
    op.drop_index(op.f('ix_node_connection_logs_node_id'), table_name='node_connection_logs')
    op.drop_table('node_connection_logs')
    
    op.drop_index(op.f('ix_node_performance_metrics_node_id'), table_name='node_performance_metrics')
    op.drop_table('node_performance_metrics')

    # Remove performance tracking fields from nodes table
    op.drop_column('nodes', 'total_connections')
    op.drop_column('nodes', 'active_connections')
    op.drop_column('nodes', 'last_performance_check')
    op.drop_column('nodes', 'success_rate')
    op.drop_column('nodes', 'avg_response_time')
