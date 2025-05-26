"""add custom subscription fields

Revision ID: add_custom_subscription_fields
Revises: merge_subscription_path_heads
Create Date: 2024-03-19 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_custom_subscription_fields'
down_revision: Union[str, None] = 'merge_subscription_path_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add custom_subscription_path column
    op.add_column('users', sa.Column('custom_subscription_path', sa.String(256), nullable=True))
    # Add custom_uuid column
    op.add_column('users', sa.Column('custom_uuid', sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'custom_uuid')
    op.drop_column('users', 'custom_subscription_path') 