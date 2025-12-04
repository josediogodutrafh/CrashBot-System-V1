"""
Router: Licenças
Endpoints para validação de licenças e telemetria do bot.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, cast

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Licenca, LogBot, Usuario
from app.schemas.licenca import (
    TelemetriaRequest,
    TelemetriaResponse,
    ValidarLicencaRequest,
    ValidarLicencaResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["licencas"])


# ============================================================================
# ENDPOINT: VALIDAR LICENÇA
# ============================================================================


@router.post("/validar", response_model=ValidarLicencaResponse)
async def validar_licenca(
    payload: ValidarLicencaRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Valida uma licença.
    """
    # Buscar licença por chave
    result = await db.execute(select(Licenca).where(Licenca.chave == payload.chave))
    licenca = result.scalar_one_or_none()

    # Licença não encontrada
    if not licenca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licença não encontrada",
        )

    # Licença desativada
    if licenca.ativa is False:
        return ValidarLicencaResponse(
            sucesso=False,
            mensagem="Licença desativada",
            ativa=False,
            dias_restantes=0,
        )

    # Licença expirada
    if bool(licenca.esta_expirada):
        return ValidarLicencaResponse(
            sucesso=False,
            mensagem="Licença expirada",
            dias_restantes=0,
            ativa=bool(licenca.ativa),
        )

    # Verificar HWID (CORREÇÃO DEFINITIVA)
    current_hwid = licenca.hwid

    if current_hwid is None:
        # Primeira vez usando - registrar HWID
        # type: ignore -> Silencia erro de atribuir str em Column[str]
        licenca.hwid = payload.hwid  # type: ignore
        await db.commit()
    elif str(current_hwid) != payload.hwid:
        # HWID já registrado e diferente
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HWID não autorizado. Licença já vinculada a outro computador.",
        )

    # Tudo OK!
    return ValidarLicencaResponse(
        sucesso=True,
        mensagem="Licença válida",
        # type: ignore -> Silencia erro se dias_restantes for None (Pydantic valida em runtime)
        dias_restantes=licenca.dias_restantes,  # type: ignore
        ativa=bool(licenca.ativa),
    )


# ============================================================================
# ENDPOINT: RECEBER TELEMETRIA
# ============================================================================


@router.post("/telemetria/log", response_model=TelemetriaResponse)
async def receber_telemetria(
    payload: TelemetriaRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe telemetria do bot.
    """
    # Criar novo log
    novo_log = LogBot(
        sessao_id=payload.sessao_id,
        hwid=payload.hwid,
        tipo=payload.tipo,
        dados=payload.dados,
        lucro=payload.lucro,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo_log)
    await db.commit()
    await db.refresh(novo_log)

    return TelemetriaResponse(
        status="ok",
        id=int(novo_log.id),  # type: ignore - Cast explícito para int
    )


# ============================================================================
# ENDPOINT: LISTAR LICENÇAS (Admin)
# ============================================================================


@router.get("/licencas")
async def listar_licencas(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Lista todas as licenças (endpoint admin)."""
    result = await db.execute(
        select(Licenca).offset(skip).limit(limit).order_by(Licenca.id.desc())
    )
    licencas = result.scalars().all()

    return [licenca.to_dict() for licenca in licencas]


# ============================================================================
# SCHEMA: Criar Licenca
# ============================================================================


class CriarLicencaRequest(BaseModel):
    cliente_nome: str
    email_cliente: str
    whatsapp: Optional[str] = None
    plano_tipo: str = "mensal"
    dias_validade: int = 30


# ============================================================================
# ENDPOINT: CRIAR LICENCA (Admin)
# ============================================================================


@router.post("/licencas", status_code=status.HTTP_201_CREATED)
async def criar_licenca(
    payload: CriarLicencaRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Cria uma nova licenca manualmente (admin)."""
    # Gerar chave unica
    chave = f"KEY-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}-"

    # Calcular data de expiracao
    data_expiracao = datetime.now(timezone.utc) + timedelta(days=payload.dias_validade)

    nova_licenca = Licenca(
        chave=chave,
        cliente_nome=payload.cliente_nome,
        email_cliente=payload.email_cliente,
        whatsapp=payload.whatsapp or "Nao informado",
        plano_tipo=payload.plano_tipo,
        ativa=True,
        data_expiracao=data_expiracao,
    )

    db.add(nova_licenca)
    await db.commit()
    await db.refresh(nova_licenca)

    return nova_licenca.to_dict()


# ============================================================================
# ENDPOINT: TOGGLE ATIVAR/DESATIVAR LICENCA (Admin)
# ============================================================================


@router.patch("/licencas/{licenca_id}/toggle")
async def toggle_licenca(
    licenca_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Ativa ou desativa uma licenca."""
    result = await db.execute(select(Licenca).where(Licenca.id == licenca_id))
    licenca = result.scalar_one_or_none()

    if not licenca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licenca nao encontrada",
        )

    # CORREÇÃO: Cast para bool para evitar erro de tipo na inversão
    status_atual = bool(licenca.ativa)
    # type: ignore -> Silencia erro de atribuir bool em Column[bool]
    licenca.ativa = not status_atual  # type: ignore

    await db.commit()

    return {"success": True, "ativa": licenca.ativa}


# ============================================================================
# ENDPOINT: RESET HWID (Admin)
# ============================================================================


@router.patch("/licencas/{licenca_id}/reset-hwid")
async def reset_hwid(
    licenca_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Reseta o HWID de uma licenca."""
    result = await db.execute(select(Licenca).where(Licenca.id == licenca_id))
    licenca = result.scalar_one_or_none()

    if not licenca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licenca nao encontrada",
        )

    # type: ignore -> Silencia erro de atribuir None em Column[str]
    licenca.hwid = None  # type: ignore
    await db.commit()

    return {"success": True, "message": "HWID resetado com sucesso"}


# ============================================================================
# ENDPOINT: LISTAR LOGS TELEMETRIA (Admin)
# ============================================================================


@router.get("/telemetria/logs")
async def listar_logs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Lista todos os logs de telemetria (admin)."""
    result = await db.execute(
        select(LogBot).offset(skip).limit(limit).order_by(LogBot.id.desc())
    )
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "sessao_id": log.sessao_id,
            "hwid": log.hwid,
            "tipo": log.tipo,
            "dados": log.dados,
            "lucro": log.lucro,
            # CORREÇÃO: Cast seguro e verificação de None para o timestamp
            "timestamp": (
                cast(datetime, log.timestamp).isoformat()
                if log.timestamp is not None
                else None
            ),
        }
        for log in logs
    ]
