"""fix_migration_chain

Revision ID: fix_migration_chain
Revises: add_resilient_node_group_to_hosts
Create Date: 2025-06-05 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_migration_chain'
down_revision: str = 'add_resilient_node_group_to_hosts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration fixes the chain after removing client_address migration
    # No actual schema changes needed
    pass


def downgrade() -> None:
    # No changes to revert
    pass
