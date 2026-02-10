"""
Router: Telegram Webhook
Recebe mensagens do Telegram Bot e registra chat_id dos clientes.

FLUXO:
1. Cliente clica no link do email e abre @tucunare_crashbot_bot
2. Cliente envia /start
3. Bot pede a chave de licença
4. Cliente envia a chave (formato XXXX-XXXX-XXXX-XXXX)
5. Sistema valida e salva o chat_id na licença
6. Cliente começa a receber notificações!

NOTA: Stateless - reconhece chaves de licença pelo formato (sem dict em memória).
"""

import os
import re
from typing import Optional

import httpx
from app.database import get_db
from app.models import Licenca
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Regex para detectar chave de licença (XXXX-XXXX-XXXX-XXXX)
LICENSE_KEY_PATTERN = re.compile(
    r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
)


# ============================================================================
# SCHEMAS
# ============================================================================


class TelegramUpdate(BaseModel):
    """Schema simplificado do update do Telegram."""

    update_id: int
    message: Optional[dict] = None


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


async def send_telegram_message(
    chat_id: int, text: str, parse_mode: str = "Markdown"
) -> bool:
    """Envia mensagem para um chat do Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN nao configurado")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
                timeout=10.0,
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar mensagem Telegram: {e}")
        return False


def is_license_key(text: str) -> bool:
    """Verifica se o texto parece uma chave de licença."""
    return bool(LICENSE_KEY_PATTERN.match(text.upper().strip()))


async def validate_and_link_license(
    chat_id: int,
    license_key: str,
    db: AsyncSession,
) -> tuple[bool, str]:
    """
    Valida a chave de licença e vincula o chat_id.

    Returns:
        tuple: (sucesso, mensagem)
    """
    query = select(Licenca).where(
        Licenca.chave == license_key.upper().strip()
    )
    result = await db.execute(query)
    licenca = result.scalar_one_or_none()

    if not licenca:
        msg = (
            "Chave de licenca nao encontrada.\n\n"
            "Verifique se digitou corretamente e tente novamente."
        )
        return False, msg

    if licenca.ativa is False:
        msg = (
            "Esta licenca esta desativada.\n\n"
            "Entre em contato com o suporte."
        )
        return False, msg

    if licenca.esta_expirada:
        msg = (
            "Esta licenca esta expirada.\n\n"
            "Renove sua licenca em tucunarebot.com.br"
        )
        return False, msg

    # Verificar se já está vinculada a outro chat
    current_chat_id = licenca.telegram_chat_id
    if current_chat_id is not None and str(current_chat_id) != str(chat_id):
        msg = (
            "Esta licenca ja esta vinculada a outro Telegram.\n\n"
            "Use /desativar no Telegram original ou contate o suporte."
        )
        return False, msg

    # Vincular chat_id à licença
    licenca.telegram_chat_id = str(chat_id)  # type: ignore
    await db.commit()

    nome = licenca.cliente_nome or "Cliente"
    dias = licenca.dias_restantes or 0

    return (
        True,
        f"*Licenca ativada com sucesso!*\n\n"
        f"Ola, *{nome}*!\n\n"
        f"Voce agora recebera notificacoes de:\n"
        f"- HITs (acertos)\n"
        f"- MISSes (erros)\n"
        f"- Alertas de Stop Loss\n"
        f"- Meta atingida\n"
        f"- Relatorios periodicos\n\n"
        f"*Dias restantes:* {dias} dias\n\n"
        f"_Boas operacoes!_",
    )


# ============================================================================
# WEBHOOK ENDPOINT
# ============================================================================


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe updates do Telegram Bot.
    Stateless: reconhece chaves pelo formato XXXX-XXXX-XXXX-XXXX.
    """
    try:
        body = await request.json()
    except Exception:
        return {"ok": True}

    # Extrair dados da mensagem
    message = body.get("message")
    if not message:
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    user_name = message.get("from", {}).get("first_name", "")

    if not chat_id or not text:
        return {"ok": True}

    # ── Comandos ──────────────────────────────────────────────────

    if text == "/start":
        welcome_message = (
            f"*Bem-vindo ao TucunareBot!*\n\n"
            f"Ola, {user_name}!\n\n"
            f"Para ativar as notificacoes, envie sua chave de licenca.\n\n"
            f"*Digite sua chave de licenca:*\n"
            f"_(Formato: XXXX-XXXX-XXXX-XXXX)_\n\n"
            f"A chave foi enviada no seu email de compra."
        )
        await send_telegram_message(chat_id, welcome_message)
        return {"ok": True}

    elif text == "/status":
        result = await db.execute(
            select(Licenca).where(
                Licenca.telegram_chat_id == str(chat_id)
            )
        )
        licenca = result.scalar_one_or_none()

        if licenca:
            dias = licenca.dias_restantes or 0
            status_msg = (
                f"*Licenca Vinculada*\n\n"
                f"Chave: `{licenca.chave}`\n"
                f"Dias restantes: {dias}\n"
                f"Notificacoes: Ativas\n\n"
                f"Use /desativar para parar as notificacoes."
            )
        else:
            status_msg = (
                "*Nenhuma licenca vinculada*\n\n"
                "Envie sua chave de licenca para vincular.\n"
                "_(Formato: XXXX-XXXX-XXXX-XXXX)_"
            )

        await send_telegram_message(chat_id, status_msg)
        return {"ok": True}

    elif text == "/desativar":
        result = await db.execute(
            select(Licenca).where(
                Licenca.telegram_chat_id == str(chat_id)
            )
        )
        licenca = result.scalar_one_or_none()

        if licenca:
            licenca.telegram_chat_id = None  # type: ignore
            await db.commit()
            msg = (
                "*Notificacoes desativadas*\n\n"
                "Envie sua chave novamente para reativar."
            )
            await send_telegram_message(chat_id, msg)
        else:
            await send_telegram_message(
                chat_id,
                "Nenhuma licenca vinculada a este Telegram.",
            )
        return {"ok": True}

    elif text in ("/ajuda", "/help"):
        help_message = (
            "*Comandos Disponiveis*\n\n"
            "/start - Iniciar vinculacao\n"
            "/status - Ver status da licenca\n"
            "/desativar - Parar notificacoes\n"
            "/ajuda - Ver esta mensagem\n\n"
            "*Suporte:* tucunarebot.com.br"
        )
        await send_telegram_message(chat_id, help_message)
        return {"ok": True}

    # ── Chave de licença (detectada pelo formato) ─────────────────

    elif is_license_key(text):
        success, response_message = await validate_and_link_license(
            chat_id=chat_id,
            license_key=text,
            db=db,
        )
        await send_telegram_message(chat_id, response_message)
        return {"ok": True}

    # ── Mensagem não reconhecida ──────────────────────────────────

    else:
        msg = (
            "Nao entendi.\n\n"
            "Envie sua chave de licenca (XXXX-XXXX-XXXX-XXXX) "
            "ou use /ajuda para ver os comandos."
        )
        await send_telegram_message(chat_id, msg)
        return {"ok": True}


