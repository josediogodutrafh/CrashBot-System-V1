"""
Script: Criar Primeiro Usuário Admin
Cria um usuário admin no banco de dados.
"""

import asyncio

from app.database import AsyncSessionLocal, Base, engine
from app.models import Usuario
from app.services.auth_service import get_password_hash
from sqlalchemy import select


async def create_admin():
    """Cria usuário admin padrão."""

    print("🔧 Criando tabelas no banco...")

    # Criar todas as tabelas (se não existirem)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Tabelas criadas/verificadas!")

    # Dados do admin
    admin_email = "admin@crashbot.com"
    admin_password = "admin123"  # MUDE ESTA SENHA EM PRODUÇÃO!
    admin_nome = "Administrador"

    # Criar sessão
    async with AsyncSessionLocal() as session:
        # Verificar se admin já existe
        result = await session.execute(
            select(Usuario).where(Usuario.email == admin_email)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print(f"⚠️  Admin já existe: {admin_email}")
            return

        # Criar hash da senha
        senha_hash = get_password_hash(admin_password)

        # Criar novo admin
        admin = Usuario(
            email=admin_email,
            senha_hash=senha_hash,
            nome=admin_nome,
            is_admin=True,
            is_active=True,
        )

        session.add(admin)
        await session.commit()

        print(f"✅ Admin criado com sucesso!")
        print(f"📧 Email: {admin_email}")
        print(f"🔑 Senha: {admin_password}")
        print(f"⚠️  IMPORTANTE: Mude a senha após primeiro login!")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 CRIAR USUÁRIO ADMIN")
    print("=" * 60)

    asyncio.run(create_admin())

    print("=" * 60)
    print("✅ CONCLUÍDO!")
    print("=" * 60)
