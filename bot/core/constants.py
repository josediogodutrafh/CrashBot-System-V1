#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - CONSTANTES GLOBAIS

Centraliza todas as constantes do sistema em um único lugar.
Evita "magic numbers" e strings espalhadas pelo código.
"""

from typing import Any, Dict

# ═══════════════════════════════════════════════════════════════════════════════
# VERSÃO E IDENTIFICAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

BOT_VERSION = "3.0.0"
BOT_NAME = "TucunaréBot"
BOT_AUTHOR = "TucunaréBot"

# ═══════════════════════════════════════════════════════════════════════════════
# PLATAFORMAS SUPORTADAS
# ═══════════════════════════════════════════════════════════════════════════════

SUPPORTED_PLATFORMS = ["Brabet", "OneBra", "WinBra", "PGWin"]
DEFAULT_PLATFORM = "Brabet"

PLATFORM_DETAILS: Dict[str, Dict[str, Any]] = {
    "Brabet": {
        "display_name": "Brabet",
        "color": (168, 85, 247),  # purple
        "affiliate_url": "https://www.brabet.com/?agentid=135486005",
    },
    "OneBra": {
        "display_name": "OneBra",
        "color": (59, 130, 246),  # blue
        "affiliate_url": "",
    },
    "WinBra": {
        "display_name": "WinBra",
        "color": (34, 197, 94),  # green
        "affiliate_url": "",
    },
    "PGWin": {
        "display_name": "PGWin",
        "color": (234, 179, 8),  # amber
        "affiliate_url": "",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# API E ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

API_BASE_URL = "https://crash-api-jose.onrender.com"

# Endpoints
API_ENDPOINTS = {
    "validate_license": "/validar",
    "check_version": "/api/v1/bot/versao",
    "telemetry": "/api/v1/telemetria/log",
}

# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN_DEFAULT = "8329220374:AAHsK2aMseiAJpxzggsRutkz-S638eQWc8s"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE MODOS DE RISCO
# ═══════════════════════════════════════════════════════════════════════════════

RISK_MODE_CONFIG: Dict[str, Dict[str, Any]] = {
    "CONSERVADOR": {
        "banca_percent": 0.33,  # Usa 33% da banca real
        "gatilho_opcoes": [8],  # Sempre 8 velas
        "meta_min": 0.25,  # Meta entre 25% e 40%
        "meta_max": 0.40,
        "color": "green",
        "emoji": "🛡️",
    },
    "MODERADO": {
        "banca_percent": 0.50,  # Usa 50% da banca real
        "gatilho_opcoes": [7, 8],  # Sorteia entre 7 ou 8
        "meta_min": 0.30,  # Meta entre 30% e 45%
        "meta_max": 0.45,
        "color": "yellow",
        "emoji": "⚖️",
    },
    "AGRESSIVO": {
        "banca_percent": 1.00,  # Usa 100% da banca real
        "gatilho_opcoes": [6, 7],  # Sorteia entre 6 ou 7
        "meta_min": 0.35,  # Meta entre 35% e 55%
        "meta_max": 0.55,
        "color": "red",
        "emoji": "⚔️",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE MARTINGALE
# ═══════════════════════════════════════════════════════════════════════════════

MARTINGALE_MAX_DOBRA = 4
MARTINGALE_MULTIPLIERS = {1: 1, 2: 2, 3: 4, 4: 8}
MARTINGALE_BANCA_DIVISOR = 15  # Banca operacional / 15

# Target range para apostas (randomizado para anti-detecção)
TARGET_MIN = 1.81
TARGET_MAX = 1.95

# Limiar para considerar "vela baixa"
LOW_THRESHOLD = 2.0

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE ML
# ═══════════════════════════════════════════════════════════════════════════════

ML_CONFIDENCE_THRESHOLD = 0.80
ML_REQUIRED_HISTORY = 250
ML_TARGET_MULTIPLIER = 2.0

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE SESSÃO
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_SESSION_HOURS = 8
DEFAULT_MAX_ROUNDS = 1000
SUSPENSION_HOURS = 4  # Horas de suspensão após meta
SUSPENSION_SECONDS = SUSPENSION_HOURS * 3600

# Stop loss padrão
DEFAULT_STOP_LOSS_PERCENT = 0.50  # 50%

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE TIMING
# ═══════════════════════════════════════════════════════════════════════════════

# Intervalos de threads
BALANCE_CHECK_INTERVAL = 3.0  # Segundos entre verificações de saldo
FRAME_CAPTURE_INTERVAL = 0.05  # Segundos entre capturas de frame
COOLDOWN_AFTER_BET = 8  # Segundos de cooldown após detecção de aposta

# Timeouts
API_TIMEOUT = 10  # Segundos para requests à API
LICENSE_CHECK_TIMEOUT = 10  # Segundos para validar licença

# Relatório periódico
PERIODIC_REPORT_INTERVAL = 1800  # 30 minutos em segundos

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

# Mudança drástica de saldo (requer confirmação)
BALANCE_CHANGE_THRESHOLD_PERCENT = 30

# Range válido de saldo
BALANCE_MIN = 0.01
BALANCE_MAX = 1_000_000

# Range válido de multiplicador
MULTIPLIER_MIN = 1.0
MULTIPLIER_MAX = 999.99

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE SEGURANÇA
# ═══════════════════════════════════════════════════════════════════════════════

# Limiares de segurança (fase arrecadatória)
DANGER_STD_THRESHOLD = 2.3
DANGER_MEAN_THRESHOLD = 2.5

# Alerta de velas baixas consecutivas
LOW_ALERT_THRESHOLD = 6

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE UI
# ═══════════════════════════════════════════════════════════════════════════════

# Cores do tema (para DearPyGui)
THEME_COLORS = {
    "background": (15, 23, 42),  # slate-950
    "card": (30, 41, 59),  # slate-800
    "border": (71, 85, 105),  # slate-600
    "text_primary": (255, 255, 255),  # white
    "text_secondary": (148, 163, 184),  # slate-400
    "accent_cyan": (6, 182, 212),  # cyan-500
    "accent_emerald": (34, 197, 94),  # emerald-500
    "accent_amber": (234, 179, 8),  # amber-500
    "accent_red": (239, 68, 68),  # red-500
    "accent_purple": (168, 85, 247),  # purple-500
}

# Tamanhos de fonte
FONT_SIZES = {
    "title": 32,
    "heading": 24,
    "body": 16,
    "small": 12,
    "mono": 14,
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE SONS
# ═══════════════════════════════════════════════════════════════════════════════

# Frequências para winsound.Beep (Windows)
SOUND_HIT = {"frequency": 1500, "duration": 150}
SOUND_MISS = {"frequency": 700, "duration": 300}
SOUND_ALERT = {"frequency": 500, "duration": 1000}

# ═══════════════════════════════════════════════════════════════════════════════
# MENSAGENS E TEXTOS
# ═══════════════════════════════════════════════════════════════════════════════

MESSAGES = {
    "session_started": "✅ Sessão iniciada",
    "session_ended": "🏁 Sessão finalizada",
    "license_valid": "✅ Licença válida",
    "license_invalid": "❌ Licença inválida",
    "balance_detected": "💰 Saldo detectado",
    "goal_reached": "🏆 META ATINGIDA!",
    "stop_loss": "🚨 STOP LOSS ATINGIDO!",
    "waiting": "⏳ Aguardando...",
    "betting": "✅ Apostando...",
    "skipped": "⏸️ Pulou",
}

# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORDS PARA OCR
# ═══════════════════════════════════════════════════════════════════════════════

BET_DETECTION_KEYWORDS = [
    "APOSTA",
    "APOSTAR",
    "APOSTE",
    "BET",
    "APOST",
    "POSTA",
]

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTADO DE APOSTAS
# ═══════════════════════════════════════════════════════════════════════════════

RESULTADO_HIT = "hit"
RESULTADO_MISS = "miss"