# ============================================================================
# ENDPOINT: CONFIGURAR WEBHOOK
# ============================================================================


@router.get("/setup-webhook")
async def setup_webhook():
    """
    Configura o webhook do Telegram.
    Acesse esta rota UMA VEZ para configurar.
    """
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN nao configurado"}

    base = os.getenv(
        "API_BASE_URL", "https://crash-api-jose.onrender.com"
    )
    webhook_url = f"{base}/api/v1/telegram/webhook"

    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{TELEGRAM_API_URL}/deleteWebhook")

            response = await client.post(
                f"{TELEGRAM_API_URL}/setWebhook",
                json={"url": webhook_url},
                timeout=10.0,
            )

            result = response.json()

            if result.get("ok"):
                return {
                    "success": True,
                    "message": "Webhook configurado com sucesso!",
                    "webhook_url": webhook_url,
                }
            else:
                return {
                    "success": False,
                    "error": result.get(
                        "description", "Erro desconhecido"
                    ),
                }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# ENDPOINT: INFO DO WEBHOOK
# ============================================================================


@router.get("/webhook-info")
async def webhook_info():
    """Retorna informacoes do webhook atual."""
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN nao configurado"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TELEGRAM_API_URL}/getWebhookInfo",
                timeout=10.0,
            )
            return response.json()

    except Exception as e:
        return {"error": str(e)}
