"""
Auth Service - Autenticação e JWT
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from jose import JWTError, jwt
from passlib.context import CryptContext

# ============================================================================
# CONFIGURAÇÃO DE SENHA
# ============================================================================

# Contexto para hash de senhas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# FUNÇÕES DE SENHA
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha está correta.

    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash da senha armazenada

    Returns:
        bool: True se a senha está correta
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Gera hash da senha.

    Args:
        password: Senha em texto plano

    Returns:
        str: Hash da senha
    """
    return pwd_context.hash(password)


# ============================================================================
# FUNÇÕES JWT
# ============================================================================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT.

    Args:
        data: Dados a serem codificados no token
        expires_delta: Tempo de expiração customizado (opcional)

    Returns:
        str: Token JWT codificado
    """
    to_encode = data.copy()

    # Definir tempo de expiração
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    # Criar token
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica e valida um token JWT.

    Args:
        token: Token JWT

    Returns:
        dict | None: Payload do token ou None se inválido
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
