"""
Schemas - Validação de dados com Pydantic
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ============================================================================
# SCHEMAS DE VALIDAÇÃO DE LICENÇA
# ============================================================================


class ValidarLicencaRequest(BaseModel):
    """Request para validar licença."""

    chave: str = Field(
        ..., min_length=10, max_length=50, description="Chave da licença"
    )
    hwid: str = Field(
        ..., min_length=5, max_length=100, description="Hardware ID do computador"
    )


class ValidarLicencaResponse(BaseModel):
    """Response da validação de licença."""

    sucesso: bool = Field(..., description="Se a validação foi bem-sucedida")
    mensagem: str = Field(..., description="Mensagem descritiva")
    dias_restantes: int | None = Field(None, description="Dias restantes até expiração")
    ativa: bool | None = Field(None, description="Se a licença está ativa")


# ============================================================================
# SCHEMAS DE TELEMETRIA
# ============================================================================


class TelemetriaRequest(BaseModel):
    """Request para enviar telemetria do bot."""

    sessao_id: str = Field(..., description="ID da sessão do bot")
    hwid: str = Field(..., description="Hardware ID")
    tipo: str = Field(..., description="Tipo de log (bet, win, loss, error)")
    dados: str = Field(default="", description="Dados adicionais")
    lucro: float = Field(default=0.0, description="Lucro/prejuízo da operação")


class TelemetriaResponse(BaseModel):
    """Response do envio de telemetria."""

    status: str = Field(..., description="Status do envio")
    id: int | None = Field(None, description="ID do log criado")


# ============================================================================
# SCHEMAS DE LICENÇA (CRUD)
# ============================================================================


class LicencaResponse(BaseModel):
    """Response com dados de uma licença."""

    id: int
    chave: str
    hwid: str | None
    ativa: bool
    created_at: datetime
    data_expiracao: datetime | None
    cliente_nome: str | None
    email_cliente: str | None
    whatsapp: str | None
    telegram_chat_id: str | None
    plano_tipo: str | None
    payment_id: str | None
    dias_restantes: int | None

    class Config:
        from_attributes = True
