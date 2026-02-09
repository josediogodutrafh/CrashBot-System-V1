#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NOTIFICATION MANAGER
Envia alertas via Telegram em uma thread separada para não bloquear o bot.
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
    Função principal. Inicia o envio da mensagem em uma nova thread
    para não bloquear o loop principal do bot.
    """
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
    send_telegram_alert(
        f"⚠️ *TRICK:* {lows_count} baixas consecutivas!\n"
        f"Entrando com *{setup_name}*..."
    )


def notify_hit(dobra: int, profit: float, balance: float):
    """Alerta de aposta ganha."""
    send_telegram_alert(
        f"✅ *HIT!* Dobra {dobra} | +R${profit:.2f}\n"
        f"Saldo: R${balance:.2f}"
    )


def notify_miss(dobra: int, max_dobras: int, next_bet: float):
    """Alerta de aposta perdida (continua ciclo)."""
    send_telegram_alert(
        f"❌ *MISS!* Dobra {dobra}/{max_dobras}\n"
        f"Próxima: R${next_bet:.2f}"
    )


def notify_break(setup_name: str, loss: float):
    """Alerta de bust (ciclo perdido)."""
    send_telegram_alert(
        f"💀 *BREAK!* Ciclo perdido no {setup_name}\n"
        f"-R${loss:.2f} | Repondo banca..."
    )


def notify_meta_reached(profit: float, percent: int):
    """Alerta de meta atingida."""
    send_telegram_alert(
        f"🎯 *META ATINGIDA!* +{percent}% (+R${profit:.2f})\n"
        f"Saque disponível!"
    )


def notify_withdrawal(amount: float, base: float):
    """Alerta de saque executado."""
    send_telegram_alert(
        f"💰 *SAQUE:* R${amount:.2f} sacado\n"
        f"Banca resetada para R${base:.2f}"
    )


def notify_deposit(amount: float, total: float):
    """Alerta de reposição após bust."""
    send_telegram_alert(
        f"🔄 *REPOSIÇÃO:* R${amount:.2f} depositado\n"
        f"Total investido: R${total:.2f}"
    )


def notify_setup_change(old_name: str, new_name: str):
    """Alerta de troca de setup."""
    send_telegram_alert(
        f"🔄 *Setup alterado:* {old_name} → {new_name}"
    )


def notify_premium_change(is_premium: bool, hour: int, day: str):
    """Alerta de mudança de horário premium."""
    if is_premium:
        send_telegram_alert(
            f"🟢 Entrando em horário *PREMIUM* ({hour}h - {day})"
        )
    else:
        send_telegram_alert(
            f"🔴 Saindo do horário premium ({hour}h - {day}). Pausando apostas..."
        )


def notify_session_summary(stats: dict):
    """Resumo da sessão."""
    lines = [
        "📊 *RESUMO DA SESSÃO*",
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
