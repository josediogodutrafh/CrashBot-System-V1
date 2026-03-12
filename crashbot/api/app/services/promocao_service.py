"""
Service: Promoções
Lógica para verificar elegibilidade a trial.
ATUALIZADO: Inclui verificação de WhatsApp para trial
"""

from app.models import Licenca
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def verificar_elegibilidade_trial(
    db: AsyncSession,
    cpf: str,
    whatsapp: str | None = None,
    hwid: str | None = None,
) -> dict:
    """
    Verifica se CPF, WhatsApp ou HWID já usou trial.

    Args:
        db: Sessão do banco
        cpf: CPF do cliente (obrigatório)
        whatsapp: WhatsApp do cliente (opcional, mas recomendado)
        hwid: Hardware ID (opcional)

    Returns:
        dict: {
            "pode_usar_trial": bool,
            "motivo": str | None,
            "bloqueado_por": str | None  # "cpf", "whatsapp" ou "hwid"
        }
    """
    # Normalizar WhatsApp (remover formatação)
    whatsapp_limpo = None
    if whatsapp:
        whatsapp_limpo = "".join(filter(str.isdigit, whatsapp))

    # Buscar licenças trial existentes para este CPF
    conditions = [and_(Licenca.cpf == cpf, Licenca.is_trial == True)]

    # Adicionar condição para WhatsApp
    if whatsapp_limpo:
        # Buscar WhatsApp com ou sem formatação
        conditions.append(and_(Licenca.whatsapp.isnot(None), Licenca.is_trial == True))

    # Adicionar condição para HWID
    if hwid:
        conditions.append(and_(Licenca.hwid == hwid, Licenca.is_trial == True))

    # Buscar todas as licenças trial que correspondem
    result = await db.execute(select(Licenca).where(or_(*conditions)))
    licencas_trial = result.scalars().all()

    for licenca in licencas_trial:
        # Verificar CPF
        if licenca.cpf == cpf:
            return {
                "pode_usar_trial": False,
                "motivo": "Este CPF já utilizou o período trial.",
                "bloqueado_por": "cpf",
            }

        # Verificar WhatsApp (comparar números limpos)
        if whatsapp_limpo and licenca.whatsapp:
            whatsapp_licenca = "".join(filter(str.isdigit, licenca.whatsapp))
            if whatsapp_limpo == whatsapp_licenca or whatsapp_limpo[-9:] == whatsapp_licenca[-9:]:
                return {
                    "pode_usar_trial": False,
                    "motivo": "Este WhatsApp já utilizou o período trial.",
                    "bloqueado_por": "whatsapp",
                }

        # Verificar HWID
        if hwid and licenca.hwid == hwid:
            return {
                "pode_usar_trial": False,
                "motivo": "Este dispositivo já utilizou o período trial.",
                "bloqueado_por": "hwid",
            }

    return {"pode_usar_trial": True, "motivo": None, "bloqueado_por": None}


async def obter_preco_plano(
    db: AsyncSession,
    plano: str,
    cpf: str,
    hwid: str | None = None,
) -> dict | None:
    """
    Retorna o preço do plano.

    Args:
        db: Sessão do banco
        plano: Tipo do plano (semanal, mensal)
        cpf: CPF do cliente
        hwid: Hardware ID (opcional)

    Returns:
        dict com preco e dias, ou None se plano inválido
    """
    PRECOS = {
        "mensal": {"preco": 600.00, "dias": 30},
    }

    if plano not in PRECOS:
        return None

    plano_info = PRECOS[plano]

    return {
        "preco": plano_info["preco"],
        "preco_original": plano_info["preco"],
        "is_primeira_adesao": False,
        "desconto": 0,
        "dias": plano_info["dias"],
    }
