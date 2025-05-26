"""merge subscription path heads

Revision ID: merge_subscription_path_heads
Revises: add_subscription_path_and_token, 2b231de97dc3
Create Date: 2024-03-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_subscription_path_heads'
down_revision: Union[str, Sequence[str], None] = ('add_subscription_path_and_token', '2b231de97dc3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 