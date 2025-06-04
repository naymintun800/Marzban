"""add is_public to nodes and node_id to hosts

Revision ID: d5e7c2742b95
Revises: add_custom_subscription_fields
Create Date: 2025-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd5e7c2742b95'
down_revision = 'add_custom_subscription_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('nodes', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('1')))
    op.add_column('hosts', sa.Column('node_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'hosts', 'nodes', ['node_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'hosts', type_='foreignkey')
    op.drop_column('hosts', 'node_id')
    op.drop_column('nodes', 'is_public')
