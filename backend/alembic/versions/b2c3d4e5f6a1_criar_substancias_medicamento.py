"""criar_substancias_medicamento

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'substancias_medicamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('medicamento_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(['medicamento_id'], ['medicamentos.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('substancias_medicamento')
