"""add_session_fields_to_log_bot

Revision ID: a1b2c3d4e5f6
Revises: 35b58db7fa84
Create Date: 2025-12-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "35b58db7fa84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona campos de sessão ao log_bot."""
    op.add_column("log_bot", sa.Column("dobra_atual", sa.Integer(), nullable=True))
    op.add_column("log_bot", sa.Column("total_rodadas", sa.Integer(), nullable=True))
    op.add_column(
        "log_bot", sa.Column("tempo_sessao_segundos", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Remove campos de sessão do log_bot."""
    op.drop_column("log_bot", "tempo_sessao_segundos")
    op.drop_column("log_bot", "total_rodadas")
    op.drop_column("log_bot", "dobra_atual")
