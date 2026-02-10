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

    # CORREÇÃO: Cast para bool para evitar erro de 'Column' no 'not'
    # O Pylance se confunde com colunas booleanas em modelos antigos do SQLAlchemy
    status_atual = bool(versao.ativa)

    # Atribuição direta. O type checker pode reclamar da atribuição a Column,
    # mas em runtime isso funciona perfeitamente no SQLAlchemy.
    # Adicionamos type: ignore para silenciar o erro específico de atribuição estática
    versao.ativa = not status_atual  # type: ignore

    await db.commit()

    return {"success": True, "ativa": versao.ativa}
