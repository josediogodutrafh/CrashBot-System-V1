"""
Router: Calendar
Endpoints para agendamento de treinamentos via Google Calendar.
"""

from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.services.google_calendar_service import google_calendar
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


# ============================================================================
# SCHEMAS
# ============================================================================


class AgendarTreinamentoRequest(BaseModel):
    """Request para agendar treinamento."""

    nome: str
    email: EmailStr
    whatsapp: str
    data_hora: datetime  # Formato: 2025-12-20T14:00:00
    observacoes: Optional[str] = None


class AgendarTreinamentoResponse(BaseModel):
    """Response do agendamento."""

    success: bool
    mensagem: str
    evento_id: Optional[str] = None
    meet_link: Optional[str] = None
    data_hora: Optional[str] = None


class HorariosDisponiveisResponse(BaseModel):
    """Response com horários disponíveis."""

    slots: list
    total: int


# ============================================================================
# ENDPOINTS DE AUTENTICAÇÃO (Admin)
# ============================================================================


@router.get("/auth")
async def iniciar_autenticacao():
    """
    Inicia o fluxo de autenticação OAuth com Google.
    APENAS ADMIN deve acessar para autorizar o calendário.
    """
    auth_url = google_calendar.get_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback_autenticacao(code: str = Query(...)):
    """
    Callback do OAuth após autorização do Google.
    Recebe o código e troca por tokens.
    """
    result = await google_calendar.exchange_code_for_tokens(code)

    if result["success"]:
        return {
            "status": "success",
            "message": (
                "Autenticação realizada com sucesso! " "O calendário está conectado."
            ),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"],
        )


@router.get("/status")
async def status_autenticacao():
    """Verifica se o calendário está autenticado."""
    is_auth = google_calendar.is_authenticated()
    msg = (
        "Calendário conectado"
        if is_auth
        else (
            "Calendário não conectado. Acesse " "/api/v1/calendar/auth para autenticar."
        )
    )
    return {
        "autenticado": is_auth,
        "mensagem": msg,
    }


# ============================================================================
# ENDPOINTS DE AGENDAMENTO (Público)
# ============================================================================


@router.get("/horarios-disponiveis", response_model=HorariosDisponiveisResponse)
async def listar_horarios_disponiveis(
    data: Optional[str] = Query(
        None,
        description=(
            "Data no formato YYYY-MM-DD. " "Se não informada, usa próximos 7 dias."
        ),
    ),
):
    """
    Lista horários disponíveis para agendamento.
    Retorna slots de 30 minutos entre 10h e 18h (horário de Brasília).
    """
    if not google_calendar.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema de agendamento não disponível no momento.",
        )

    # Definir período de busca
    if data:
        try:
            data_inicio = datetime.strptime(data, "%Y-%m-%d")
            data_fim = data_inicio + timedelta(days=1)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de data inválido. Use YYYY-MM-DD.",
            ) from None
    else:
        # Próximos 7 dias
        data_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = data_inicio + timedelta(days=7)

    result = await google_calendar.listar_horarios_disponiveis(data_inicio, data_fim)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"],
        )

    return HorariosDisponiveisResponse(
        slots=result["slots"],
        total=result["total"],
    )


@router.post("/agendar", response_model=AgendarTreinamentoResponse)
async def agendar_treinamento(
    dados: AgendarTreinamentoRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Agenda um treinamento de integração.
    Cria evento no Google Calendar com link do Google Meet.
    """
    if not google_calendar.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema de agendamento não disponível no momento.",
        )

    # Validar horário (10h às 18h, segunda a sexta)
    hora = dados.data_hora.hour
    dia_semana = dados.data_hora.weekday()

    if dia_semana > 4:  # Sábado ou Domingo
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agendamentos disponíveis apenas de segunda a sexta.",
        )

    if hora < 10 or hora >= 18:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Horário disponível: 10h às 18h (horário de Brasília).",
        )

    # Criar agendamento
    result = await google_calendar.criar_agendamento(
        titulo=f"Treinamento CrashBot - {dados.nome}",
        descricao=dados.observacoes or "Treinamento de integração do CrashBot",
        data_hora=dados.data_hora,
        duracao_minutos=30,
        email_convidado=dados.email,
        nome_convidado=dados.nome,
        whatsapp_convidado=dados.whatsapp,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"],
        )

    msg_sucesso = (
        "Treinamento agendado com sucesso! " "Você receberá um email de confirmação."
    )

    return AgendarTreinamentoResponse(
        success=True,
        mensagem=msg_sucesso,
        evento_id=result.get("evento_id"),
        meet_link=result.get("meet_link"),
        data_hora=result.get("inicio"),
    )


@router.delete("/cancelar/{evento_id}")
async def cancelar_agendamento(evento_id: str):
    """Cancela um agendamento existente."""
    if not google_calendar.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema de agendamento não disponível no momento.",
        )

    result = await google_calendar.cancelar_agendamento(evento_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"],
        )

    return result
