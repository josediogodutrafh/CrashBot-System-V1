"""
CrashBot GUI - Main Application (Flet).

Entry point: main()
- Creates Flet page with dark gaming theme
- Shows config panel for initial setup
- Launches bot in background thread
- Async loop syncs BotState → panels every 750ms
"""

import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import flet as ft

from src.gui.state import get_state, reset_state
from src.gui.theme import BG_MAIN
from src.gui.panels import (
    header,
    financial,
    strategy,
    stats,
    history,
    controls,
    config,
)

# Build timestamp (set at import time)
BUILD_TIME = "2026-02-13 09:30"

logger = logging.getLogger(__name__)


def _setup_file_logging():
    """Configure logging to write to crashbot.log next to the .exe.

    Only logs src.* modules and this module - NOT flet internals.
    """
    try:
        # Determine log path: next to .exe or in project root
        if getattr(sys, "frozen", False):
            log_dir = Path(sys.executable).parent
        else:
            log_dir = Path(__file__).parent.parent.parent

        log_file = log_dir / "crashbot.log"

        file_handler = logging.FileHandler(
            str(log_file), mode="w", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        # Force flush after every log line (Windows ignores line_buffering on files)
        _original_emit = file_handler.emit
        def _flushing_emit(record, _orig=_original_emit, _fh=file_handler):
            _orig(record)
            _fh.flush()
        file_handler.emit = _flushing_emit
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

        # Only attach handler to "src" logger (not root!)
        # This prevents flet_transport, asyncio, websocket etc from flooding
        # All src.* loggers inherit from "src" via propagation
        src_logger = logging.getLogger("src")
        src_logger.setLevel(logging.DEBUG)
        src_logger.addHandler(file_handler)

        # Also ensure this module (src.gui.app) doesn't duplicate
        # (it's a child of "src" so propagation handles it)

        # Also add a console handler for critical errors
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        logging.getLogger("src").addHandler(console)

        logger.info(f"=== CrashBot started (build {BUILD_TIME}) ===")
        logger.info(f"Log file: {log_file}")
        logger.info(f"Python: {sys.version}")
        logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    except Exception as e:
        print(f"Warning: could not setup file logging: {e}")

# Global reference to bot controller
_bot_controller = None
_bot_thread = None
_page_ref = None


# =============================================================================
# BOT BRIDGE - connects BotController to BotState
# =============================================================================

def _run_bot_in_background(config_dict: dict):
    """Run the bot controller in a background thread.

    CRITICAL: Everything is inside try/except so import errors
    don't kill the thread silently.
    """
    global _bot_controller
    state = get_state()

    try:
        logger.info("Bot thread: importing modules...")
        state.update("last_action", "Importando modulos...")

        from src.gui.app_mode import get_setup
        from src.bot.controller import BotController

        logger.info("Bot thread: imports OK, creating BotController...")
        state.update("last_action", "Inicializando bot...")

        setup = get_setup(config_dict["setup_name"])
        logger.info(f"Bot thread: setup={config_dict['setup_name']}")

        _bot_controller = BotController(
            caixa=config_dict["caixa"],
            banca_inicial=config_dict["banca"],
            setup=setup,
            meta_pct=config_dict["stop_gain_pct"],
            stop_loss_pct=config_dict["stop_loss_pct"],
            session_hours=config_dict["session_hours"],
            gain_action=config_dict["gain_action"],
            gain_suspend_hours=config_dict["gain_suspend_hours"],
            gain_reinvest_pct=config_dict["gain_reinvest_pct"],
            loss_action=config_dict["loss_action"],
            loss_suspend_hours=config_dict["loss_suspend_hours"],
            premium_only=config_dict["premium_only"],
            headless=True,
            profile_name=config_dict.get("profile_name", ""),
        )

        logger.info("Bot thread: BotController created OK")
        _bot_controller._gui_state = state
        state.update("phase", "running")
        state.update("running", True)
        state.update("session_start", datetime.now().timestamp())

        logger.info("Bot thread: calling start()...")
        _bot_controller.start()
        logger.info("Bot thread: start() returned")

    except Exception as e:
        logger.error(f"Bot thread EXCEPTION: {e}", exc_info=True)
        state.update("last_action", f"ERRO: {e}")
    finally:
        # Final sync so last_action error is visible
        if _bot_controller:
            try:
                state.update("last_action", _bot_controller.last_action)
                logger.info(f"Bot thread final last_action: {_bot_controller.last_action}")
            except Exception:
                pass
        state.update("running", False)
        state.update("phase", "stopped")
        logger.info("Bot thread: finished")


def _sync_state_from_bot():
    """Read bot controller state and push to BotState."""
    bot = _bot_controller
    if bot is None:
        return

    state = get_state()

    # Always sync last_action (even during connection phases)
    try:
        state.update("last_action", bot.last_action)
    except Exception:
        pass

    try:
        # Financial
        with bot.balance_lock:
            saldo = bot.current_balance or 0.0

        state.update_many({
            "caixa": bot.bankroll.caixa,
            "banca": bot.bankroll.banca,
            "n_bancas": bot.bankroll.n_bancas,
            "saldo": saldo,
            "session_profit": bot.session_profit,
            "session_hits": bot.session_hits,
            "session_misses": bot.session_misses,
            "round_count": bot.round_count,
            "session_hours": bot.session_hours,
        })

        # Stop gain / loss
        state.update_many({
            "stop_gain_pct": bot.bankroll.meta_percent,
            "stop_loss_pct": bot.bankroll.stop_loss_percent,
            "stop_gain_value": bot.bankroll.meta_value,
            "stop_loss_value": bot.bankroll.stop_loss_value,
            "meta_progress": bot.bankroll.get_meta_progress(),
            "meta_reached": bot.bankroll.check_meta_reached(),
        })

        # Strategy
        analysis = bot.strategy.get_current_analysis()
        from src.gui.app_mode import get_display_name
        setup_raw = analysis.get("setup_name", "N/A")

        # Parse "X/Y" format (e.g. "3/6")
        baixos_raw = analysis.get("baixos_consecutivos", "0/6")
        if isinstance(baixos_raw, str) and "/" in baixos_raw:
            parts = baixos_raw.split("/")
            baixos_val = int(parts[0])
            baixos_trigger = int(parts[1])
        else:
            baixos_val = int(baixos_raw) if baixos_raw else 0
            baixos_trigger = 6

        state.update_many({
            "setup_name": setup_raw,
            "setup_display": get_display_name(setup_raw),
            "baixos_consecutivos": baixos_val,
            "baixos_trigger": baixos_trigger,
            "baixos_display": str(baixos_raw),
            "martingale_active": analysis.get("martingale_active", False),
            "dobra_atual": analysis.get("dobra_atual", 0),
            "max_dobras": analysis.get("max_dobras", 0),
            "n_cycles": analysis.get("n_cycles", 1),
            "cycle_info": analysis.get("cycle_info"),
            "bets_by_cycle": analysis.get("bets_by_cycle", []),
            "pending_swap": analysis.get("pending_swap"),
            "total_sequences": analysis.get("total_sequences", 0),
            "total_wins": analysis.get("total_wins", 0),
            "total_breaks": analysis.get("total_breaks", 0),
            "total_profit": analysis.get("total_profit", 0.0),
            "wins_by_dobra": analysis.get("wins_by_dobra", {}),
        })

        # WS stats
        ws_stats = bot.ws_capture.get_stats()
        state.update_many({
            "ws_connected": bot.ws_capture.is_connected(),
            "ws_phase": bot.ws_capture.get_game_phase(),
            "ws_frames": ws_stats.get("frames_received", 0),
            "ws_rounds": ws_stats.get("rounds_captured", 0),
            "ws_errors": ws_stats.get("errors", 0),
            "ws_uptime": ws_stats.get("uptime_seconds", 0),
            "ws_last_frame": ws_stats.get("last_frame_time", 0),
        })

        # History
        hist = list(bot.strategy.explosion_history) if bot.strategy.explosion_history else []
        state.update("explosion_history", hist)

        # Misc
        state.update("last_action", bot.last_action)
        state.update("paused", bot.paused)
        # Only sync 'running' when bot has actually set it to True.
        # During connection phases (FASE 1/2/3), bot.running is still False
        # but we must NOT overwrite state["running"] = True (set by _on_config_start)
        # because _is_gui_stop_requested() reads it to detect user Stop clicks.
        if bot.running:
            state.update("running", True)

        # Premium
        premium_info = bot.schedule.get_current_info()
        if premium_info.get("is_premium"):
            prem = "PREMIUM+" if premium_info.get("strength") == "strong" else "PREMIUM"
        else:
            prem = "REGULAR"
        state.update("premium_status", prem)

        today_hours = bot.schedule.get_hours_for_today()
        state.update("premium_hours_today", today_hours or [])

        # Loss progress
        loss_current = max(0, bot.bankroll.bankroll_base - bot.bankroll.current_bankroll)
        loss_progress = (
            (loss_current / bot.bankroll.stop_loss_value)
            if bot.bankroll.stop_loss_value > 0 else 0
        )
        state.update("loss_progress", loss_progress)

    except Exception as e:
        logger.debug(f"State sync error: {e}")


# =============================================================================
# CALLBACKS
# =============================================================================

def _on_config_start(config_dict: dict):
    """Called when user clicks 'Iniciar Bot' on config panel."""
    global _bot_thread
    logger.info("=== INICIAR BOT clicado ===")
    logger.info(f"Config: caixa={config_dict.get('caixa')}, "
                f"banca={config_dict.get('banca')}, "
                f"setup={config_dict.get('setup_name')}")

    page = _page_ref
    if page is None:
        logger.error("_on_config_start: page is None!")
        return

    # Switch views
    config.hide(page)
    _show_dashboard(page)
    logger.info("Dashboard view created")

    # Reset state then push config values immediately (main thread)
    reset_state()
    state = get_state()
    state.update_many({
        "caixa": config_dict["caixa"],
        "banca": config_dict["banca"],
        "saldo": config_dict["banca"],
        "stop_gain_pct": config_dict["stop_gain_pct"],
        "stop_loss_pct": config_dict["stop_loss_pct"],
        "stop_gain_value": config_dict["caixa"] * config_dict["stop_gain_pct"] / 100,
        "stop_loss_value": config_dict["caixa"] * config_dict["stop_loss_pct"] / 100,
        "setup_display": config_dict["setup_name"],
        "phase": "connecting",
        "last_action": "Conectando ao Chrome DevTools...",
    })

    # Launch bot in background thread
    _bot_thread = threading.Thread(
        target=_run_bot_in_background,
        args=(config_dict,),
        daemon=True,
        name="bot-main",
    )
    _bot_thread.start()
    logger.info("Bot thread launched (daemon)")

    # Start async update loop
    page.run_task(_update_loop)
    logger.info("Update loop started")


def _on_setup_change(setup_name: str):
    bot = _bot_controller
    if bot and bot.running:
        bot._on_setup_change(setup_name)


def _on_meta_cycle():
    bot = _bot_controller
    if bot and bot.running:
        bot._on_meta_cycle()


def _on_pause():
    bot = _bot_controller
    if bot and bot.running:
        bot._on_pause()


def _on_stop():
    bot = _bot_controller
    if bot:
        bot._on_stop()


# =============================================================================
# ASYNC UPDATE LOOP
# =============================================================================

async def _update_loop():
    """Async loop: syncs BotState → panels every 750ms.

    NEVER exits - keeps running even after bot stops so the user
    can always see the clock, status messages and error details.
    """
    page = _page_ref
    stopped_renders = 0

    while True:
        state = get_state()
        phase = state.get("phase")
        if phase in ("running", "connecting"):
            _sync_state_from_bot()

        snap = state.snapshot()

        for panel in (header, financial, strategy, stats, history, controls):
            try:
                panel.update(snap)
            except Exception as e:
                logger.debug(f"Render error in {panel.__name__}: {e}")

        try:
            page.update()
        except Exception:
            break

        # After bot stops, slow down updates but KEEP RUNNING
        # (so the user can see the error message in the header)
        if phase == "stopped":
            stopped_renders += 1
            # First few renders: fast (show error quickly)
            if stopped_renders <= 3:
                await asyncio.sleep(0.5)
            else:
                # Then slow down to 2s (just keep clock ticking)
                await asyncio.sleep(2.0)
        else:
            stopped_renders = 0
            await asyncio.sleep(0.75)


# =============================================================================
# VIEW MANAGEMENT
# =============================================================================

_dashboard_view = None


def _create_dashboard() -> ft.Column:
    """Create the dashboard layout with all panels."""
    return ft.Column([
        header.create(),
        ft.ResponsiveRow([
            ft.Column([
                financial.create(),
                history.create(),
            ], col={"xs": 12, "md": 6}, spacing=8),
            ft.Column([
                strategy.create(),
                stats.create(),
            ], col={"xs": 12, "md": 6}, spacing=8),
        ], spacing=8),
        controls.create(),
    ], spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)


def _show_dashboard(page: ft.Page):
    """Show the dashboard view."""
    global _dashboard_view
    _dashboard_view = _create_dashboard()
    page.add(_dashboard_view)


# =============================================================================
# MAIN
# =============================================================================

def _thread_excepthook(args):
    """Catch uncaught exceptions in ANY thread and log them."""
    logger.error(
        f"UNCAUGHT THREAD EXCEPTION in '{args.thread.name}': "
        f"{args.exc_type.__name__}: {args.exc_value}",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
    # Also push to state so user sees it in the UI
    try:
        state = get_state()
        state.update("last_action", f"ERRO FATAL: {args.exc_value}")
        state.update("phase", "stopped")
    except Exception:
        pass


def _flet_main(page: ft.Page):
    """Flet page setup."""
    global _page_ref
    _page_ref = page

    # Page configuration
    from src.gui.app_mode import get_title
    page.title = f"{get_title()} (build {BUILD_TIME})"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_MAIN
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 1024
    page.window.min_height = 600
    page.padding = ft.padding.all(12)

    # Try to set icon
    try:
        icon_path = Path(__file__).parent.parent.parent / "tools" / "icone.ico"
        if icon_path.exists():
            page.window.icon = str(icon_path)
    except Exception:
        pass

    # Setup logging (file only for src.* modules, no flet spam)
    _setup_file_logging()

    # Catch uncaught thread exceptions (e.g. import errors in bot thread)
    threading.excepthook = _thread_excepthook

    # Set callbacks
    config.set_on_start(_on_config_start)
    controls.set_callbacks(
        on_setup_change=_on_setup_change,
        on_meta_cycle=_on_meta_cycle,
        on_pause=_on_pause,
        on_stop=_on_stop,
    )

    # Show config view first
    config_view = config.create()
    page.add(config_view)
    page.update()


def main():
    """Entry point - called from run.py."""
    ft.app(target=_flet_main)


if __name__ == "__main__":
    main()
