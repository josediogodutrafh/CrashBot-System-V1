"""add plataforma column to log_bot

Revision ID: a1b2c3d4e5f6
Revises: 35b58db7fa84
Create Date: 2026-03-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "35b58db7fa84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("log_bot", sa.Column("plataforma", sa.String(30), nullable=True))
    op.create_index("ix_log_bot_plataforma", "log_bot", ["plataforma"])


def downgrade() -> None:
    op.drop_index("ix_log_bot_plataforma", table_name="log_bot")
    op.drop_column("log_bot", "plataforma")
