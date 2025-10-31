"""add role to histories table

Revision ID: 06e990cb07eb
Revises: aa8aa6eb6dd0
Create Date: 2025-10-31 01:52:01.434542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06e990cb07eb'
down_revision: Union[str, Sequence[str], None] = 'aa8aa6eb6dd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('histories', sa.Column('role', sa.Enum('USER', 'AI', name='message_role'), nullable=False, server_default='USER'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('histories', 'role')
