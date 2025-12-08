"""
Service: Promoções
Lógica para verificar elegibilidade a trial e primeira adesão.
"""

from app.models import Licenca
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def verificar_elegibilidade_trial(
    db: AsyncSession,
    cpf: str,
    hwid: str | None = None,
) -> dict:
    """
    Verifica se CPF ou HWID já usou trial.

    Args:
        db: Sessão do banco
        cpf: CPF do cliente (obrigatório)
        hwid: Hardware ID (opcional)

    Returns:
        dict: {
            "pode_usar_trial": bool,
            "motivo": str | None
        }
    """
    # Buscar licenças trial existentes para este CPF ou HWID
    conditions = [and_(Licenca.cpf == cpf, Licenca.is_trial == True)]

    if hwid:
        conditions.append(and_(Licenca.hwid == hwid, Licenca.is_trial == True))

    result = await db.execute(select(Licenca).where(or_(*conditions)))
    licenca_trial = result.scalar_one_or_none()

    if licenca_trial:
        return {
            "pode_usar_trial": False,
            "motivo": "CPF ou dispositivo já utilizou o período trial",
        }

    return {"pode_usar_trial": True, "motivo": None}


async def verificar_elegibilidade_primeira_adesao(
    db: AsyncSession,
    cpf: str,
    hwid: str | None = None,
) -> dict:
    """
    Verifica se CPF ou HWID já usou preço de primeira adesão.

    Args:
        db: Sessão do banco
        cpf: CPF do cliente (obrigatório)
        hwid: Hardware ID (opcional)

    Returns:
        dict: {
            "pode_usar_primeira_adesao": bool,
            "motivo": str | None
        }
    """
    # Buscar licenças com primeira adesão para este CPF ou HWID
    conditions = [and_(Licenca.cpf == cpf, Licenca.is_primeira_adesao == True)]

    if hwid:
        conditions.append(
            and_(Licenca.hwid == hwid, Licenca.is_primeira_adesao == True)
        )

    result = await db.execute(select(Licenca).where(or_(*conditions)))
    licenca_primeira = result.scalar_one_or_none()

    if licenca_primeira:
        return {
            "pode_usar_primeira_adesao": False,
            "motivo": "CPF ou dispositivo já utilizou o preço promocional de primeira adesão",
        }

    return {"pode_usar_primeira_adesao": True, "motivo": None}


async def obter_preco_plano(
    db: AsyncSession,
    plano: str,
    cpf: str,
    hwid: str | None = None,
) -> dict:
    """
    Retorna o preço correto do plano baseado no histórico do cliente.

    Args:
        db: Sessão do banco
        plano: Tipo do plano (semanal, quinzenal, mensal)
        cpf: CPF do cliente
        hwid: Hardware ID (opcional)

    Returns:
        dict: {
            "preco": float,
            "preco_original": float,
            "is_primeira_adesao": bool,
            "desconto": float
        }
    """
    # Preços dos planos
    PRECOS = {
        "semanal": {"normal": 149.90, "primeira_adesao": 49.90, "dias": 7},
        "quinzenal": {"normal": 249.90, "primeira_adesao": 89.90, "dias": 15},
        "mensal": {"normal": 449.90, "primeira_adesao": 149.90, "dias": 30},
    }

    if plano not in PRECOS:
        return None

    plano_info = PRECOS[plano]

    # Verificar elegibilidade para primeira adesão
    elegibilidade = await verificar_elegibilidade_primeira_adesao(db, cpf, hwid)

    if elegibilidade["pode_usar_primeira_adesao"]:
        return {
            "preco": plano_info["primeira_adesao"],
            "preco_original": plano_info["normal"],
            "is_primeira_adesao": True,
            "desconto": plano_info["normal"] - plano_info["primeira_adesao"],
            "dias": plano_info["dias"],
        }

    return {
        "preco": plano_info["normal"],
        "preco_original": plano_info["normal"],
        "is_primeira_adesao": False,
        "desconto": 0,
        "dias": plano_info["dias"],
    }
