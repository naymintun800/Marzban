"""merge resilient and load balancer heads

Revision ID: merge_resilient_and_load_balancer_heads
Revises: 0a587bdb4f4f, c83bf33c0b66
Create Date: 2025-06-05 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_resilient_and_load_balancer_heads'
down_revision: Union[str, Sequence[str], None] = ('0a587bdb4f4f', 'c83bf33c0b66')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is a merge migration - no changes needed
    # Both parent migrations have already created their respective tables
    pass


def downgrade() -> None:
    # This is a merge migration - no changes needed
    # Downgrading will revert to the individual parent migrations
    pass
