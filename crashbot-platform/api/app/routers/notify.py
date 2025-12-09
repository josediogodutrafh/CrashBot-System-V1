"""
Router: Notificações do Bot
Endpoints para o BOT DESKTOP enviar notificações aos clientes.

O bot desktop faz requisições POST para estes endpoints,
e a API envia as notificações via Telegram para os clientes.
"""

from typing import Optional

from app.database import get_db
from app.models import Licenca
from app.services.client_notification_service import AlertType, send_client_notification
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/notify", tags=["notifications"])


# ============================================================================
# SCHEMAS
# ============================================================================


class NotifyHitRequest(BaseModel):
    """Request para notificar HIT."""

    hwid: str
    estrategia: str
    alvo: float
    explosao: float
    saldo: float
    lucro: float


class NotifyMissRequest(BaseModel):
    """Request para notificar MISS."""

    hwid: str
    estrategia: str
    alvo: float
    explosao: float
    saldo: float
    prejuizo: float


class NotifyStopLossRequest(BaseModel):
    """Request para notificar Stop Loss."""

    hwid: str
    saldo_inicial: float
    saldo_atual: float
    perda_pct: float


class NotifyMetaRequest(BaseModel):
    """Request para notificar Meta Atingida."""

    hwid: str
    meta: float
    saldo: float
    lucro_total: float


class NotifySessaoInicioRequest(BaseModel):
    """Request para notificar início de sessão."""

    hwid: str
    modo: str
    banca: float
    meta: float


class NotifySessaoFimRequest(BaseModel):
    """Request para notificar fim de sessão."""

    hwid: str
    duracao: str
    saldo_inicial: float
    saldo_final: float
    total_rodadas: int


class NotifyRelatorioPeriodico(BaseModel):
    """Request para relatório periódico."""

    hwid: str
    modo: str
    saldo: float
    rodadas: int
    hits: int
    misses: int
    lucro_sessao: float


class NotifyResponse(BaseModel):
    """Response padrão."""

    success: bool
    message: str


# ============================================================================
# FUNÇÃO AUXILIAR
# ============================================================================


async def get_client_chat_id(hwid: str, db: AsyncSession) -> Optional[str]:
    """
    Busca o chat_id do cliente pela licença vinculada ao HWID.

    Args:
        hwid: Hardware ID do bot
        db: Sessão do banco

    Returns:
        chat_id ou None se não encontrado
    """
    result = await db.execute(select(Licenca).where(Licenca.hwid == hwid))
    licenca = result.scalar_one_or_none()

    if not licenca:
        return None

    # Retorna o chat_id do Telegram (pode ser None se cliente não configurou)
    chat_id = licenca.telegram_chat_id

    # Fix Pylance: Verificação explícita de None para Column[str]
    return str(chat_id) if chat_id is not None else None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/hit", response_model=NotifyResponse)
async def notify_hit(
    payload: NotifyHitRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Notifica cliente sobre um HIT.
    Chamado pelo bot desktop após acerto.
    """
    chat_id = await get_client_chat_id(payload.hwid, db)

    if not chat_id:
        return NotifyResponse(
            success=False, message="Cliente não tem Telegram configurado"
        )

    success = await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.HIT,
        data={
            "estrategia": payload.estrategia,
            "alvo": payload.alvo,
            "explosao": payload.explosao,
            "saldo": payload.saldo,
            "lucro": payload.lucro,
        },
    )

    msg = "HIT notificado" if success else "Falha ao enviar notificação"
    return NotifyResponse(success=success, message=msg)


@router.post("/miss", response_model=NotifyResponse)
async def notify_miss(
    payload: NotifyMissRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Notifica cliente sobre um MISS.
    Chamado pelo bot desktop após erro.
    """
    chat_id = await get_client_chat_id(payload.hwid, db)

    if not chat_id:
        return NotifyResponse(
            success=False, message="Cliente não tem Telegram configurado"
        )

    success = await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.MISS,
        data={
            "estrategia": payload.estrategia,
            "alvo": payload.alvo,
            "explosao": payload.explosao,
            "saldo": payload.saldo,
            "prejuizo": payload.prejuizo,
        },
    )

    msg = "MISS notificado" if success else "Falha ao enviar notificação"
    return NotifyResponse(success=success, message=msg)


