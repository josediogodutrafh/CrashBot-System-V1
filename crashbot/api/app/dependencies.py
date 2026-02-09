"""
Dependencies - Autenticação e Autorização
"""

from app.database import get_db
from app.models import Usuario
from app.services.auth_service import decode_access_token
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Security scheme para tokens JWT
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """
    Dependency que valida o token JWT e retorna o usuário atual.

    Args:
        credentials: Token JWT enviado no header Authorization
        db: Sessão do banco de dados

    Returns:
        Usuario: Usuário autenticado

    Raises:
        HTTPException: Se token inválido ou usuário não encontrado
    """
    # Pegar o token
    token = credentials.credentials

    # Decodificar token
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Pegar user_id do payload
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Buscar usuário no banco
    result = await db.execute(select(Usuario).where(Usuario.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar se usuário está ativo
    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado",
        )

    return user


async def get_current_admin(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """
    Dependency que valida se o usuário é admin.

    Args:
        current_user: Usuário atual (validado por get_current_user)

    Returns:
        Usuario: Usuário admin

    Raises:
        HTTPException: Se usuário não é admin
    """
    if current_user.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente. Apenas admins podem acessar.",
        )

    return current_user
