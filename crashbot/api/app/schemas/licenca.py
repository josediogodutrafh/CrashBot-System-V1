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
    telegram_chat_id: str | None = Field(
        None, description="Chat ID do Telegram do cliente"
    )


# ============================================================================
# SCHEMAS DE TELEMETRIA
# ============================================================================
class TelemetriaRequest(BaseModel):
    """Request para enviar telemetria do bot."""

    # Campos obrigatórios
    sessao_id: str = Field(..., description="ID da sessão do bot")
    hwid: str = Field(..., description="Hardware ID")
    tipo: str = Field(
        ...,
        description="Tipo: sessao_inicio, aposta, sessao_fim, erro, modo_alterado, alerta",
    )

    # Campos opcionais - Dados gerais
    dados: str | None = Field(default=None, description="JSON com dados extras")
    lucro: float = Field(default=0.0, description="Lucro/prejuízo da operação")

    # Campos opcionais - Vínculo
    licenca_id: int | None = Field(default=None, description="ID da licença")

    # Campos opcionais - Financeiros
    saldo: float | None = Field(default=None, description="Saldo atual")
    valor_aposta: float | None = Field(default=None, description="Valor da aposta")
    banca_inicial: float | None = Field(
        default=None, description="Banca no início da sessão"
    )
    banca_final: float | None = Field(
        default=None, description="Banca no fim da sessão"
    )

    # Campos opcionais - Jogo
    modo_risco: str | None = Field(
        default=None, description="CONSERVADOR, MODERADO, AGRESSIVO"
    )
    estrategia: str | None = Field(default=None, description="Nome da estratégia ativa")
    target: float | None = Field(default=None, description="Target da aposta")
    explosao: float | None = Field(default=None, description="Valor da explosão")
    resultado: str | None = Field(default=None, description="hit ou miss")
    sequencia_perdas: int | None = Field(
        default=None, description="Contador de perdas consecutivas"
    )
    dobra_atual: int | None = Field(
        default=None, description="Nível do Martingale (1-4)"
    )

    # Campos opcionais - Sessão
    total_rodadas: int | None = Field(
        default=None, description="Total de rodadas na sessão"
    )
    tempo_sessao_segundos: int | None = Field(
        default=None, description="Duração da sessão em segundos"
    )

    # Campos opcionais - Alertas

    # Campos opcionais - Alertas
    stop_loss_atingido: str | None = Field(default=None, description="S ou N")
    meta_atingida: str | None = Field(default=None, description="S ou N")

    # Campos opcionais - Metadados
    versao_bot: str | None = Field(default=None, description="Versão do bot")
    sistema_operacional: str | None = Field(default=None, description="SO do cliente")


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
