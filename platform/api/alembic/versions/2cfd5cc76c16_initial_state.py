"""initial_state

Revision ID: 2cfd5cc76c16
Revises:
Create Date: 2025-12-08 12:03:50.209322

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2cfd5cc76c16"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adiciona apenas os novos campos para controle de promoções
    op.add_column(
        "licenca",
        sa.Column(
            "is_trial", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "licenca",
        sa.Column(
            "is_primeira_adesao",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("licenca", "is_primeira_adesao")
    op.drop_column("licenca", "is_trial")
