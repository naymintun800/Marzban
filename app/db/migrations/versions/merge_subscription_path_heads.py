"""merge subscription path heads

Revision ID: merge_subscription_path_heads
Revises: add_subscription_path_and_token, 07f9bbb3db4e, 08b381fc1bc7, 0f720f5c54dd, 1ad79b97fdcf, 1cf7d159fdbb, 21226bc711ac, 2313cdc30da3, 2b231de97dc3, 2ea33513efc0, 305943d779c4, 31f92220c0d0, 35f7f8fa9cf2, 37692c1c9715, 3cf36a5fde73, 470465472326, 4f045f53bef8, 51e941ed9018, 54c4b8c525fc, 5575fe410515, 57fda18cd9e6, 5a4446e7b165, 5b84d88804a1, 671621870b02, 714f227201a7, 77c86a261126, 7a0dbb8a2f65, 7cbe9d91ac11, 852d951c9c08, 8e849e06f131, 947ebbd8debe, 94a5cc12c0d6, 97dd9311ab93, 9b60be6cd0a2, 9d5a518ae432, a0715c2615f0, a0d3d400ea75, a6e3fff39291, a9cfd5611a82, adda2dd4a741, b15eba6e5867, b25e7e6be241, b3378dc6de01, be0c5f840473, c106bb40c861, c3cd674b9bcd, c47250b790eb, ccbf9d322ae3, d02dcfbf1517, d0a3960f5dad, dd725e4d3628, e3f0e888a563, e410e5f15c3f, e4a86bc8ec7b, e56f1c781e46, e7b869e999b4, e91236993f1a, ece13c4c6f65, fad8b1997c3a, fc01b1520e72, fe7796f840a4, 015cf1dc6eca
Create Date: 2024-03-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_subscription_path_heads'
down_revision: Union[str, Sequence[str], None] = (
    'add_subscription_path_and_token', '07f9bbb3db4e', '08b381fc1bc7', '0f720f5c54dd', 
    '1ad79b97fdcf', '1cf7d159fdbb', '21226bc711ac', '2313cdc30da3', '2b231de97dc3', 
    '2ea33513efc0', '305943d779c4', '31f92220c0d0', '35f7f8fa9cf2', '37692c1c9715', 
    '3cf36a5fde73', '470465472326', '4f045f53bef8', '51e941ed9018', '54c4b8c525fc', 
    '5575fe410515', '57fda18cd9e6', '5a4446e7b165', '5b84d88804a1', '671621870b02', 
    '714f227201a7', '77c86a261126', '7a0dbb8a2f65', '7cbe9d91ac11', '852d951c9c08', 
    '8e849e06f131', '947ebbd8debe', '94a5cc12c0d6', '97dd9311ab93', '9b60be6cd0a2', 
    '9d5a518ae432', 'a0715c2615f0', 'a0d3d400ea75', 'a6e3fff39291', 'a9cfd5611a82', 
    'adda2dd4a741', 'b15eba6e5867', 'b25e7e6be241', 'b3378dc6de01', 'be0c5f840473', 
    'c106bb40c861', 'c3cd674b9bcd', 'c47250b790eb', 'ccbf9d322ae3', 'd02dcfbf1517', 
    'd0a3960f5dad', 'dd725e4d3628', 'e3f0e888a563', 'e410e5f15c3f', 'e4a86bc8ec7b', 
    'e56f1c781e46', 'e7b869e999b4', 'e91236993f1a', 'ece13c4c6f65', 'fad8b1997c3a', 
    'fc01b1520e72', 'fe7796f840a4', '015cf1dc6eca'
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 