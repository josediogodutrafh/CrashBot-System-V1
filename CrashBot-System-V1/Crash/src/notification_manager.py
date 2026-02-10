#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NOTIFICATION MANAGER
Envia alertas (ex: Telegram) em uma thread separada para não bloquear o bot.
"""

import logging
import threading

import requests

# Configuração do logger
logger = logging.getLogger(__name__)

# Variáveis globais para guardar as credenciais (serão carregadas 1 vez)
BOT_TOKEN = None
CHAT_ID = None


def load_credentials(token: str, chat_id: str):
    """Recebe as credenciais do bot_controller."""
    global BOT_TOKEN, CHAT_ID
    BOT_TOKEN = token
    CHAT_ID = chat_id
    logger.info("Credenciais do Telegram carregadas no NotificationManager.")


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
        "parse_mode": "Markdown",  # Permite usar negrito (*texto*), etc.
    }

    try:
        requests.get(url, params=params, timeout=5)  # 5 segundos de timeout
    except requests.RequestException as e:
        logger.error(f"Exceção ao enviar alerta Telegram: {e}")


def send_telegram_alert(message: str):
    """
    Função principal. Inicia o envio da mensagem em uma nova thread
    para não bloquear o loop principal do bot.
    """
    try:
        # Cria e inicia a thread de envio
        alert_thread = threading.Thread(
            target=_send_message_task, args=(message,), daemon=True
        )
        alert_thread.start()
    except Exception as e:
        logger.error(f"Erro ao iniciar thread de alerta: {e}")
