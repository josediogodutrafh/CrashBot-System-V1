"""add_telemetria_fields_to_log_bot

Revision ID: 35b58db7fa84
Revises: 2cfd5cc76c16
Create Date: 2025-12-11 15:57:21.617801

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "35b58db7fa84"
down_revision: Union[str, Sequence[str], None] = "2cfd5cc76c16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Adiciona campos de telemetria ao log_bot."""
    # Novos campos de telemetria
    op.add_column("log_bot", sa.Column("licenca_id", sa.Integer(), nullable=True))
    op.add_column("log_bot", sa.Column("saldo", sa.Float(), nullable=True))
    op.add_column("log_bot", sa.Column("valor_aposta", sa.Float(), nullable=True))
    op.add_column("log_bot", sa.Column("banca_inicial", sa.Float(), nullable=True))
    op.add_column("log_bot", sa.Column("banca_final", sa.Float(), nullable=True))
    op.add_column(
        "log_bot", sa.Column("modo_risco", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "log_bot", sa.Column("estrategia", sa.String(length=100), nullable=True)
    )
    op.add_column("log_bot", sa.Column("target", sa.Float(), nullable=True))
    op.add_column("log_bot", sa.Column("explosao", sa.Float(), nullable=True))
    op.add_column(
        "log_bot", sa.Column("resultado", sa.String(length=10), nullable=True)
    )
    op.add_column("log_bot", sa.Column("sequencia_perdas", sa.Integer(), nullable=True))
    op.add_column(
        "log_bot", sa.Column("stop_loss_atingido", sa.String(length=1), nullable=True)
    )
    op.add_column(
        "log_bot", sa.Column("meta_atingida", sa.String(length=1), nullable=True)
    )
    op.add_column(
        "log_bot", sa.Column("versao_bot", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "log_bot", sa.Column("sistema_operacional", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "log_bot", sa.Column("ip_cliente", sa.String(length=45), nullable=True)
    )

    # Índices para performance
    op.create_index(
        op.f("ix_log_bot_licenca_id"), "log_bot", ["licenca_id"], unique=False
    )
    op.create_index(
        op.f("ix_log_bot_modo_risco"), "log_bot", ["modo_risco"], unique=False
    )
    op.create_index(
        op.f("ix_log_bot_resultado"), "log_bot", ["resultado"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema - Remove campos de telemetria do log_bot."""
    op.drop_index(op.f("ix_log_bot_resultado"), table_name="log_bot")
    op.drop_index(op.f("ix_log_bot_modo_risco"), table_name="log_bot")
    op.drop_index(op.f("ix_log_bot_licenca_id"), table_name="log_bot")
    op.drop_column("log_bot", "ip_cliente")
    op.drop_column("log_bot", "sistema_operacional")
    op.drop_column("log_bot", "versao_bot")
    op.drop_column("log_bot", "meta_atingida")
    op.drop_column("log_bot", "stop_loss_atingido")
    op.drop_column("log_bot", "sequencia_perdas")
    op.drop_column("log_bot", "resultado")
    op.drop_column("log_bot", "explosao")
    op.drop_column("log_bot", "target")
    op.drop_column("log_bot", "estrategia")
    op.drop_column("log_bot", "modo_risco")
    op.drop_column("log_bot", "banca_final")
    op.drop_column("log_bot", "banca_inicial")
    op.drop_column("log_bot", "valor_aposta")
    op.drop_column("log_bot", "saldo")
    op.drop_column("log_bot", "licenca_id")