@router.post("/stop-loss", response_model=NotifyResponse)
async def notify_stop_loss(
    payload: NotifyStopLossRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Notifica cliente sobre Stop Loss atingido.
    """
    chat_id = await get_client_chat_id(payload.hwid, db)

    if not chat_id:
        return NotifyResponse(
            success=False, message="Cliente não tem Telegram configurado"
        )

    success = await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.STOP_LOSS,
        data={
            "saldo_inicial": payload.saldo_inicial,
            "saldo_atual": payload.saldo_atual,
            "perda_pct": payload.perda_pct,
        },
    )

    msg = "Stop Loss notificado" if success else "Falha ao enviar notificação"
    return NotifyResponse(success=success, message=msg)


@router.post("/meta-atingida", response_model=NotifyResponse)
async def notify_meta(
    payload: NotifyMetaRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Notifica cliente sobre Meta Atingida.
    """
    chat_id = await get_client_chat_id(payload.hwid, db)

    if not chat_id:
        return NotifyResponse(
            success=False, message="Cliente não tem Telegram configurado"
        )

    success = await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.META_ATINGIDA,
        data={
            "meta": payload.meta,
            "saldo": payload.saldo,
            "lucro_total": payload.lucro_total,
            "tempo_suspensao": "4 horas",
        },
    )

    msg = "Meta notificada" if success else "Falha ao enviar notificação"
    return NotifyResponse(success=success, message=msg)


@router.post("/sessao-inicio", response_model=NotifyResponse)
async def notify_sessao_inicio(
    payload: NotifySessaoInicioRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Notifica cliente sobre início de sessão.
    """
    chat_id = await get_client_chat_id(payload.hwid, db)

    if not chat_id:
        return NotifyResponse(
            success=False, message="Cliente não tem Telegram configurado"
        )

    success = await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.SESSAO_INICIO,
        data={
            "modo": payload.modo,
            "banca": payload.banca,
            "meta": payload.meta,
        },
    )

    # Fix E501
    msg = "Início de sessão notificado" if success else "Falha ao enviar notificação"
    return NotifyResponse(success=success, message=msg)


@router.post("/sessao-fim", response_model=NotifyResponse)
async def notify_sessao_fim(
    payload: NotifySessaoFimRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Notifica cliente sobre fim de sessão.
    """
    chat_id = await get_client_chat_id(payload.hwid, db)

    if not chat_id:
        return NotifyResponse(
            success=False, message="Cliente não tem Telegram configurado"
        )

    success = await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.SESSAO_FIM,
        data={
            "duracao": payload.duracao,
            "saldo_inicial": payload.saldo_inicial,
            "saldo_final": payload.saldo_final,
            "total_rodadas": payload.total_rodadas,
        },
    )

    # Fix E501
    msg = "Fim de sessão notificado" if success else "Falha ao enviar notificação"
    return NotifyResponse(success=success, message=msg)


@router.post("/relatorio-periodico", response_model=NotifyResponse)
async def notify_relatorio(
    payload: NotifyRelatorioPeriodico,
    db: AsyncSession = Depends(get_db),
):
    """
    Envia relatório periódico (30 min) para o cliente.
    """
    chat_id = await get_client_chat_id(payload.hwid, db)

    if not chat_id:
        return NotifyResponse(
            success=False, message="Cliente não tem Telegram configurado"
        )

    success = await send_client_notification(
        chat_id=chat_id,
        alert_type=AlertType.RELATORIO_PERIODICO,
        data={
            "modo": payload.modo,
            "saldo": payload.saldo,
            "rodadas": payload.rodadas,
            "hits": payload.hits,
            "misses": payload.misses,
            "lucro_sessao": payload.lucro_sessao,
        },
    )

    msg = "Relatório enviado" if success else "Falha ao enviar notificação"
    return NotifyResponse(success=success, message=msg)
