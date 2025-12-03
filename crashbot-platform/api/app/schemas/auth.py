"""
Schemas - Autenticação
"""

from pydantic import BaseModel, EmailStr, Field

# ============================================================================
# SCHEMAS DE LOGIN
# ============================================================================


class LoginRequest(BaseModel):
    """Request para login."""

    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=6, description="Senha do usuário")


class LoginResponse(BaseModel):
    """Response do login."""

    access_token: str = Field(..., description="Token JWT")
    token_type: str = Field(default="bearer", description="Tipo do token")
    user: dict = Field(..., description="Dados do usuário")


# ============================================================================
# SCHEMAS DE USUÁRIO
# ============================================================================


class UsuarioCreate(BaseModel):
    """Schema para criar usuário."""

    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=6, description="Senha")
    nome: str = Field(..., min_length=3, description="Nome completo")
    is_admin: bool = Field(default=True, description="Se é admin")


class UsuarioResponse(BaseModel):
    """Response com dados do usuário."""

    id: int
    email: str
    nome: str | None
    is_admin: bool
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS DE TOKEN
# ============================================================================


class TokenData(BaseModel):
    """Dados decodificados do token."""

    user_id: int | None = None
    email: str | None = None
