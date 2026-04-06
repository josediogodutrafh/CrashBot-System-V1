#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TELEGRAM BOT INTERATIVO
========================
Bot com InlineKeyboard para consultar dados de cada plataforma.
Roda em thread daemon com asyncio loop próprio.

Funcionalidades:
- /start, /menu → Menu principal com plataformas
- /status → Resumo rápido de todas plataformas
- InlineKeyboard → saldo, estratégia, apostas, índices, relatório

Lifecycle:
    start_bot(brain, token, chat_id)  → inicia polling em thread daemon
    stop_bot()                         → encerra graciosamente
    send_push(text)                    → envia notificação thread-safe
"""

import asyncio
import logging
import threading
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# SINGLETON STATE
# ══════════════════════════════════════════════════════════════════════

_app: Optional[Application] = None
_brain = None  # MultiPlatformController
_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_chat_id: str = ""


# ══════════════════════════════════════════════════════════════════════
# LIFECYCLE
# ══════════════════════════════════════════════════════════════════════

def start_bot(brain, token: str, chat_id: str):
    """Inicia o bot interativo em thread daemon.

    Args:
        brain: MultiPlatformController (referência para consultar estado)
        token: Bot token do Telegram
        chat_id: Chat ID autorizado para receber mensagens
    """
    global _app, _brain, _loop, _thread, _chat_id

    if not token or not chat_id:
        logger.warning("Telegram bot: token/chat_id não configurados — bot não iniciado")
        return

    if _thread and _thread.is_alive():
        logger.warning("Telegram bot já está rodando")
        return

    _brain = brain
    _chat_id = str(chat_id)

    _thread = threading.Thread(target=_run_bot, args=(token,), daemon=True, name="telegram-bot")
    _thread.start()
    logger.info("Telegram bot interativo iniciado em thread daemon")


def stop_bot():
    """Encerra o bot graciosamente."""
    global _app, _loop, _thread

    if _app and _loop and _loop.is_running():
        try:
            future = asyncio.run_coroutine_threadsafe(_app.stop(), _loop)
            future.result(timeout=5)
        except Exception as e:
            logger.debug(f"Erro ao parar bot: {e}")

    if _loop and _loop.is_running():
        _loop.call_soon_threadsafe(_loop.stop)

    _app = None
    _loop = None
    _thread = None
    logger.info("Telegram bot encerrado")


def send_push(text: str):
    """Envia notificação push thread-safe.

    Chamado pelo telegram.py (roteamento) de qualquer thread.
    Usa run_coroutine_threadsafe para injetar no loop do bot.

    Raises:
        RuntimeError: Se o bot não está rodando.
    """
    if not _app or not _loop or not _loop.is_running():
        raise RuntimeError("Bot não está rodando")

    asyncio.run_coroutine_threadsafe(_async_send_push(text), _loop)


async def _async_send_push(text: str):
    """Envia mensagem via bot (async)."""
    try:
        await _app.bot.send_message(
            chat_id=_chat_id,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro send_push: {e}")


def _run_bot(token: str):
    """Thread principal do bot — cria loop asyncio e roda polling."""
    global _app, _loop

    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    try:
        _loop.run_until_complete(_start_polling(token))
    except Exception as e:
        logger.error(f"Telegram bot encerrou com erro: {e}")
    finally:
        try:
            _loop.close()
        except Exception:
            pass


async def _start_polling(token: str):
    """Configura handlers e inicia polling."""
    global _app

    builder = Application.builder().token(token)
    _app = builder.build()

    # Comandos
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("menu", cmd_start))
    _app.add_handler(CommandHandler("status", cmd_status))

    # Callbacks (InlineKeyboard)
    _app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Telegram bot: iniciando polling...")
    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=False)

    # Manter rodando até o loop ser parado externamente
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()


# ══════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start ou /menu — mostra menu principal."""
    if not _check_authorized(update):
        return

    keyboard = _build_main_menu()
    await update.message.reply_text(
        "🎰 *Crash Lab - Menu Principal*\n\nEscolha uma plataforma:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status — resumo rápido de todas as plataformas."""
    if not _check_authorized(update):
        return

    text = _format_general_report()
    await update.message.reply_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════
# CALLBACK HANDLER (InlineKeyboard)
# ══════════════════════════════════════════════════════════════════════

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteia callbacks do InlineKeyboard."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data:
        return

    # Menu principal
    if data == "main_menu":
        keyboard = _build_main_menu()
        await query.edit_message_text(
            "🎰 *Crash Lab - Menu Principal*\n\nEscolha uma plataforma:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    # Relatório geral
    if data == "general_report":
        text = _format_general_report()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("« Voltar", callback_data="main_menu")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    # Seleção de plataforma → sub-menu
    if data.startswith("platform:"):
        platform = data.split(":")[1]
        keyboard = _build_platform_menu(platform)
        await query.edit_message_text(
            f"📊 *{platform.upper()}*\n\nEscolha uma informação:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    # Ação em plataforma
    if data.startswith("action:"):
        parts = data.split(":")
        if len(parts) < 3:
            return
        platform = parts[1]
        action = parts[2]

        text = _dispatch_action(platform, action)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("« Voltar", callback_data=f"platform:{platform}")],
            [InlineKeyboardButton("« Menu Principal", callback_data="main_menu")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return


# ══════════════════════════════════════════════════════════════════════
# MENU BUILDERS
# ══════════════════════════════════════════════════════════════════════

def _build_main_menu() -> InlineKeyboardMarkup:
    """Constrói menu principal com plataformas disponíveis."""
    if not _brain:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("Bot não conectado", callback_data="main_menu")
        ]])

    buttons = []
    row = []
    for name in _brain.platform_names:
        session = _brain.sessions.get(name)
        icon = "🟢" if session and session.running else "⚫"
        row.append(InlineKeyboardButton(
            f"{icon} {name.capitalize()}",
            callback_data=f"platform:{name}",
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("📋 Relatório Geral", callback_data="general_report")])
    return InlineKeyboardMarkup(buttons)


