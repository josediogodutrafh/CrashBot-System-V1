"""
Router: Licenças
Endpoints para validação de licenças e telemetria do bot.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional, cast

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.models import Licenca, LogBot, Usuario
from app.models.versao_bot import VersaoBot
from app.services.email_service import enviar_email, template_licenca_criada
from passlib.context import CryptContext
from app.schemas.licenca import (
    TelemetriaRequest,
    TelemetriaResponse,
    ValidarLicencaRequest,
    ValidarLicencaResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1", tags=["licencas"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _gerar_senha_temporaria(tamanho: int = 10) -> str:
    """Gera uma senha temporaria aleatoria."""
    import string
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choices(caracteres, k=tamanho))


def _normalizar_versao(versao: str) -> str:
    """Remove prefixo 'v' e espaços. 'v5.3.0' -> '5.3.0'.

    O painel admin costuma receber a versão copiada da tag do GitHub
    (que tem o 'v'), mas aqui trabalhamos só com o número.
    """
    if not versao:
        return ""
    return versao.strip().lstrip("vV")


def _parse_versao(versao: str) -> Optional[list]:
    """Converte '5.3.0' em [5, 3, 0]. Retorna None se não for parseável."""
    try:
        partes = [int(x) for x in _normalizar_versao(versao).split(".")]
    except (ValueError, AttributeError):
        return None
    if not partes:
        return None
    # Completa com zeros: '6.0' e '6.0.0' devem comparar igual
    while len(partes) < 3:
        partes.append(0)
    return partes


def _versao_menor(versao_cliente: str, versao_servidor: str) -> bool:
    """Retorna True se versao_cliente < versao_servidor."""
    parts_s = _parse_versao(versao_servidor)
    if parts_s is None:
        # Versão cadastrada no painel está inválida (ex: digitada errada).
        # NÃO forçar update: o cliente não tem como satisfazer a exigência
        # e ficaria preso em loop de download infinito.
        return False

    parts_c = _parse_versao(versao_cliente)
    if parts_c is None:
        return True  # Bot antigo/sem versão: forçar update

    return parts_c < parts_s


def _normalizar_chave(chave: str) -> str:
    """Normaliza caracteres ambíguos em chaves de licença.

    Converte 0→O, 1→I para resolver confusão entre caracteres
    visualmente similares (O/0, I/1/L) em chaves geradas pelo
    sistema antigo que permitia esses caracteres.
    """
    return (
        chave.upper()
        .replace("0", "O")
        .replace("1", "I")
        .replace("L", "I")
    )


# ============================================================================
# ENDPOINT: VALIDAR LICENÇA
# ============================================================================


@router.post("/validar", response_model=ValidarLicencaResponse)
@limiter.limit("10/minute")  # Máximo 10 validações por minuto por IP
async def validar_licenca(
    request: Request,  # Adicionar este parâmetro
    payload: ValidarLicencaRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Valida uma licença.
    """
    # Buscar licença por chave (com normalização de caracteres ambíguos)
    # Normaliza AMBOS os lados: input do cliente E valor no banco
    chave_normalizada = _normalizar_chave(payload.chave)

    chave_db_normalizada = func.replace(
        func.replace(
            func.replace(func.upper(Licenca.chave), "0", "O"),
            "1", "I",
        ),
        "L", "I",
    )

    result = await db.execute(
        select(Licenca).where(chave_db_normalizada == chave_normalizada)
    )
    licenca = result.scalar_one_or_none()

    # Licença não encontrada
    if not licenca:
        return ValidarLicencaResponse(
            sucesso=False,
            mensagem="Licença não encontrada",
            ativa=False,
            dias_restantes=0,
            telegram_chat_id=None,
        )

    # Licença desativada
    if licenca.ativa is False:
        return ValidarLicencaResponse(
            sucesso=False,
            mensagem="Licença desativada",
            ativa=False,
            dias_restantes=0,
            telegram_chat_id=None,
        )

    # Licença expirada
    if bool(licenca.esta_expirada):
        return ValidarLicencaResponse(
            sucesso=False,
            mensagem="Licença expirada",
            dias_restantes=0,
            ativa=bool(licenca.ativa),
            telegram_chat_id=None,
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

    # Verificar versão mínima obrigatória
    force_update = False
    download_url = None

    result = await db.execute(
        select(VersaoBot)
        .where(VersaoBot.ativa == True, VersaoBot.obrigatoria == True)
        .order_by(VersaoBot.created_at.desc())
        .limit(1)
    )
    versao_obrigatoria = result.scalar_one_or_none()

    if versao_obrigatoria:
        versao_cliente = payload.versao_bot
        versao_servidor = _normalizar_versao(str(versao_obrigatoria.versao))

        # Se o bot não envia versão (antigo) ou versão é menor, forçar update
        if not versao_cliente or _versao_menor(versao_cliente, versao_servidor):
            force_update = True
            download_url = str(versao_obrigatoria.download_url)

            # Bloquear bots antigos: retornar sucesso=False
            return ValidarLicencaResponse(
                sucesso=False,
                mensagem=f"Atualização obrigatória para v{versao_servidor}. Baixe em: {download_url}",
                dias_restantes=licenca.dias_restantes,  # type: ignore
                ativa=bool(licenca.ativa),
                telegram_chat_id=licenca.telegram_chat_id,  # type: ignore
                force_update=True,
                download_url=download_url,
            )

    # Tudo OK!
    return ValidarLicencaResponse(
        sucesso=True,
        mensagem="Licença válida",
        dias_restantes=licenca.dias_restantes,  # type: ignore
        ativa=bool(licenca.ativa),
        telegram_chat_id=licenca.telegram_chat_id,  # type: ignore
    )


# ============================================================================
# ENDPOINT: RECEBER TELEMETRIA
# ============================================================================


@router.post("/telemetria/log", response_model=TelemetriaResponse)
async def receber_telemetria(
    payload: TelemetriaRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe telemetria do bot com dados completos.
    """
    # Capturar IP do cliente
    ip_cliente = request.client.host if request.client else None

    # Criar novo log com todos os campos
    novo_log = LogBot(
        # Campos obrigatórios
        sessao_id=payload.sessao_id,
        hwid=payload.hwid,
        tipo=payload.tipo,
        timestamp=datetime.now(timezone.utc),
        # Dados gerais
        dados=payload.dados,
        lucro=payload.lucro,
        # Vínculo
        licenca_id=payload.licenca_id,
        # Financeiros
        saldo=payload.saldo,
        valor_aposta=payload.valor_aposta,
        banca_inicial=payload.banca_inicial,
        banca_final=payload.banca_final,
        # Jogo
        modo_risco=payload.modo_risco,
        estrategia=payload.estrategia,
        target=payload.target,
        explosao=payload.explosao,
        resultado=payload.resultado,
        sequencia_perdas=payload.sequencia_perdas,
        dobra_atual=payload.dobra_atual,
        # Sessão
        total_rodadas=payload.total_rodadas,
        tempo_sessao_segundos=payload.tempo_sessao_segundos,
        # Alertas
        stop_loss_atingido=payload.stop_loss_atingido,
        meta_atingida=payload.meta_atingida,
        # Metadados
        versao_bot=payload.versao_bot,
        sistema_operacional=payload.sistema_operacional,
        ip_cliente=ip_cliente,
        plataforma=payload.plataforma,
    )

    db.add(novo_log)
    await db.commit()
    await db.refresh(novo_log)

    return TelemetriaResponse(
        status="ok",
        id=int(novo_log.id),  # type: ignore
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
    cpf: Optional[str] = None
    whatsapp: Optional[str] = None
    plano_tipo: str = "mensal"
    dias_validade: int = 30


# ============================================================================
# ENDPOINT: CRIAR LICENCA (Admin)
# ============================================================================


@router.post("/admin/test-email", status_code=status.HTTP_200_OK)
async def test_email(
    payload: dict,
    current_admin: Usuario = Depends(get_current_admin),
):
    """Testa envio de email para diagnostico."""
    import os
    from app.config import settings

    para = payload.get("para", "")
    if not para:
        return {"success": False, "error": "campo 'para' obrigatorio"}

    # Diagnostico
    api_key_env = os.getenv("RESEND_API_KEY", "")
    api_key_settings = settings.RESEND_API_KEY or ""

    diagnostico = {
        "resend_api_key_env_set": bool(api_key_env),
        "resend_api_key_env_prefix": api_key_env[:8] + "..." if api_key_env else "VAZIO",
        "resend_api_key_settings_set": bool(api_key_settings),
        "email_from": settings.EMAIL_FROM,
    }

    # Tentar enviar
    try:
        sucesso = await enviar_email(
            para=para,
            assunto="Teste TucunareBot - Email funcionando!",
            html="<h1>Teste OK</h1><p>Se voce recebeu este email, o sistema esta funcionando.</p>",
            texto="Teste OK - Sistema de email funcionando.",
        )
        return {
            "success": sucesso,
            "diagnostico": diagnostico,
            "destinatario": para,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "diagnostico": diagnostico,
        }


@router.delete("/admin/reset-clientes", status_code=status.HTTP_200_OK)
async def reset_clientes(
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Reseta todos os clientes, licencas e logs (mantem apenas admins)."""
    from sqlalchemy import delete

    # Apagar logs (referencia licenca_id)
    log_result = await db.execute(delete(LogBot))
    logs_deleted = log_result.rowcount

    # Apagar licencas
    lic_result = await db.execute(delete(Licenca))
    licencas_deleted = lic_result.rowcount

    # Apagar usuarios nao-admin
    user_result = await db.execute(
        delete(Usuario).where(Usuario.is_admin == False)
    )
    users_deleted = user_result.rowcount

    await db.commit()

    return {
        "success": True,
        "logs_deleted": logs_deleted,
        "licencas_deleted": licencas_deleted,
        "usuarios_deleted": users_deleted,
    }


@router.post("/licencas", status_code=status.HTTP_201_CREATED)
async def criar_licenca(
    payload: CriarLicencaRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Cria uma nova licenca manualmente (admin).

    Tambem cria a conta do cliente (se nao existir) e envia email
    com a chave de licenca + dados de acesso ao painel.
    """
    # Gerar chave no formato XXXX-XXXX-XXXX-XXXX (sem caracteres ambiguos)
    caracteres = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    chave = "-".join("".join(random.choices(caracteres, k=4)) for _ in range(4))

    data_expiracao = datetime.now(timezone.utc) + timedelta(days=payload.dias_validade)

    nova_licenca = Licenca(
        chave=chave,
        cliente_nome=payload.cliente_nome,
        email_cliente=payload.email_cliente,
        cpf=payload.cpf,
        whatsapp=payload.whatsapp or "Nao informado",
        plano_tipo=payload.plano_tipo,
        ativa=True,
        data_expiracao=data_expiracao,
    )

    db.add(nova_licenca)
    await db.commit()
    await db.refresh(nova_licenca)

    # Criar conta do cliente (se nao existir)
    senha_temporaria = "(sua senha atual)"
    result_user = await db.execute(
        select(Usuario).where(Usuario.email == payload.email_cliente)
    )
    usuario_existente = result_user.scalar_one_or_none()

    if not usuario_existente:
        senha_temporaria = _gerar_senha_temporaria()
        novo_usuario = Usuario(
            email=payload.email_cliente,
            senha_hash=pwd_context.hash(senha_temporaria),
            nome=payload.cliente_nome,
            is_admin=False,
            is_active=True,
        )
        db.add(novo_usuario)
        await db.commit()
        print(f"Usuario criado: {payload.email_cliente}")

    # Enviar email com licenca
    try:
        html_email = template_licenca_criada(
            nome=payload.cliente_nome or "Cliente",
            email=payload.email_cliente,
            senha=senha_temporaria,
            chave_licenca=chave,
            plano=payload.plano_tipo or "manual",
            dias=int(payload.dias_validade),
        )
        await enviar_email(
            para=payload.email_cliente,
            assunto="Sua licenca TucunareBot esta pronta!",
            html=html_email,
        )
    except Exception as e:
        print(f"Erro ao enviar email: {e}")

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
# ENDPOINT: RENOVAR LICENCA (Admin)
# ============================================================================


class RenovarLicencaRequest(BaseModel):
    dias: int


@router.post("/licencas/{licenca_id}/renovar")
async def renovar_licenca(
    licenca_id: int,
    payload: RenovarLicencaRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    """Adiciona N dias na data de expiracao da licenca.

    Se a licenca estiver expirada (ou sem data_expiracao), conta a
    partir de agora. Caso contrario, soma sobre a data atual de
    expiracao. Tambem reativa a licenca se estiver desativada.
    """
    if payload.dias <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O numero de dias deve ser positivo",
        )

    result = await db.execute(select(Licenca).where(Licenca.id == licenca_id))
    licenca = result.scalar_one_or_none()

    if not licenca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licenca nao encontrada",
        )

    now = datetime.now(timezone.utc)
    base = licenca.data_expiracao
    if base is not None:
        base_dt = cast(datetime, base)
        if base_dt.tzinfo is None:
            base_dt = base_dt.replace(tzinfo=timezone.utc)
        # Se ja expirou, renova a partir de agora
        if base_dt < now:
            base_dt = now
    else:
        base_dt = now

    nova_expiracao = base_dt + timedelta(days=payload.dias)
    licenca.data_expiracao = nova_expiracao  # type: ignore
    licenca.ativa = True  # type: ignore  # renovar sempre reativa

    await db.commit()
    await db.refresh(licenca)

    return {
        "success": True,
        "data_expiracao": nova_expiracao.isoformat(),
        "dias_restantes": licenca.dias_restantes,
        "ativa": bool(licenca.ativa),
    }


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


# ============================================================================
# ENDPOINT: MINHAS LICENÇAS (Cliente)
# ============================================================================


@router.get("/minhas-licencas")
async def minhas_licencas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista as licenças do usuário logado (por email)."""
    # Buscar licenças pelo email do usuário
    result = await db.execute(
        select(Licenca)
        .where(Licenca.email_cliente == current_user.email)
        .order_by(Licenca.id.desc())
    )
    licencas = result.scalars().all()

    return [licenca.to_dict() for licenca in licencas]
