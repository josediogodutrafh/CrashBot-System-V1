#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NOTIFICATION MANAGER
Envia alertas via Telegram em uma thread separada para não bloquear o bot.

Suporta:
- Thread-local platform context (cada PlatformSession seta seu nome)
- Roteamento via telegram_bot.py (quando o bot interativo está rodando)
- Fallback para HTTP direto quando o bot não está disponível
"""

import logging
import threading

import requests

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Configuração do logger
logger = logging.getLogger(__name__)

# ==============================================================================
# CREDENCIAIS DO TELEGRAM (carregadas do .env via config.py)
# ==============================================================================
BOT_TOKEN = TELEGRAM_BOT_TOKEN
CHAT_ID = TELEGRAM_CHAT_ID

# ==============================================================================
# CONTEXTO DE PLATAFORMA (thread-local)
# ==============================================================================
_context = threading.local()


def set_platform_context(platform_name: str):
    """Define o nome da plataforma para a thread atual.

    Chamado por PlatformSession._run() no início de cada thread.
    Todas as notificações disparadas nessa thread terão o prefixo.
    """
    _context.platform_name = platform_name


def _get_platform_prefix() -> str:
    """Retorna '[BRABET] ' ou '' conforme contexto da thread."""
    name = getattr(_context, "platform_name", "")
    return f"[{name.upper()}] " if name else ""


def load_credentials(token: str, chat_id: str):
    """Recebe as credenciais do bot_controller (opcional agora)."""
    global BOT_TOKEN, CHAT_ID
    BOT_TOKEN = token
    CHAT_ID = chat_id
    logger.info("Credenciais do Telegram atualizadas.")


def _send_message_task(message: str):
    """
    Função executada na thread para enviar a mensagem via API do Telegram.
    """
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Token/ChatID do Telegram não configurados. Alerta ignorado.")
        return

    # URL da API do Telegram para enviar mensagens
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Parâmetros da mensagem
    params = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            logger.info(f"Alerta Telegram enviado: {message[:50]}...")
        else:
            logger.error(f"Erro ao enviar Telegram: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Exceção ao enviar alerta Telegram: {e}")


def send_telegram_alert(message: str):
    """
    Função principal. Tenta enviar via bot interativo (se rodando),
    senão faz fallback para HTTP direto em thread daemon.
    """
    try:
        from src.notifications.telegram_bot import send_push
        send_push(message)
        return
    except (ImportError, RuntimeError):
        pass
    except Exception as e:
        logger.debug(f"Bot indisponível, usando fallback HTTP: {e}")

    # Fallback: HTTP direto em thread daemon
    try:
        alert_thread = threading.Thread(
            target=_send_message_task, args=(message,), daemon=True
        )
        alert_thread.start()
    except Exception as e:
        logger.error(f"Erro ao iniciar thread de alerta: {e}")


# ==============================================================================
# ALERTAS ESPECIALIZADOS
# ==============================================================================

def notify_trick(lows_count: int, setup_name: str):
    """Alerta de trick (gatilho atingido)."""
    p = _get_platform_prefix()
    send_telegram_alert(
        f"{p}⚠️ *TRICK:* {lows_count} baixas consecutivas!\n"
        f"Entrando com *{setup_name}*..."
    )


def notify_hit(dobra: int, profit: float, balance: float):
    """Alerta de aposta ganha."""
    p = _get_platform_prefix()
    send_telegram_alert(
        f"{p}✅ *HIT!* Bet {dobra} | +R${profit:.2f}\n"
        f"Saldo: R${balance:.2f}"
    )


def notify_miss(dobra: int, max_dobras: int, next_bet: float):
    """Alerta de aposta perdida (continua ciclo)."""
    p = _get_platform_prefix()
    if next_bet > 0:
        send_telegram_alert(
            f"{p}❌ *MISS!* Bet {dobra}/{max_dobras}\n"
            f"Recovery: R${next_bet:.2f}"
        )
    else:
        send_telegram_alert(
            f"{p}❌ *MISS!* Bet {dobra}/{max_dobras}"
        )


def notify_break(setup_name: str, loss: float):
    """Alerta de bust (ciclo perdido)."""
    p = _get_platform_prefix()
    send_telegram_alert(
        f"{p}💀 *BREAK!* Ciclo perdido no {setup_name}\n"
        f"-R${loss:.2f}"
    )


def notify_meta_reached(profit: float, percent: int):
    """Alerta de meta atingida."""
    p = _get_platform_prefix()
    send_telegram_alert(
        f"{p}🎯 *META ATINGIDA!* +{percent}% (+R${profit:.2f})\n"
        f"Saque disponível!"
    )


def notify_withdrawal(amount: float, base: float):
    """Alerta de saque executado."""
    p = _get_platform_prefix()
    send_telegram_alert(
        f"{p}💰 *SAQUE:* R${amount:.2f} sacado\n"
        f"Banca resetada para R${base:.2f}"
    )


def notify_deposit(amount: float, total: float):
    """Alerta de reposição após bust."""
    p = _get_platform_prefix()
    send_telegram_alert(
        f"{p}🔄 *REPOSIÇÃO:* R${amount:.2f} depositado\n"
        f"Total investido: R${total:.2f}"
    )


def notify_setup_change(old_name: str, new_name: str):
    """Alerta de troca de setup."""
    p = _get_platform_prefix()
    send_telegram_alert(
        f"{p}🔄 *Setup alterado:* {old_name} → {new_name}"
    )


def notify_premium_change(is_premium: bool, hour: int, day: str):
    """Alerta de mudança de horário premium."""
    p = _get_platform_prefix()
    if is_premium:
        send_telegram_alert(
            f"{p}🟢 Entrando em horário *PREMIUM* ({hour}h - {day})"
        )
    else:
        send_telegram_alert(
            f"{p}🔴 Saindo do horário premium ({hour}h - {day}). Pausando..."
        )


def notify_session_summary(stats: dict):
    """Resumo da sessão."""
    p = _get_platform_prefix()
    lines = [
        f"{p}📊 *RESUMO DA SESSÃO*",
        f"Lucro líquido: R${stats.get('net_profit', 0):.2f}",
        f"Total sacado: R${stats.get('total_withdrawn', 0):.2f}",
        f"Total depositado: R${stats.get('total_deposited', 0):.2f}",
        f"Saques: {stats.get('n_withdrawals', 0)}",
        f"Depósitos: {stats.get('n_deposits', 0)}",
    ]
    if 'roi' in stats:
        lines.append(f"ROI: {stats['roi']:.1f}%")
    send_telegram_alert("\n".join(lines))


# ==============================================================================
# NOVAS NOTIFICAÇÕES ENRIQUECIDAS
# ==============================================================================

def notify_bet_placed(amount: float, target: float, strategy_name: str, safety_level: str = ""):
    """Alerta de aposta executada (antes do resultado)."""
    p = _get_platform_prefix()
    level_str = f" | Safety: {safety_level}" if safety_level else ""
    send_telegram_alert(
        f"{p}🎯 *BET* R${amount:.2f} @ {target:.2f}x\n"
        f"{strategy_name}{level_str}"
    )


def notify_advisor_change(msg: str):
    """Alerta de mudança do StrategyAdvisor (nível/setup)."""
    p = _get_platform_prefix()
    send_telegram_alert(f"{p}🔄 {msg}")


# ==============================================================================
# TESTE: Se rodar este arquivo diretamente, envia uma mensagem de teste
# ==============================================================================
if __name__ == "__main__":
    print("Enviando mensagem de teste...")
    send_telegram_alert(
        "🚀 *Teste do Bot Crash!*\n\nSe você recebeu isso, está funcionando!"
    )
    print("Mensagem enviada! Verifique seu Telegram.")

    # Aguarda a thread terminar
    import time

    time.sleep(3)
