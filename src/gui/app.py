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

logger = logging.getLogger(__name__)

# Global reference to bot controller
_bot_controller = None
_bot_thread = None
_page_ref = None


# =============================================================================
# BOT BRIDGE - connects BotController to BotState
# =============================================================================

def _run_bot_in_background(config_dict: dict):
    """Run the bot controller in a background thread."""
    global _bot_controller

    from src.bot.setups import get_setup
    from src.bot.controller import BotController

    state = get_state()
    state.update("phase", "connecting")
    state.update("last_action", "Conectando ao Chrome DevTools...")

    try:
        setup = get_setup(config_dict["setup_name"])

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
        )

        _bot_controller._gui_state = state
        state.update("phase", "running")
        state.update("running", True)
        state.update("session_start", datetime.now().timestamp())

        _bot_controller.start()

    except Exception as e:
        logger.error(f"Bot error: {e}")
        state.update("last_action", f"ERRO: {e}")
        state.update("phase", "stopped")
    finally:
        state.update("running", False)
        state.update("phase", "stopped")


def _sync_state_from_bot():
    """Read bot controller state and push to BotState."""
    bot = _bot_controller
    if bot is None:
        return

    state = get_state()

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
        from src.bot.setups import get_display_name
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
        state.update("running", bot.running)

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
    page = _page_ref
    if page is None:
        return

    # Switch views
    config.hide(page)
    _show_dashboard(page)

    # Reset state
    reset_state()

    # Launch bot in background thread
    _bot_thread = threading.Thread(
        target=_run_bot_in_background,
        args=(config_dict,),
        daemon=True,
        name="bot-main",
    )
    _bot_thread.start()

    # Start async update loop
    page.run_task(_update_loop)


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
    """Async loop: syncs BotState → panels every 750ms."""
    page = _page_ref
    while True:
        state = get_state()
        if state.get("phase") in ("running", "connecting"):
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

def _flet_main(page: ft.Page):
    """Flet page setup."""
    global _page_ref
    _page_ref = page

    # Page configuration
    page.title = "CrashBot v3.0 - Crash Game Assistant"
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

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("src.ws").setLevel(logging.WARNING)
    logging.getLogger("src.data").setLevel(logging.WARNING)

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
