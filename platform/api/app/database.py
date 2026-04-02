"""
Database - Configuração SQLAlchemy 2.0
"""

from typing import AsyncGenerator

from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# ============================================================================
# CONFIGURAÇÃO DO SQLALCHEMY
# ============================================================================

# Converter URL para async (FastAPI funciona melhor com async)
# postgresql://... → postgresql+asyncpg://...
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Engine assíncrona
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,  # Log de queries em desenvolvimento
    future=True,
    pool_pre_ping=True,  # Verifica conexão antes de usar
    pool_size=10,  # Número de conexões no pool
    max_overflow=20,  # Conexões extras se necessário
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    # autocommit=False não é necessário/suportado no estilo 2.0 (padrão é transacional)
)

# Base para modelos
Base = declarative_base()


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para obter sessão do banco de dados.

    Uso:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Model))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# UTILITÁRIOS
# ============================================================================


async def init_db():
    """
    Inicializa o banco de dados.
    Cria todas as tabelas definidas nos modelos.

    IMPORTANTE: Em produção, use Alembic para migrations!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection() -> bool:
    """
    Verifica se a conexão com o banco está funcionando.

    Returns:
        bool: True se conectado, False caso contrário
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Erro ao conectar no banco: {e}")
        return False
