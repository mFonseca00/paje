"""adicionar_ultima_verificacao_anvisa_a_bulas

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a1b2'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bulas', sa.Column(
        'ultima_verificacao_anvisa',
        sa.DateTime(timezone=True),
        nullable=True,
    ))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bulas', 'ultima_verificacao_anvisa')
