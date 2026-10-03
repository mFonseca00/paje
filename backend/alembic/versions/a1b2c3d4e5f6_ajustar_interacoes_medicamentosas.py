"""ajustar_interacoes_medicamentosas

Revision ID: a1b2c3d4e5f6
Revises: ec401c233308
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ec401c233308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # (a) Renomear substancia → referencia
    op.alter_column('interacoes_medicamentosas', 'substancia', new_column_name='referencia')

    # (b) Adicionar coluna tipo VARCHAR NOT NULL
    # server_default temporário para lidar com linhas existentes
    op.add_column(
        'interacoes_medicamentosas',
        sa.Column('tipo', sa.String(20), nullable=False, server_default='NOME_DIRETO'),
    )
    op.alter_column('interacoes_medicamentosas', 'tipo', server_default=None)

    # (c) Tornar efeito nullable
    op.alter_column(
        'interacoes_medicamentosas',
        'efeito',
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'interacoes_medicamentosas',
        'efeito',
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column('interacoes_medicamentosas', 'tipo')
    op.alter_column('interacoes_medicamentosas', 'referencia', new_column_name='substancia')
