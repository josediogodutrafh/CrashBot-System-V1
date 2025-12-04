"""
Router: Autenticação
Endpoints para login, registro e gerenciamento de usuários.
"""

from datetime import datetime, timezone

# Adicionado cast e Optional para tipagem correta
from typing import List

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.models import Usuario
from app.schemas.auth import LoginRequest, LoginResponse, UsuarioCreate, UsuarioResponse
from app.services.auth_service import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ============================================================================
# ENDPOINT: LOGIN
# ============================================================================


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Faz login e retorna token JWT.

    Args:
        credentials: Email e senha

    Returns:
        LoginResponse: Token JWT e dados do usuário
    """
    # Buscar usuário por email
    result = await db.execute(select(Usuario).where(Usuario.email == credentials.email))
    user = result.scalar_one_or_none()

    # Verificar se usuário existe
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    # Verificar senha
    # CORREÇÃO PYLANCE: Cast para garantir que senha_hash é string
    senha_hash_str = str(user.senha_hash)
    if not verify_password(credentials.password, senha_hash_str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    # Verificar se usuário está ativo
    # CORREÇÃO PYLANCE: Comparação explícita com False
    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado",
        )

    # Atualizar last_login
    # CORREÇÃO PYLANCE: type ignore para atribuição em Column
    user.last_login = datetime.now(timezone.utc)  # type: ignore
    await db.commit()

    # Criar token JWT
    access_token = create_access_token(
        data={"sub": str(user.id), "email": str(user.email)}
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.to_dict(),
    )


# ============================================================================
# ENDPOINT: REGISTRAR USUÁRIO (apenas admin pode criar outros usuários)
# ============================================================================


@router.post("/register", response_model=UsuarioResponse)
async def register(
    user_data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Registra novo usuário (apenas admin).

    Args:
        user_data: Dados do novo usuário
        current_admin: Admin autenticado

    Returns:
        UsuarioResponse: Dados do usuário criado
    """
    # Verificar se email já existe (CORREÇÃO SOURCERY: Walrus Operator)
    result = await db.execute(select(Usuario).where(Usuario.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado",
        )

    # Criar hash da senha
    senha_hash = get_password_hash(user_data.password)

    # Criar novo usuário
    new_user = Usuario(
        email=user_data.email,
        senha_hash=senha_hash,
        nome=user_data.nome,
        is_admin=user_data.is_admin,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# ============================================================================
# ENDPOINT: OBTER USUÁRIO ATUAL
# ============================================================================


@router.get("/me", response_model=UsuarioResponse)
async def get_me(
    current_user: Usuario = Depends(get_current_user),
):
    """
    Retorna dados do usuário autenticado.

    Args:
        current_user: Usuário autenticado

    Returns:
        UsuarioResponse: Dados do usuário
    """
    return current_user


# ============================================================================
# ENDPOINT: ALTERAR SENHA
# ============================================================================


@router.put("/change-password")
async def change_password(
    senha_atual: str,
    nova_senha: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Altera a senha do usuário autenticado.

    Args:
        senha_atual: Senha atual
        nova_senha: Nova senha
        current_user: Usuário autenticado

    Returns:
        dict: Mensagem de sucesso
    """
    # Verificar senha atual
    # CORREÇÃO PYLANCE: Cast explícito para str
    current_hash = str(current_user.senha_hash)
    if not verify_password(senha_atual, current_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )

    # Validar nova senha
    if len(nova_senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ter pelo menos 6 caracteres",
        )

    # Atualizar senha
    # CORREÇÃO PYLANCE: type ignore para atribuição
    current_user.senha_hash = get_password_hash(nova_senha)  # type: ignore
    await db.commit()

    return {"message": "Senha alterada com sucesso"}


# ============================================================================
# ENDPOINT: LISTAR USUÁRIOS (apenas admin)
# ============================================================================


@router.get("/users", response_model=List[UsuarioResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Lista todos os usuários (apenas admin).

    Args:
        current_admin: Admin autenticado

    Returns:
        list[UsuarioResponse]: Lista de usuários
    """
    result = await db.execute(select(Usuario).order_by(Usuario.id.desc()))
    # CORREÇÃO SOURCERY: Retorno direto (inline variable)
    return result.scalars().all()


# ============================================================================
# ENDPOINT: RESET SENHA (Admin)
# ============================================================================


@router.put("/reset-password/{user_id}")
async def reset_password(
    user_id: int,
    nova_senha: str,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Reseta a senha de um usuário (apenas admin).

    Args:
        user_id: ID do usuário
        nova_senha: Nova senha
        current_admin: Admin autenticado

    Returns:
        dict: Mensagem de sucesso
    """
    # Buscar usuário
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    # Validar nova senha
    if len(nova_senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ter pelo menos 6 caracteres",
        )

    # Atualizar senha
    user.senha_hash = get_password_hash(nova_senha)  # type: ignore
    await db.commit()

    return {"message": f"Senha do usuário {user.email} resetada com sucesso"}
