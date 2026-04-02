import asyncio

from app.database import engine
from sqlalchemy import text


async def adicionar_cpf():
    async with engine.begin() as conn:
        # Verificar se coluna existe
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'licenca' AND column_name = 'cpf'"
            )
        )
        if result.fetchone():
            print("Coluna CPF ja existe!")
        else:
            await conn.execute(text("ALTER TABLE licenca ADD COLUMN cpf VARCHAR(14)"))
            print("Coluna CPF adicionada com sucesso!")


asyncio.run(adicionar_cpf())
