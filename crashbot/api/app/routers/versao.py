"""
Router: Versão do Bot
Endpoints para auto-update do bot.
"""

from typing import Optional, cast

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Usuario, VersaoBot
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/bot", tags=["versao"])


# ============================================================================
# SCHEMAS
# ============================================================================


class VersaoResponse(BaseModel):
    versao: str
    download_url: str
    changelog: Optional[str] = None
    obrigatoria: bool = False


class VersaoCreateRequest(BaseModel):
    versao: str
    download_url: str
    changelog: Optional[str] = None
    obrigatoria: bool = False


class VersaoUpdateRequest(BaseModel):
    download_url: Optional[str] = None
    changelog: Optional[str] = None
    obrigatoria: Optional[bool] = None


# ============================================================================
# ENDPOINT PÚBLICO: Verificar versão atual
# ============================================================================


@router.get("/versao", response_model=VersaoResponse)
async def get_versao_atual(db: AsyncSession = Depends(get_db)):
    """
    Retorna a versão mais recente do bot.
    Endpoint PÚBLICO - usado pelo bot para verificar atualizações.
    """
    result = await db.execute(
        select(VersaoBot)
        .where(VersaoBot.ativa.is_(True))
        .order_by(desc(VersaoBot.created_at))
        .limit(1)
    )
    versao: Optional[VersaoBot] = result.scalar_one_or_none()

    if not versao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma versao disponivel",
        )

    changelog_val = str(versao.changelog) if versao.changelog is not None else None

    return VersaoResponse(
        versao=str(versao.versao),
        download_url=str(versao.download_url),
        changelog=changelog_val,
        obrigatoria=bool(versao.obrigatoria),
    )


# ============================================================================
# ENDPOINT ADMIN: Listar todas as versões
# ============================================================================


@router.get("/versoes")
async def listar_versoes(
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Lista todas as versões do bot (admin)."""
    result = await db.execute(select(VersaoBot).order_by(desc(VersaoBot.created_at)))
    versoes = result.scalars().all()
    return [v.to_dict() for v in versoes]


# ============================================================================
# ENDPOINT ADMIN: Criar nova versão
# ============================================================================


@router.post("/versao", status_code=status.HTTP_201_CREATED)
async def criar_versao(
    payload: VersaoCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Cria uma nova versão do bot (admin)."""
    # Verificar se versão já existe
    result = await db.execute(
        select(VersaoBot).where(VersaoBot.versao == payload.versao)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Versao ja existe",
        )

    nova_versao = VersaoBot(
        versao=payload.versao,
        download_url=payload.download_url,
        changelog=payload.changelog,
        obrigatoria=payload.obrigatoria,
        ativa=True,
    )

    db.add(nova_versao)
    await db.commit()
    await db.refresh(nova_versao)

    return nova_versao.to_dict()


# ============================================================================
# ENDPOINT ADMIN: Atualizar versão
# ============================================================================


@router.patch("/versao/{versao_id}")
async def atualizar_versao(
    versao_id: int,
    payload: VersaoUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Atualiza campos de uma versão existente (admin)."""
    result = await db.execute(select(VersaoBot).where(VersaoBot.id == versao_id))
    versao: Optional[VersaoBot] = result.scalar_one_or_none()

    if not versao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Versao nao encontrada",
        )

    if payload.download_url is not None:
        versao.download_url = payload.download_url  # type: ignore
    if payload.changelog is not None:
        versao.changelog = payload.changelog  # type: ignore
    if payload.obrigatoria is not None:
        versao.obrigatoria = payload.obrigatoria  # type: ignore

    await db.commit()
    await db.refresh(versao)

    return versao.to_dict()


# ============================================================================
# ENDPOINT ADMIN: Desativar versão
# ============================================================================


@router.patch("/versao/{versao_id}/toggle")
async def toggle_versao(
    versao_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Ativa/desativa uma versão (admin)."""
    result = await db.execute(select(VersaoBot).where(VersaoBot.id == versao_id))
    # Dica de tipo para o Pylance entender que é uma instância ou None
    versao: Optional[VersaoBot] = result.scalar_one_or_none()

    if not versao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Versao nao encontrada",
        )

    status_atual = bool(versao.ativa)
    versao.ativa = not status_atual  # type: ignore
    await db.commit()

    return {"success": True, "ativa": versao.ativa}


# ============================================================================
# ENDPOINT ADMIN: Deletar versão
# ============================================================================


@router.delete("/versao/{versao_id}")
async def deletar_versao(
    versao_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Deleta uma versão do bot (admin)."""
    result = await db.execute(select(VersaoBot).where(VersaoBot.id == versao_id))
    versao: Optional[VersaoBot] = result.scalar_one_or_none()

    if not versao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Versao nao encontrada",
        )

    await db.delete(versao)
    await db.commit()

    return {"success": True, "deletada": str(versao.versao)}


# ============================================================================
# ENDPOINT ADMIN: Limpar versões antigas e registrar a nova
# ============================================================================


@router.post("/versoes/cleanup")
async def cleanup_versoes(
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """
    Desativa todas as versões antigas e registra a v3.0.0 como atual.
    Uso único após o deploy da nova versão.
    """
    # Desativar todas as versões existentes
    result = await db.execute(select(VersaoBot).where(VersaoBot.ativa.is_(True)))
    versoes_ativas = result.scalars().all()
    desativadas = []

    for v in versoes_ativas:
        v.ativa = False  # type: ignore
        desativadas.append(str(v.versao))

    # Verificar se v3.0.0 já existe
    result_v3 = await db.execute(
        select(VersaoBot).where(VersaoBot.versao == "3.0.0")
    )
    v3 = result_v3.scalar_one_or_none()

    if v3:
        v3.ativa = True  # type: ignore
        v3.obrigatoria = True  # type: ignore
        v3.changelog = (  # type: ignore
            "v3.0 - WebSocket capture, novo sistema de precos, "
            "Telegram stateless, deploy Render"
        )
    else:
        v3 = VersaoBot(
            versao="3.0.0",
            download_url="https://tucunarebot.com.br/download/v3",
            changelog=(
                "v3.0 - WebSocket capture, novo sistema de precos, "
                "Telegram stateless, deploy Render"
            ),
            obrigatoria=True,
            ativa=True,
        )
        db.add(v3)

    await db.commit()

    return {
        "success": True,
        "desativadas": desativadas,
        "versao_atual": "3.0.0",
        "obrigatoria": True,
    }