def _build_platform_menu(platform: str) -> InlineKeyboardMarkup:
    """Constrói sub-menu de uma plataforma."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Saldo", callback_data=f"action:{platform}:saldo"),
            InlineKeyboardButton("🧠 Estratégia", callback_data=f"action:{platform}:estrategia"),
        ],
        [
            InlineKeyboardButton("🎲 Apostas", callback_data=f"action:{platform}:apostas"),
            InlineKeyboardButton("📈 Índices", callback_data=f"action:{platform}:indices"),
        ],
        [
            InlineKeyboardButton("📋 Relatório Completo", callback_data=f"action:{platform}:full"),
        ],
        [
            InlineKeyboardButton("« Voltar", callback_data="main_menu"),
        ],
    ])


# ══════════════════════════════════════════════════════════════════════
# ACTION DISPATCHER
# ══════════════════════════════════════════════════════════════════════

def _dispatch_action(platform: str, action: str) -> str:
    """Roteia ação para o formatador correto."""
    formatters = {
        "saldo": _format_platform_saldo,
        "estrategia": _format_platform_strategy,
        "apostas": _format_platform_bets,
        "indices": _format_platform_indices,
        "full": _format_platform_full_report,
    }
    formatter = formatters.get(action)
    if not formatter:
        return f"Ação desconhecida: {action}"
    return formatter(platform)


# ══════════════════════════════════════════════════════════════════════
# DATA FORMATTERS
# ══════════════════════════════════════════════════════════════════════

def _get_session(platform: str):
    """Retorna PlatformSession ou None."""
    if not _brain:
        return None
    return _brain.sessions.get(platform)


def _format_platform_saldo(platform: str) -> str:
    """Formata informações financeiras da plataforma."""
    session = _get_session(platform)
    if not session:
        return f"⚫ *{platform.upper()}* — plataforma não encontrada"

    state = session.get_state()
    bk = session.bankroll

    saldo = state.get("saldo", 0.0)
    caixa = state.get("caixa", 0.0)
    banca_config = state.get("banca", 0.0)
    profit = state.get("session_profit", 0.0)
    eff_banca = bk.effective_banca
    peak = bk._peak_bankroll
    dd = bk.drawdown_from_peak * 100

    status_icon = "🟢" if state.get("running") else "⚫"
    profit_icon = "📈" if profit >= 0 else "📉"

    return (
        f"{status_icon} *{platform.upper()} — Saldo*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Saldo atual: R${saldo:.2f}\n"
        f"🏦 Caixa (reserva): R${caixa:.2f}\n"
        f"📊 Banca efetiva: R${eff_banca:.2f}\n"
        f"📊 Banca config: R${banca_config:.2f}\n"
        f"🏔️ Pico da sessão: R${peak:.2f}\n"
        f"📉 Drawdown do pico: {dd:.1f}%\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{profit_icon} Lucro sessão: R${profit:+.2f}"
    )


def _format_platform_strategy(platform: str) -> str:
    """Formata informações de estratégia e advisor."""
    session = _get_session(platform)
    if not session:
        return f"⚫ *{platform.upper()}* — plataforma não encontrada"

    state = session.get_state()
    advisor = state.get("advisor", {})

    setup = state.get("setup_name", "N/A")
    active = state.get("martingale_active", False)
    dobra = state.get("dobra_atual", 0)
    max_d = state.get("max_dobras", 0)
    baixos = state.get("baixos_consecutivos", 0)

    # Safety Index
    si = advisor.get("safety_index", 0.0)
    level = advisor.get("safety_level", "N/A")
    color = advisor.get("safety_color", "⚪")
    paused = advisor.get("pause_bets", False)
    last_action = advisor.get("last_action", "—")

    # Scores individuais
    dist = advisor.get("distribution_score", 0.0)
    dd = advisor.get("drawdown_score", 0.0)
    wr = advisor.get("win_rate_score", 0.0)
    pf = advisor.get("profit_score", 0.0)
    bk = advisor.get("bankroll_score", 0.0)

    cycle_str = f"Bet {dobra}/{max_d}" if active else "Inativo"
    pause_str = " ⏸️ PAUSADO" if paused else ""

    return (
        f"🧠 *{platform.upper()} — Estratégia*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Setup: *{setup}*\n"
        f"🎯 Ciclo: {cycle_str}\n"
        f"📊 Baixos consecutivos: {baixos}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🛡️ Safety Index: *{si:.2f}* ({level}){pause_str}\n"
        f"   Distribuição: {dist:.2f}\n"
        f"   Drawdown: {dd:.2f}\n"
        f"   Win Rate: {wr:.2f}\n"
        f"   Profit: {pf:.2f}\n"
        f"   Bankroll: {bk:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Último advisor: {last_action}"
    )


def _format_platform_bets(platform: str) -> str:
    """Formata informações de apostas da sessão."""
    session = _get_session(platform)
    if not session:
        return f"⚫ *{platform.upper()}* — plataforma não encontrada"

    state = session.get_state()

    hits = state.get("session_hits", 0)
    misses = state.get("session_misses", 0)
    total_bets = hits + misses
    rounds = state.get("round_count", 0)
    ws_rounds = state.get("ws_rounds", 0)
    ws_connected = state.get("ws_connected", False)
    sequences = state.get("total_sequences", 0)
    wins = state.get("total_wins", 0)
    breaks = state.get("total_breaks", 0)
    profit = state.get("session_profit", 0.0)
    last = state.get("last_action", "—")

    hit_rate = (hits / total_bets * 100) if total_bets > 0 else 0.0
    ws_icon = "🟢" if ws_connected else "🔴"

    return (
        f"🎲 *{platform.upper()} — Apostas*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Hits: {hits}\n"
        f"❌ Misses: {misses}\n"
        f"📊 Hit rate: {hit_rate:.1f}%\n"
        f"💰 Lucro: R${profit:+.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Ciclos: {sequences} (W:{wins} / B:{breaks})\n"
        f"📡 Rounds: {rounds} (WS: {ws_rounds})\n"
        f"{ws_icon} WebSocket: {'conectado' if ws_connected else 'desconectado'}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 {last}"
    )


def _format_platform_indices(platform: str) -> str:
    """Formata índices e estatísticas do DB (7 dias)."""
    session = _get_session(platform)
    if not session:
        return f"⚫ *{platform.upper()}* — plataforma não encontrada"

    # Dados da sessão atual
    state = session.get_state()
    hits = state.get("session_hits", 0)
    misses = state.get("session_misses", 0)
    total_bets = hits + misses
    profit = state.get("session_profit", 0.0)
    hit_rate = (hits / total_bets * 100) if total_bets > 0 else 0.0

    # Profit factor
    # (simplificado: lucro dos hits / perda dos misses)
    banca_cfg = state.get("banca", 1.0)
    if misses > 0 and banca_cfg > 0:
        avg_win = profit / hits if hits > 0 and profit > 0 else 0
        pf_str = f"{avg_win:.2f}" if avg_win > 0 else "N/A"
    else:
        pf_str = "∞" if hits > 0 else "N/A"

    # Dados do DB (7 dias)
    db_stats = {}
    try:
        db_stats = session.db_manager.get_platform_stats(platform, 7)
    except Exception:
        pass

    db_rounds = db_stats.get("total_rounds", 0)
    db_bets = db_stats.get("total_bets", 0)
    db_hits = db_stats.get("hits", 0)
    db_hr = db_stats.get("hit_rate", 0.0)
    db_profit = db_stats.get("profit", 0.0)
    db_avg = db_stats.get("avg_multiplier", 0.0)

    return (
        f"📈 *{platform.upper()} — Índices*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"*Sessão Atual:*\n"
        f"  Hit rate: {hit_rate:.1f}% ({hits}/{total_bets})\n"
        f"  Lucro: R${profit:+.2f}\n"
        f"  Profit factor: {pf_str}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"*Últimos 7 dias (DB):*\n"
        f"  Rounds: {db_rounds}\n"
        f"  Apostas: {db_bets} (hits: {db_hits})\n"
        f"  Hit rate: {db_hr:.1f}%\n"
        f"  Lucro: R${db_profit:+.2f}\n"
        f"  Mult. médio: {db_avg:.2f}x"
    )


def _format_platform_full_report(platform: str) -> str:
    """Relatório completo de uma plataforma."""
    session = _get_session(platform)
    if not session:
        return f"⚫ *{platform.upper()}* — plataforma não encontrada"

    state = session.get_state()
    advisor = state.get("advisor", {})
    bk = session.bankroll

    # Financial
    saldo = state.get("saldo", 0.0)
    caixa = state.get("caixa", 0.0)
    eff_banca = bk.effective_banca
    peak = bk._peak_bankroll
    dd_pct = bk.drawdown_from_peak * 100
    profit = state.get("session_profit", 0.0)

    # Strategy
    setup = state.get("setup_name", "N/A")
    active = state.get("martingale_active", False)
    dobra = state.get("dobra_atual", 0)
    max_d = state.get("max_dobras", 0)
    baixos = state.get("baixos_consecutivos", 0)

    # Bets
    hits = state.get("session_hits", 0)
    misses = state.get("session_misses", 0)
    total_bets = hits + misses
    rounds = state.get("round_count", 0)
    sequences = state.get("total_sequences", 0)
    wins = state.get("total_wins", 0)
    breaks = state.get("total_breaks", 0)
    hit_rate = (hits / total_bets * 100) if total_bets > 0 else 0.0

    # Safety
    si = advisor.get("safety_index", 0.0)
    level = advisor.get("safety_level", "N/A")
    paused = advisor.get("pause_bets", False)

    # WS
    ws_connected = state.get("ws_connected", False)
    ws_icon = "🟢" if ws_connected else "🔴"

    # DB 7d
    db_stats = {}
    try:
        db_stats = session.db_manager.get_platform_stats(platform, 7)
    except Exception:
        pass

    cycle_str = f"Bet {dobra}/{max_d}" if active else "Inativo"
    status_icon = "🟢" if state.get("running") else "⚫"
    pause_str = " ⏸️" if paused else ""
    profit_icon = "📈" if profit >= 0 else "📉"

    lines = [
        f"{status_icon} *{platform.upper()} — Relatório Completo*",
        f"━━━━━━━━━━━━━━━━━━━━━━━",
        f"",
        f"*💰 Financeiro:*",
        f"  Saldo: R${saldo:.2f}",
        f"  Banca efetiva: R${eff_banca:.2f}",
        f"  Caixa: R${caixa:.2f}",
        f"  Pico: R${peak:.2f} | DD: {dd_pct:.1f}%",
        f"  {profit_icon} Lucro: R${profit:+.2f}",
        f"",
        f"*🧠 Estratégia:*",
        f"  Setup: *{setup}*",
        f"  Ciclo: {cycle_str}",
        f"  Baixos: {baixos}",
        f"  🛡️ Safety: *{si:.2f}* ({level}){pause_str}",
        f"",
        f"*🎲 Apostas (sessão):*",
        f"  Hits: {hits} | Misses: {misses}",
        f"  Hit rate: {hit_rate:.1f}%",
        f"  Ciclos: {sequences} (W:{wins} / B:{breaks})",
        f"  Rounds: {rounds}",
        f"",
        f"*📡 Conexão:*",
        f"  {ws_icon} WebSocket",
    ]

    # Append DB stats if available
    if db_stats and not db_stats.get("error"):
        lines.extend([
            f"",
            f"*📊 DB (7 dias):*",
            f"  Rounds: {db_stats.get('total_rounds', 0)}",
            f"  Apostas: {db_stats.get('total_bets', 0)}",
            f"  Hit rate: {db_stats.get('hit_rate', 0.0):.1f}%",
            f"  Lucro: R${db_stats.get('profit', 0.0):+.2f}",
        ])

    return "\n".join(lines)


def _format_general_report() -> str:
    """Relatório geral de todas as plataformas."""
    if not _brain:
        return "⚫ Bot não conectado ao controlador"

    agg = _brain.get_aggregate_stats()

    total_profit = agg.get("total_profit", 0.0)
    total_hits = agg.get("total_hits", 0)
    total_misses = agg.get("total_misses", 0)
    total_rounds = agg.get("total_rounds", 0)
    total_saldo = agg.get("total_saldo", 0.0)
    hit_rate = agg.get("hit_rate", 0.0)
    running = agg.get("platforms_running", 0)
    total_plat = agg.get("platforms_total", 0)
    statuses = agg.get("platforms_status", {})

    profit_icon = "📈" if total_profit >= 0 else "📉"

    lines = [
        f"📋 *RELATÓRIO GERAL*",
        f"━━━━━━━━━━━━━━━━━━━━━━━",
        f"🖥️ Plataformas: {running}/{total_plat} ativas",
        f"",
    ]

    # Status de cada plataforma
    for name, status in statuses.items():
        icon = "🟢" if status == "running" else "🟡" if status == "connecting" else "⚫"
        lines.append(f"  {icon} {name.capitalize()}: {status}")

    lines.extend([
        f"",
        f"*💰 Consolidado:*",
        f"  Saldo total: R${total_saldo:.2f}",
        f"  {profit_icon} Lucro total: R${total_profit:+.2f}",
        f"  Rounds: {total_rounds}",
        f"  Hits: {total_hits} | Misses: {total_misses}",
        f"  Hit rate: {hit_rate:.1f}%",
    ])

    # Cross-platform DB comparison
    try:
        first_session = next(iter(_brain.sessions.values()), None)
        if first_session:
            cross = first_session.db_manager.get_cross_platform_comparison(7)
            platforms_db = cross.get("platforms", {})
            if platforms_db:
                lines.extend([
                    f"",
                    f"*📊 Comparativo 7 dias (DB):*",
                ])
                for pname, pdata in platforms_db.items():
                    db_profit = pdata.get("profit", 0.0)
                    db_hr = pdata.get("hit_rate", 0.0)
                    db_rounds = pdata.get("total_rounds", 0)
                    p_icon = "📈" if db_profit >= 0 else "📉"
                    lines.append(
                        f"  {pname.capitalize()}: {p_icon} R${db_profit:+.2f} "
                        f"| HR: {db_hr:.0f}% | {db_rounds}r"
                    )
    except Exception as e:
        logger.debug(f"Erro cross-platform DB: {e}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _check_authorized(update: Update) -> bool:
    """Verifica se o chat é autorizado."""
    chat_id = str(update.effective_chat.id)
    if chat_id != _chat_id:
        logger.warning(f"Chat não autorizado: {chat_id}")
        return False
    return True
