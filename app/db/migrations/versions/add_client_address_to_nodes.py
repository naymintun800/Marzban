"""add_client_address_to_nodes

Revision ID: add_client_address_to_nodes
Revises: add_resilient_node_group_to_hosts
Create Date: 2025-06-05 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_client_address_to_nodes'
down_revision: str = 'add_resilient_node_group_to_hosts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists before adding it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('nodes')]

    if 'client_address' not in columns:
        # Add client_address column to nodes table
        # This is the address that clients will connect to (can be different from management address)
        op.add_column('nodes', sa.Column('client_address', sa.String(256), nullable=True))

        # For existing nodes, copy the management address as the default client address
        # This ensures backward compatibility
        op.execute("UPDATE nodes SET client_address = address WHERE client_address IS NULL")


def downgrade() -> None:
    # Drop the client_address column
    op.drop_column('nodes', 'client_address')
