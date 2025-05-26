"""add subscription path and token

Revision ID: add_subscription_path_and_token
Revises: 025d427831dd
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from alembic.context import get_context


# revision identifiers, used by Alembic.
revision: str = 'add_subscription_path_and_token'
down_revision: Union[str, None] = '025d427831dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if we're using SQLite
    context = get_context()
    if context.dialect.name == 'sqlite':
        # For SQLite, we need to use batch mode to add columns with constraints
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('subscription_path', sa.String(256), nullable=True))
            batch_op.add_column(sa.Column('subscription_token', sa.String(256), nullable=True))
            batch_op.create_unique_constraint('uq_users_subscription_path', ['subscription_path'])
            batch_op.create_unique_constraint('uq_users_subscription_token', ['subscription_token'])
    else:
        # For other databases like MySQL or PostgreSQL
        op.add_column('users', sa.Column('subscription_path', sa.String(256), unique=True, nullable=True))
        op.add_column('users', sa.Column('subscription_token', sa.String(256), unique=True, nullable=True))


def downgrade() -> None:
    # Check if we're using SQLite
    context = get_context()
    if context.dialect.name == 'sqlite':
        # For SQLite, we need to use batch mode to remove columns with constraints
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_constraint('uq_users_subscription_path', type_='unique')
            batch_op.drop_constraint('uq_users_subscription_token', type_='unique')
            batch_op.drop_column('subscription_path')
            batch_op.drop_column('subscription_token')
    else:
        # For other databases like MySQL or PostgreSQL
        op.drop_column('users', 'subscription_path')
        op.drop_column('users', 'subscription_token') 