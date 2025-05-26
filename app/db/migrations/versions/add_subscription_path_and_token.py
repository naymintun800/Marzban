"""add subscription path and token

Revision ID: add_subscription_path_and_token
Revises: 025d427831dd
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_subscription_path_and_token'
down_revision: Union[str, None] = '025d427831dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add subscription_path and subscription_token columns to users table
    op.add_column('users', sa.Column('subscription_path', sa.String(256), unique=True, nullable=True))
    op.add_column('users', sa.Column('subscription_token', sa.String(256), unique=True, nullable=True))


def downgrade() -> None:
    # Remove subscription_path and subscription_token columns from users table
    op.drop_column('users', 'subscription_path')
    op.drop_column('users', 'subscription_token') 