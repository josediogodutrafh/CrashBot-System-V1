"""
Router: Autenticação
Endpoints para login, registro e gerenciamento de usuários.
"""

from datetime import datetime, timezone

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
    if not verify_password(credentials.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    # Verificar se usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado",
        )

    # Atualizar last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Criar token JWT
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

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
    # Verificar se email já existe
    result = await db.execute(select(Usuario).where(Usuario.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
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
# ENDPOINT: LISTAR USUÁRIOS (apenas admin)
# ============================================================================


@router.get("/users", response_model=list[UsuarioResponse])
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
    users = result.scalars().all()

    return users
