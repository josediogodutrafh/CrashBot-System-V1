"""
Router: Telegram Webhook
Recebe mensagens do Telegram Bot e registra chat_id dos clientes.

FLUXO:
1. Cliente clica no link do email e abre @tucunare_crashbot_bot
2. Cliente envia /start
3. Bot pede a chave de licença
4. Cliente envia a chave
5. Sistema valida e salva o chat_id na licença
6. Cliente começa a receber notificações!
"""

import os
from typing import Optional

import httpx
from app.database import get_db
from app.models import Licenca
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Estados de conversa (simples, em memória)
# Em produção, usar Redis para persistir estados
user_states: dict = {}


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
        print("⚠️ TELEGRAM_BOT_TOKEN não configurado")
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
        print(f"❌ Erro ao enviar mensagem Telegram: {e}")
        return False


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
    # Normalizar caracteres ambíguos (0↔O, 1↔I, L↔I)
    # Normaliza AMBOS os lados: input do cliente E valor no banco
    from app.routers.licencas import _normalizar_chave

    chave_normalizada = _normalizar_chave(license_key)

    chave_db_normalizada = func.replace(
        func.replace(
            func.replace(func.upper(Licenca.chave), "0", "O"),
            "1", "I",
        ),
        "L", "I",
    )

    query = select(Licenca).where(chave_db_normalizada == chave_normalizada)
    result = await db.execute(query)
    licenca = result.scalar_one_or_none()

    if not licenca:
        msg = (
            "❌ Chave de licença não encontrada.\n\n"
            "Verifique se digitou corretamente e tente novamente."
        )
        return False, msg

    # Fix Pylance: Comparação explícita com False
    if licenca.ativa is False:
        msg = "❌ Esta licença está desativada.\n\n" "Entre em contato com o suporte."
        return False, msg

    if licenca.esta_expirada:
        msg = (
            "❌ Esta licença está expirada.\n\n"
            "Renove sua licença em tucunarebot.com.br"
        )
        return False, msg

    # Verificar se já está vinculada a outro chat
    current_chat_id = licenca.telegram_chat_id

    # Fix Pylance: Verificação explícita de None antes de converter
    if current_chat_id is not None and str(current_chat_id) != str(chat_id):
        msg = (
            "⚠️ Esta licença já está vinculada a outro Telegram.\n\n"
            "Use /reset no seu Telegram original ou contate o suporte."
        )
        return False, msg

    # Vincular chat_id à licença
    licenca.telegram_chat_id = str(chat_id)  # type: ignore
    await db.commit()

    nome = licenca.cliente_nome or "Cliente"
    dias = licenca.dias_restantes or 0

    return (
        True,
        f"""
✅ *Licença ativada com sucesso!*

Olá, *{nome}*! 🎉

Você agora receberá notificações de:
• ✅ HITs (acertos)
• ❌ MISSes (erros)
• 🚨 Alertas de Stop Loss
• 🏆 Meta atingida
• 📊 Relatórios periódicos

📅 *Dias restantes:* {dias} dias

_Boas operações! 🚀_
    """.strip(),
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

    # Processar comandos
    if text == "/start":
        # Iniciar processo de vinculação
        user_states[chat_id] = "waiting_license"

        welcome_message = f"""
🤖 *Bem-vindo ao TucunaréBot!*

Olá, {user_name}! 👋

Para ativar as notificações, preciso vincular sua licença.

📝 *Digite sua chave de licença:*
_(Formato: XXXX-XXXX-XXXX-XXXX)_

A chave foi enviada no seu email de compra.
        """.strip()

        await send_telegram_message(chat_id, welcome_message)
        return {"ok": True}

    elif text == "/status":
        # Verificar status da vinculação
        result = await db.execute(
            select(Licenca).where(Licenca.telegram_chat_id == str(chat_id))
        )
        licenca = result.scalar_one_or_none()

        if licenca:
            dias = licenca.dias_restantes or 0
            status_msg = f"""
✅ *Licença Vinculada*

📋 Chave: `{licenca.chave}`
📅 Dias restantes: {dias}
🔔 Notificações: Ativas

Use /desativar para parar as notificações.
            """.strip()
        else:
            status_msg = """
❌ *Nenhuma licença vinculada*

Use /start para vincular sua licença.
            """.strip()

        await send_telegram_message(chat_id, status_msg)
        return {"ok": True}

    elif text == "/desativar":
        # Desativar notificações (remover chat_id)
        result = await db.execute(
            select(Licenca).where(Licenca.telegram_chat_id == str(chat_id))
        )
        licenca = result.scalar_one_or_none()

        if licenca:
            licenca.telegram_chat_id = None  # type: ignore
            await db.commit()
            # Fix E501: Quebra de string
            msg = "🔕 *Notificações desativadas*\n\n" "Use /start para reativar."
            await send_telegram_message(chat_id, msg)
        else:
            await send_telegram_message(
                chat_id, "❌ Nenhuma licença vinculada a este Telegram."
            )

        return {"ok": True}

    # Sourcery Fix: Merge comparisons with 'in'
    elif text in ["/ajuda", "/help"]:
        help_message = """
🆘 *Comandos Disponíveis*

/start - Vincular licença
/status - Ver status da licença
/desativar - Parar notificações
/ajuda - Ver esta mensagem

📞 *Suporte:* Entre em contato pelo WhatsApp no site tucunarebot.com.br
        """.strip()

        await send_telegram_message(chat_id, help_message)
        return {"ok": True}

    # Se está esperando a chave de licença
    elif user_states.get(chat_id) == "waiting_license":
        # Tentar validar como chave de licença
        success, response_message = await validate_and_link_license(
            chat_id=chat_id,
            license_key=text,
            db=db,
        )

        if success:
            # Limpar estado
            user_states.pop(chat_id, None)

        await send_telegram_message(chat_id, response_message)
        return {"ok": True}

    # Mensagem não reconhecida
    else:
        # Fix E501: Quebra de string
        msg = "🤔 Não entendi.\n\n" "Use /ajuda para ver os comandos disponíveis."
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
        return {"error": "TELEGRAM_BOT_TOKEN não configurado"}

    # Fix E501: URL longa na docstring (ver docstring original do metodo acima)
    base = "https://crash-api-jose.onrender.com"
    webhook_url = f"{base}/api/v1/telegram/webhook"

    try:
        async with httpx.AsyncClient() as client:
            # Primeiro, deletar webhook existente
            await client.get(f"{TELEGRAM_API_URL}/deleteWebhook")

            # Configurar novo webhook
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
                    "error": result.get("description", "Erro desconhecido"),
                }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# ENDPOINT: INFO DO WEBHOOK
# ============================================================================


@router.get("/webhook-info")
async def webhook_info():
    """Retorna informações do webhook atual."""
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN não configurado"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TELEGRAM_API_URL}/getWebhookInfo",
                timeout=10.0,
            )
            return response.json()

    except Exception as e:
        return {"error": str(e)}
