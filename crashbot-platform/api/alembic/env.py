"""
Alembic ENV - Configuração para migrações do CrashBot
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Adiciona o diretório raiz ao path para importar os módulos da app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa as configurações e modelos do projeto
from app.config import settings
from app.database import Base

# Importa TODOS os modelos para o Alembic detectar
from app.models.licenca import Licenca
from app.models.log_bot import LogBot
from app.models.usuario import Usuario
from app.models.versao_bot import VersaoBot

# Configuração do Alembic
config = context.config

# Configura o SQLAlchemy URL a partir das settings
# (sobrescreve o valor do alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configura logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData dos modelos para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Executa migrações em modo 'offline'.
    Gera SQL sem conectar no banco.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executa migrações em modo 'online'.
    Conecta no banco e aplica as mudanças.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
