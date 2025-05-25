"""add custom subscription fields

Revision ID: add_custom_subscription_fields
Revises: # You'll need to replace this with the previous migration ID
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_custom_subscription_fields'
down_revision = None  # Replace with previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Add custom_subscription_path column
    op.add_column('user', sa.Column('custom_subscription_path', sa.String(), nullable=True))
    # Add custom_uuid column
    op.add_column('user', sa.Column('custom_uuid', sa.String(), nullable=True))
    # Create index for faster lookups
    op.create_index(op.f('ix_user_custom_subscription_path'), 'user', ['custom_subscription_path'], unique=False)
    op.create_index(op.f('ix_user_custom_uuid'), 'user', ['custom_uuid'], unique=True)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_user_custom_uuid'), table_name='user')
    op.drop_index(op.f('ix_user_custom_subscription_path'), table_name='user')
    # Drop columns
    op.drop_column('user', 'custom_uuid')
    op.drop_column('user', 'custom_subscription_path') 