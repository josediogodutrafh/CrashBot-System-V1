"""
CrashBot GUI - Multi-Platform Mode.

Dashboard for 4 platforms simultaneously.
- Tab-based view: one tab per platform
- Aggregate sidebar with totals
- Independent start/stop per platform

Entry point: main()
"""

import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import flet as ft

from src.gui.theme import (
    BG_MAIN, BG_CARD, BG_HEADER, BG_INPUT,
    NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW, NEON_PURPLE, NEON_CYAN,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container, section_title, neon_button, stat_row,
    get_explosion_color, CARD_SHADOW,
)

BUILD_TIME = "2026-02-19 Lab"
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# GLOBALS
# ═══════════════════════════════════════════════════════════════════════

_brain = None           # MultiPlatformController
_brain_thread = None
_page_ref = None

# Per-platform Flet controls (keyed by platform name)
_platform_controls: Dict[str, Dict[str, ft.Control]] = {}
_aggregate_controls: Dict[str, ft.Control] = {}
_active_platform: str = ""


# ═══════════════════════════════════════════════════════════════════════
# PLATFORM PANEL (per-platform dashboard)
# ═══════════════════════════════════════════════════════════════════════

def _create_platform_panel(name: str) -> ft.Column:
    """Create a dashboard panel for one platform."""
    ctrls = {}

    # Status
    ctrls["status"] = ft.Text("idle", size=12, color=TEXT_SECONDARY)
    ctrls["last_action"] = ft.Text("--", size=11, color=TEXT_DIM, max_lines=2)

    # Financial
    ctrls["saldo"] = ft.Text("R$ 0.00", size=22, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    ctrls["profit"] = ft.Text("+R$ 0.00", size=16, color=NEON_GREEN)
    ctrls["caixa"] = ft.Text("Banca: aguardando...", size=11, color=TEXT_DIM)
    ctrls["banca"] = ft.Text("Banca: R$ 0", size=11, color=TEXT_SECONDARY)

    # Stats
    ctrls["hits"] = ft.Text("0", size=14, color=NEON_GREEN)
    ctrls["misses"] = ft.Text("0", size=14, color=NEON_RED)
    ctrls["rounds"] = ft.Text("0", size=14, color=TEXT_PRIMARY)

    # Strategy
    ctrls["setup"] = ft.Text("--", size=12, color=NEON_BLUE)
    ctrls["dobra"] = ft.Text("--", size=11, color=TEXT_SECONDARY)
    ctrls["baixos"] = ft.Text("0", size=11, color=TEXT_SECONDARY)
    ctrls["next_bet"] = ft.Text("--", size=14, weight=ft.FontWeight.BOLD, color=NEON_YELLOW)

    # Advisor / Safety Index
    ctrls["safety_bar"] = ft.ProgressBar(value=0.5, width=180, bar_height=8, color=NEON_BLUE, bgcolor=BG_INPUT)
    ctrls["safety_label"] = ft.Text("Safety: 0.50 (NORMAL)", size=10, color=NEON_BLUE)
    ctrls["advisor_action"] = ft.Text("--", size=10, color=TEXT_DIM, max_lines=1)

    # WS
    ctrls["ws_status"] = ft.Icon(
        ft.Icons.CIRCLE, size=10, color=NEON_RED,
    )
    ctrls["ws_frames"] = ft.Text(
        "0 frames", size=10, color=TEXT_DIM,
    )

    # Calibrar button (no dashboard)
    def _on_calibrate_live(e):
        """Roda wizard de calibracao ao vivo."""
        import threading as _th
        if _brain and hasattr(_brain, "sessions"):
            session = _brain.sessions.get(name)
            if session:
                def _wizard():
                    ok = session.calibrate()
                    try:
                        if ok:
                            ctrls["cal_btn"].text = (
                                "Calibrado"
                            )
                            ctrls["cal_btn"].bgcolor = (
                                "#1a3a1a"
                            )
                            ctrls["cal_status"].value = (
                                "Pronto para apostar"
                            )
                            ctrls["cal_status"].color = (
                                NEON_GREEN
                            )
                        else:
                            ctrls["cal_status"].value = (
                                "Cancelado"
                            )
                            ctrls["cal_status"].color = (
                                NEON_RED
                            )
                        e.page.update()
                    except Exception:
                        pass
                _th.Thread(
                    target=_wizard, daemon=True,
                ).start()

    ctrls["cal_btn"] = ft.ElevatedButton(
        "Calibrar",
        icon=ft.Icons.CROP_FREE,
        bgcolor=BG_CARD, color=NEON_YELLOW,
        height=36,
        on_click=_on_calibrate_live,
    )
    ctrls["cal_status"] = ft.Text(
        "Modo observacao - Calibre para apostar",
        size=10, color=NEON_YELLOW,
    )

    # History
    ctrls["history"] = ft.Row(
        [], spacing=4, wrap=True,
    )

    # Trend Monitor (per-platform instance)
    from src.gui.panels.trend_panel import TrendPanel
    trend_instance = TrendPanel()
    ctrls["trend_instance"] = trend_instance
    ctrls["trend_container"] = trend_instance.create()

    _platform_controls[name] = ctrls

    # Layout
    financial_card = card_container(ft.Column([
        section_title("SALDO", ft.Icons.ACCOUNT_BALANCE_WALLET),
        ctrls["saldo"],
        ctrls["profit"],
        ft.Divider(height=1, color=TEXT_DIM),
        ctrls["caixa"],
        ctrls["banca"],
    ], spacing=6))

    stats_card = card_container(ft.Column([
        section_title("RESULTADOS", ft.Icons.ANALYTICS),
        ft.Row([
            ft.Column([ft.Text("Hits", size=10, color=TEXT_SECONDARY), ctrls["hits"]], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Column([ft.Text("Misses", size=10, color=TEXT_SECONDARY), ctrls["misses"]], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Column([ft.Text("Rounds", size=10, color=TEXT_SECONDARY), ctrls["rounds"]], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=30, alignment=ft.MainAxisAlignment.CENTER),
    ], spacing=8))

    strategy_card = card_container(ft.Column([
        section_title("STRATEGY", ft.Icons.PSYCHOLOGY),
        stat_row("Setup", ""),
        ctrls["setup"],
        ctrls["dobra"],
        stat_row("Baixos", ""),
        ctrls["baixos"],
        ft.Divider(height=1, color=TEXT_DIM),
        stat_row("Proxima aposta", ""),
        ctrls["next_bet"],
    ], spacing=4))


    ws_card = card_container(ft.Row([
        ctrls["ws_status"],
        ft.Text(
            f"WS {name}", size=11,
            color=TEXT_SECONDARY,
        ),
        ctrls["ws_frames"],
    ], spacing=8))

    cal_card = card_container(ft.Row([
        ctrls["cal_btn"],
        ctrls["cal_status"],
    ], spacing=12))

    history_card = card_container(ft.Column([
        section_title(
            "HISTORICO", ft.Icons.HISTORY,
        ),
        ctrls["history"],
    ], spacing=6))

    return ft.Column([
        ft.Row([
            ctrls["status"],
            ft.Text("|", color=TEXT_DIM),
            ctrls["last_action"],
        ], spacing=8),
        ws_card,
        cal_card,
        ft.ResponsiveRow([
            ft.Column(
                [financial_card],
                col=6, spacing=8,
            ),
            ft.Column(
                [stats_card, strategy_card],
                col=6, spacing=8,
            ),
        ], spacing=8),
        history_card,
        ctrls["trend_container"],
    ], spacing=8, scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def _update_platform_panel(name: str, state: dict):
    """Update a platform panel with new state."""
    ctrls = _platform_controls.get(name)
    if not ctrls:
        return

    status = state.get("status", "idle")
    status_colors = {
        "idle": TEXT_DIM, "connecting": NEON_YELLOW,
        "running": NEON_GREEN, "paused": NEON_YELLOW,
        "stopped": TEXT_DIM, "error": NEON_RED,
    }
    ctrls["status"].value = status.upper()
    ctrls["status"].color = status_colors.get(status, TEXT_DIM)

    ctrls["last_action"].value = state.get("last_action", "--")

    saldo = state.get("saldo", 0)
    ctrls["saldo"].value = f"R$ {saldo:,.2f}"

    profit = state.get("session_profit", 0)
    ctrls["profit"].value = f"{'+'if profit >= 0 else ''}R$ {profit:,.2f}"
    ctrls["profit"].color = NEON_GREEN if profit >= 0 else NEON_RED

    banca = state.get("banca", 0)
    if banca > 0:
        ctrls["caixa"].value = (
            f"Banca: R$ {banca:,.2f}"
        )
        ctrls["caixa"].color = TEXT_SECONDARY
    else:
        ctrls["caixa"].value = (
            "Banca: aguardando saldo..."
        )
        ctrls["caixa"].color = TEXT_DIM

    ctrls["hits"].value = str(state.get("session_hits", 0))
    ctrls["misses"].value = str(state.get("session_misses", 0))
    ctrls["rounds"].value = str(state.get("round_count", 0))

    ctrls["setup"].value = state.get("setup_name", "--")
    dobra = state.get("dobra_atual", 0)
    max_d = state.get("max_dobras", 0)
    active = state.get("martingale_active", False)
    ctrls["dobra"].value = f"Dobra {dobra}/{max_d}" if active else "Inativo"
    ctrls["baixos"].value = str(state.get("baixos_consecutivos", 0))

    next_bet = state.get("next_bet_value", 0)
    if next_bet > 0:
        ctrls["next_bet"].value = f"R$ {next_bet:,.2f}"
    else:
        ctrls["next_bet"].value = "--"

    ws_conn = state.get("ws_connected", False)
    ctrls["ws_status"].color = NEON_GREEN if ws_conn else NEON_RED
    ctrls["ws_frames"].value = f"{state.get('ws_frames', 0)} frames"

    # Calibration status update
    if _brain and hasattr(_brain, "sessions"):
        session = _brain.sessions.get(name)
        if session and session.betting.can_execute():
            ctrls["cal_btn"].text = "Calibrado"
            ctrls["cal_btn"].bgcolor = "#1a3a1a"
            ctrls["cal_status"].value = (
                "Pronto para apostar"
            )
            ctrls["cal_status"].color = NEON_GREEN

    # History chips
    history = state.get("explosion_history", [])[-15:]
    chips = []
    for v in reversed(history):
        color = get_explosion_color(v)
        chips.append(ft.Container(
            content=ft.Text(f"{v:.2f}x", size=9, color="white", weight=ft.FontWeight.BOLD),
            bgcolor=color, border_radius=4,
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
        ))
    ctrls["history"].controls = chips

    # Advisor / Safety Index
    advisor = state.get("advisor", {})
    if advisor:
        safety_val = advisor.get("safety_index", 0.5)
        safety_level = advisor.get("safety_level", "normal").upper()
        safety_color_name = advisor.get("safety_color", "blue")
        color_map = {"green": NEON_GREEN, "blue": NEON_BLUE, "yellow": NEON_YELLOW, "red": NEON_RED}
        sc = color_map.get(safety_color_name, NEON_BLUE)

        ctrls["safety_bar"].value = safety_val
        ctrls["safety_bar"].color = sc
        ctrls["safety_label"].value = f"Safety: {safety_val:.2f} ({safety_level})"
        ctrls["safety_label"].color = sc

        adv_setup = advisor.get("current_setup", "--")
        adv_compound = advisor.get("current_compound", 0)
        adv_swaps = advisor.get("total_swaps", 0)
        last_adv = advisor.get("last_action", "")
        if last_adv:
            ctrls["advisor_action"].value = last_adv[:80]
        else:
            ctrls["advisor_action"].value = f"Setup: {adv_setup} | Compound: {adv_compound:.0%} | Swaps: {adv_swaps}"

    # Trend Monitor
    trend_data = state.get("trend", {})
    trend_inst = ctrls.get("trend_instance")
    if trend_data and trend_inst:
        trend_inst.update(trend_data)


# ═══════════════════════════════════════════════════════════════════════
# AGGREGATE PANEL (sidebar)
# ═══════════════════════════════════════════════════════════════════════

def _create_aggregate_panel() -> ft.Container:
    """Create the aggregate stats sidebar."""
    ctrls = {}
    ctrls["total_saldo"] = ft.Text("R$ 0.00", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    ctrls["total_profit"] = ft.Text("+R$ 0.00", size=16, color=NEON_GREEN)
    ctrls["total_hits"] = ft.Text("0", size=13, color=NEON_GREEN)
    ctrls["total_misses"] = ft.Text("0", size=13, color=NEON_RED)
    ctrls["hit_rate"] = ft.Text("0%", size=13, color=TEXT_PRIMARY)
    ctrls["platforms_running"] = ft.Text("0/4", size=13, color=NEON_BLUE)
    ctrls["total_rounds"] = ft.Text("0", size=13, color=TEXT_PRIMARY)

    # Per-platform status dots
    ctrls["platform_dots"] = ft.Column([], spacing=4)

    _aggregate_controls.update(ctrls)

    # Weekly report badge
    ctrls["weekly_badge"] = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.ANALYTICS, size=12, color=NEON_YELLOW),
            ft.Text("Relatório semanal", size=10, color=NEON_YELLOW),
        ], spacing=4),
        visible=False,
        bgcolor=BG_INPUT,
        border=ft.border.all(1, NEON_YELLOW),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        on_click=lambda e: _show_weekly_report(e),
    )

    return card_container(ft.Column([
        ft.Text("AGREGADO", size=14, weight=ft.FontWeight.BOLD, color=NEON_CYAN),
        ctrls["weekly_badge"],
        ft.Divider(height=1, color=TEXT_DIM),
        ft.Text("Saldo Total", size=10, color=TEXT_SECONDARY),
        ctrls["total_saldo"],
        ctrls["total_profit"],
        ft.Divider(height=1, color=TEXT_DIM),
        stat_row("Hits", ""), ctrls["total_hits"],
        stat_row("Misses", ""), ctrls["total_misses"],
        stat_row("Taxa", ""), ctrls["hit_rate"],
        ft.Divider(height=1, color=TEXT_DIM),
        stat_row("Rounds", ""), ctrls["total_rounds"],
        stat_row("Ativas", ""), ctrls["platforms_running"],
        ft.Divider(height=1, color=TEXT_DIM),
        ctrls["platform_dots"],
    ], spacing=6), width=220)


def _update_aggregate(agg: dict, all_states: dict):
    """Update aggregate panel."""
    ctrls = _aggregate_controls
    if not ctrls:
        return

    total_saldo = agg.get("total_saldo", 0)
    ctrls["total_saldo"].value = f"R$ {total_saldo:,.2f}"

    profit = agg.get("total_profit", 0)
    ctrls["total_profit"].value = f"{'+'if profit >= 0 else ''}R$ {profit:,.2f}"
    ctrls["total_profit"].color = NEON_GREEN if profit >= 0 else NEON_RED

    ctrls["total_hits"].value = str(agg.get("total_hits", 0))
    ctrls["total_misses"].value = str(agg.get("total_misses", 0))
    ctrls["hit_rate"].value = f"{agg.get('hit_rate', 0):.1f}%"
    ctrls["total_rounds"].value = str(agg.get("total_rounds", 0))

    running = agg.get("platforms_running", 0)
    total = agg.get("platforms_total", 0)
    ctrls["platforms_running"].value = f"{running}/{total}"

    # Platform status dots
    dots = []
    status_colors = {
        "idle": TEXT_DIM, "connecting": NEON_YELLOW,
        "running": NEON_GREEN, "paused": NEON_YELLOW,
        "stopped": TEXT_DIM, "error": NEON_RED,
    }
    for name, state in all_states.items():
        st = state.get("status", "idle")
        color = status_colors.get(st, TEXT_DIM)
        dots.append(ft.Row([
            ft.Icon(ft.Icons.CIRCLE, size=8, color=color),
            ft.Text(name, size=10, color=TEXT_SECONDARY),
            ft.Text(st, size=9, color=color),
        ], spacing=4))
    ctrls["platform_dots"].controls = dots


# ═══════════════════════════════════════════════════════════════════════
# CONFIG PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════

import json as _json

def _load_saved_config() -> Dict:
    """Load saved platform configs from multi_platforms.json."""
    from src.config import MULTI_CONFIG_PATH
    try:
        if MULTI_CONFIG_PATH.exists():
            with open(MULTI_CONFIG_PATH, "r", encoding="utf-8") as f:
                return _json.load(f)
    except Exception as e:
        logger.warning(f"Erro ao carregar config salva: {e}")
    return {}


def _save_config(platform_names: List[str], platform_fields: Dict):
    """Save current platform configs to multi_platforms.json."""
    from src.config import MULTI_CONFIG_PATH
    data = {}
    for name in platform_names:
        fields = platform_fields.get(name, {})
        profile_dd = fields.get("profile_dropdown")
        profile_val = ""
        if profile_dd and profile_dd.value != "(sem calibracao)":
            profile_val = profile_dd.value or ""

        modo_dd = fields.get("modo")
        modo_val = "moderado"
        if modo_dd and modo_dd.value:
            modo_val = modo_dd.value

        data[name] = {
            "enabled": fields.get(
                "enabled", ft.Checkbox()
            ).value,
            "game_url": fields.get(
                "game_url", ft.TextField()
            ).value or "",
            "banca": fields.get(
                "banca", ft.TextField()
            ).value or "250",
            "modo": modo_val,
            "recording": False,
            "profile": profile_val,
            "advisor_enabled": False,
        }
    try:
        with open(MULTI_CONFIG_PATH, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Config salva em {MULTI_CONFIG_PATH}")
    except Exception as e:
        logger.warning(f"Erro ao salvar config: {e}")


# ═══════════════════════════════════════════════════════════════════════
# CONFIG PANEL (multi-platform)
# ═══════════════════════════════════════════════════════════════════════

_config_on_start = None

def _create_multi_config(platform_names: List[str]) -> ft.Container:
    """Create config panel for multiple platforms."""
    global _config_on_start

    saved = _load_saved_config()
    platform_fields = {}

    # Load existing calibration profiles
    from src.bot.calibration import get_profile_names, get_profile, validate_profile

    def _build_platform_config(name: str, page_ref=None) -> ft.Container:
        s = saved.get(name, {})
        existing_profiles = get_profile_names()
        saved_profile = s.get("profile", "")
        fields = {}

        fields["enabled"] = ft.Checkbox(
            label=f"Ativar {name}", value=s.get("enabled", True),
        )
        fields["game_url"] = ft.TextField(
            label="URL do jogo", hint_text="https://...",
            value=s.get("game_url", ""),
            bgcolor=BG_INPUT, border_color=TEXT_DIM,
            text_size=12, height=45,
        )
        fields["banca"] = ft.TextField(
            label="Banca (R$)",
            value=str(s.get("banca", "250")),
            bgcolor=BG_INPUT,
            border_color=TEXT_DIM,
            text_size=12, height=45, width=160,
        )
        fields["modo"] = ft.Dropdown(
            label="Modo",
            options=[
                ft.dropdown.Option(
                    "agressivo",
                    "Agressivo (1/2)",
                ),
                ft.dropdown.Option(
                    "moderado",
                    "Moderado (1/2/4)",
                ),
                ft.dropdown.Option(
                    "conservador",
                    "Conservador (1/2/4/8)",
                ),
            ],
            value=s.get("modo", "moderado"),
            bgcolor=BG_INPUT,
            border_color=TEXT_DIM,
            text_size=12, height=50, width=220,
        )

        # Compat (desativados)
        fields["advisor_enabled"] = ft.Checkbox(
            label="", value=False, visible=False,
        )
        fields["recording"] = ft.Checkbox(
            label="", value=False, visible=False,
        )

        # Calibration profile dropdown
        profile_options = [ft.dropdown.Option("(sem calibracao)")] + [
            ft.dropdown.Option(p) for p in existing_profiles
        ]
        fields["profile_dropdown"] = ft.Dropdown(
            label="Perfil de calibracao",
            options=profile_options,
            value=saved_profile if saved_profile in existing_profiles else "(sem calibracao)",
            bgcolor=BG_INPUT, border_color=TEXT_DIM,
            text_size=12, height=50, width=220,
        )

        # Calibration status text
        profile_status = ft.Text("", size=10, color=TEXT_DIM)
        fields["profile_status"] = profile_status

        def _update_profile_status():
            sel = fields["profile_dropdown"].value
            if sel and sel != "(sem calibracao)":
                prof = get_profile(sel)
                if prof and validate_profile(prof):
                    a1 = prof.get("bet_value_area_1", {})
                    a2 = prof.get("target_area_1", {})
                    a3 = prof.get("bet_button_area_1", {})
                    profile_status.value = (
                        f"Valor({a1.get('x')},{a1.get('y')}) "
                        f"Alvo({a2.get('x')},{a2.get('y')}) "
                        f"Botao({a3.get('x')},{a3.get('y')})"
                    )
                    profile_status.color = NEON_GREEN
                else:
                    profile_status.value = "Perfil invalido"
                    profile_status.color = NEON_RED
            else:
                profile_status.value = "Modo observacao (sem apostas)"
                profile_status.color = NEON_YELLOW

        _update_profile_status()

        def _on_profile_change(e):
            _update_profile_status()
            e.page.update()

        fields["profile_dropdown"].on_change = _on_profile_change

        # Calibrate button — opens Tkinter wizard
        def _on_calibrate(e):
            from src.bot.calibration import run_calibration_wizard, save_profile
            profile_name = f"{name}_calibration"
            # Run wizard in separate thread to not block Flet
            def _wizard():
                result = run_calibration_wizard(profile_name)
                if result:
                    save_profile(profile_name, result)
                    # Update dropdown options
                    new_profiles = get_profile_names()
                    fields["profile_dropdown"].options = (
                        [ft.dropdown.Option("(sem calibracao)")] +
                        [ft.dropdown.Option(p) for p in new_profiles]
                    )
                    fields["profile_dropdown"].value = profile_name
                    _update_profile_status()
                    try:
                        e.page.update()
                    except Exception:
                        pass
            threading.Thread(target=_wizard, daemon=True).start()

        calibrate_btn = ft.ElevatedButton(
            "Calibrar",
            icon=ft.Icons.CROP_FREE,
            bgcolor=BG_CARD, color=NEON_BLUE,
            height=40,
            on_click=_on_calibrate,
        )

        platform_fields[name] = fields

        return card_container(ft.Column([
            fields["enabled"],
            fields["game_url"],
            ft.Row([
                fields["banca"],
                fields["modo"],
            ], spacing=12),
        ], spacing=6), padding=12)

    platform_configs = ft.Column([
        _build_platform_config(name) for name in platform_names
    ], spacing=8, scroll=ft.ScrollMode.AUTO)

    def _on_start(e):
        # Save config before starting
        _save_config(platform_names, platform_fields)

        configs = []
        from src.bot.platform_session import PlatformConfig
        from src.bot.setups import get_setup
        from src.config import PLATFORM_PORTS
        ports = PLATFORM_PORTS

        for name in platform_names:
            fields = platform_fields.get(name, {})
            enabled = fields.get("enabled")
            if enabled and not enabled.value:
                continue

            try:
                banca = float(
                    fields["banca"].value or "250"
                )
            except ValueError:
                banca = 250

            # Modo escolhido pelo usuario
            modo_dd = fields.get("modo")
            modo = "moderado"
            if modo_dd and modo_dd.value:
                modo = modo_dd.value
            setup = get_setup(modo)

            # Profile da calibracao feita na config
            profile_name = f"{name}_cal"

            # Advisor
            advisor_val = fields.get("advisor_enabled", ft.Checkbox()).value

            configs.append(PlatformConfig(
                platform_name=name,
                port=ports.get(name, 9222 + len(configs)),
                game_url=fields["game_url"].value or "",
                banca=banca,
                setup=setup,
                meta_pct=20.0,
                stop_loss_pct=50.0,
                recording=fields.get("recording", ft.Checkbox()).value,
                profile_name=profile_name,
                enabled=True,
                advisor_enabled=advisor_val if advisor_val is not None else True,
            ))

        if _config_on_start and configs:
            _config_on_start(configs)

    start_btn = neon_button(
        "INICIAR",
        icon=ft.Icons.PLAY_ARROW,
        color=NEON_GREEN,
        on_click=_on_start,
        width=250, height=48,
    )

    return ft.Container(
        content=ft.Column([
            ft.Text(
                "CRASH LAB - MULTI-PLATAFORMA",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=NEON_CYAN,
            ),
            ft.Divider(height=1, color=TEXT_DIM),
            platform_configs,
            ft.Row(
                [start_btn],
                alignment=(
                    ft.MainAxisAlignment.CENTER
                ),
            ),
        ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
        ),
        padding=20, expand=True,
    )


# ═══════════════════════════════════════════════════════════════════════
# DASHBOARD (tabs + aggregate)
# ═══════════════════════════════════════════════════════════════════════

_tab_buttons: Dict[str, ft.Container] = {}
_platform_panels: Dict[str, ft.Control] = {}
_content_area = None

def _create_tab_bar(platform_names: List[str]) -> ft.Row:
    """Create a custom tab bar with styled buttons (replaces broken ft.Tabs)."""
    def _select_tab(name: str):
        global _active_platform
        _active_platform = name
        # Update button styles
        for btn_name, btn in _tab_buttons.items():
            is_active = (btn_name == name)
            btn.bgcolor = NEON_CYAN if is_active else BG_CARD
            btn.border = ft.border.only(
                bottom=ft.BorderSide(2, NEON_CYAN) if is_active else ft.BorderSide(0),
            )
            btn.content.color = BG_MAIN if is_active else TEXT_SECONDARY
            btn.content.weight = ft.FontWeight.BOLD if is_active else None
        # Toggle panel visibility
        for pname, panel in _platform_panels.items():
            panel.visible = (pname == name)

    buttons = []
    for i, name in enumerate(platform_names):
        is_first = (i == 0)
        label = ft.Text(
            name.upper(), size=13,
            color=BG_MAIN if is_first else TEXT_SECONDARY,
            weight=ft.FontWeight.BOLD if is_first else None,
        )
        btn = ft.Container(
            content=label,
            bgcolor=NEON_CYAN if is_first else BG_CARD,
            border=ft.border.only(
                bottom=ft.BorderSide(2, NEON_CYAN) if is_first else ft.BorderSide(0),
            ),
            border_radius=ft.border_radius.only(top_left=8, top_right=8),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            on_click=lambda e, n=name: (_select_tab(n), e.page.update()),
            ink=True,
        )
        _tab_buttons[name] = btn
        buttons.append(btn)

    return ft.Row(buttons, spacing=2)


def _create_dashboard(platform_names: List[str]) -> ft.Row:
    """Create multi-platform dashboard with tab selector + content + aggregate."""
    global _active_platform, _content_area

    # Create panels per platform (only first is visible)
    for i, name in enumerate(platform_names):
        panel = _create_platform_panel(name)
        panel.visible = (i == 0)
        _platform_panels[name] = panel

    if platform_names:
        _active_platform = platform_names[0]

    # Content area holds all panels (visibility toggled)
    _content_area = ft.Column(
        list(_platform_panels.values()),
        expand=True, spacing=0,
    )

    # Custom tab bar (no ft.Tabs — works on all Flet versions)
    tab_bar = _create_tab_bar(platform_names)

    aggregate = _create_aggregate_panel()

    # Stop all button
    def _stop_all(e):
        if _brain:
            _brain.stop_all()
            # Parar Telegram bot
            try:
                from src.notifications.telegram_bot import stop_bot as stop_tg_bot
                stop_tg_bot()
            except Exception:
                pass

    stop_btn = neon_button(
        "PARAR TUDO", icon=ft.Icons.STOP,
        color=NEON_RED, on_click=_stop_all, width=200,
    )

    left = ft.Column([
        ft.Row([
            ft.Text("CRASH LAB - MULTI-PLATAFORMA",
                     size=16, weight=ft.FontWeight.BOLD, color=NEON_CYAN),
            stop_btn,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        tab_bar,
        _content_area,
    ], spacing=8, expand=True)

    return ft.Row([left, aggregate], spacing=12, expand=True)


# ═══════════════════════════════════════════════════════════════════════
# UPDATE LOOP
# ═══════════════════════════════════════════════════════════════════════

def _show_weekly_report(e):
    """Show weekly report in a dialog."""
    try:
        from src.analysis.weekly_report import WeeklyReport
        report = WeeklyReport(None)
        data = report.get_latest_report()
        if data:
            summary_text = ""
            agg = data.get("aggregate", {})
            summary_text += f"Rounds: {agg.get('total_rounds', 0)}\n"
            summary_text += f"Apostas: {agg.get('total_bets', 0)}\n"
            summary_text += f"Hit rate: {agg.get('hit_rate', 0):.1f}%\n"
            summary_text += f"Lucro: R${agg.get('total_profit', 0):+.2f}\n\n"

            for name, stats in data.get("per_platform", {}).items():
                rounds = stats.get("total_rounds", 0)
                pct_low = stats.get("pct_low", 0)
                profit = stats.get("profit", 0)
                summary_text += f"{name}: {rounds}r | %LOW={pct_low:.1f}% | R${profit:+.2f}\n"

            for alert in data.get("drift_alerts", []):
                summary_text += f"\n⚠ {alert['message']}"

            dlg = ft.AlertDialog(
                title=ft.Text("Relatório Semanal", color=NEON_CYAN),
                content=ft.Text(summary_text, size=12, color=TEXT_PRIMARY),
            )
            e.page.overlay.append(dlg)
            dlg.open = True
            e.page.update()
    except Exception as ex:
        logger.debug(f"Erro ao mostrar relatório: {ex}")


async def _update_loop():
    """Async loop: sync brain state → panels every 750ms."""
    page = _page_ref

    while True:
        if _brain:
            try:
                all_states = _brain.get_all_states()
                agg = _brain.get_aggregate_stats()

                for name, state in all_states.items():
                    _update_platform_panel(name, state)

                _update_aggregate(agg, all_states)

                # Weekly report badge
                if hasattr(_brain, '_weekly_report_pending') and _brain._weekly_report_pending:
                    badge = _aggregate_controls.get("weekly_badge")
                    if badge:
                        badge.visible = True
            except Exception as e:
                logger.debug(f"Update loop error: {e}")

        try:
            page.update()
        except Exception:
            break

        await asyncio.sleep(0.75)


# ═══════════════════════════════════════════════════════════════════════
# BRAIN LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════

def _start_brain(configs):
    """Called when user clicks Iniciar on config panel."""
    global _brain, _brain_thread

    page = _page_ref
    if not page:
        return

    from src.bot.multi_controller import MultiPlatformController

    _brain = MultiPlatformController(configs)

    # Iniciar Telegram bot interativo (se configurado)
    try:
        from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        from src.notifications.telegram_bot import start_bot as start_tg_bot
        start_tg_bot(_brain, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    except Exception as ex:
        import logging
        logging.getLogger(__name__).debug(f"Telegram bot não iniciado: {ex}")

    # Switch to dashboard
    page.clean()
    platform_names = _brain.platform_names
    dashboard = _create_dashboard(platform_names)
    page.add(dashboard)
    page.update()

    # Start brain in background
    _brain_thread = threading.Thread(
        target=_brain.start_all, daemon=True, name="brain-main",
    )
    _brain_thread.start()

    # Start update loop
    page.run_task(_update_loop)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def _setup_file_logging():
    """Configure logging."""
    try:
        if getattr(sys, "frozen", False):
            log_dir = Path(sys.executable).parent
        else:
            log_dir = Path(__file__).parent.parent.parent
        log_file = log_dir / "crashbot_multi.log"

        file_handler = logging.FileHandler(str(log_file), mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        _original_emit = file_handler.emit
        def _flushing_emit(record, _orig=_original_emit, _fh=file_handler):
            _orig(record)
            _fh.flush()
        file_handler.emit = _flushing_emit
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S",
        ))
        src_logger = logging.getLogger("src")
        src_logger.setLevel(logging.DEBUG)
        src_logger.addHandler(file_handler)

        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S",
        ))
        logging.getLogger("src").addHandler(console)
    except Exception as e:
        print(f"Warning: could not setup file logging: {e}")


def _create_license_view(page: ft.Page):
    """Tela de validacao de licenca antes do bot iniciar."""
    from src.security.license import load_saved_key, validate_license
    from src.config import BOT_VERSION

    chave_input = ft.TextField(
        label="Chave de Licenca",
        hint_text="XXXX-XXXX-XXXX-XXXX",
        width=400,
        autofocus=True,
        value=load_saved_key(),
        text_align=ft.TextAlign.CENTER,
        text_size=16,
    )

    msg_text = ft.Text("", color=NEON_RED, size=12)
    loading = ft.ProgressRing(width=20, height=20, visible=False)

    async def do_validate_async(e=None):
        chave = (chave_input.value or "").strip()
        if not chave:
            msg_text.value = "Digite sua chave de licenca."
            msg_text.color = NEON_RED
            page.update()
            return

        loading.visible = True
        msg_text.value = "Validando..."
        msg_text.color = NEON_BLUE
        page.update()

        # Rodar validacao em thread para nao bloquear o event loop
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, validate_license, chave)
        loading.visible = False

        if result.get("sucesso"):
            nome = result.get("nome", "Cliente")
            dias = result.get("dias_restantes", "?")
            msg_text.value = f"OK! Bem-vindo {nome} ({dias} dias)"
            msg_text.color = NEON_GREEN
            page.update()

            await asyncio.sleep(1)

            # Transicao para o app principal (no mesmo contexto async)
            page.controls.clear()
            from src.ws.parsers import get_platform_names
            platforms = get_platform_names()
            config_view = _create_multi_config(platforms)
            page.add(config_view)
            page.update()
        else:
            msg = result.get("mensagem", "Licenca invalida")
            msg_text.value = msg
            msg_text.color = NEON_RED
            page.update()

            if result.get("force_update"):
                await asyncio.sleep(3)
                page.window.close()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(height=80),
                ft.Text("TucunareBot", size=42, weight=ft.FontWeight.BOLD, color=NEON_GREEN),
                ft.Text(f"v{BOT_VERSION} - Multi-Plataforma", size=14, color=TEXT_DIM),
                ft.Container(height=40),
                ft.Text("Validacao de Licenca", size=18, color=TEXT_PRIMARY),
                ft.Container(height=20),
                chave_input,
                ft.Container(height=10),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            content=ft.Text("Validar e Entrar", weight=ft.FontWeight.BOLD),
                            on_click=do_validate_async,
                            bgcolor=NEON_GREEN,
                            color="#000000",
                            width=400,
                            height=45,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                ft.Row([loading, msg_text], alignment=ft.MainAxisAlignment.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )


def _flet_main(page: ft.Page):
    """Flet page setup for multi-platform mode."""
    global _page_ref, _config_on_start

    try:
        _page_ref = page
        _config_on_start = _start_brain

        from src.config import BOT_VERSION
        page.title = f"TucunareBot v{BOT_VERSION} - Multi-Plataforma"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = BG_MAIN
        page.window.width = 1400
        page.window.height = 850
        page.window.min_width = 1100
        page.window.min_height = 650
        page.padding = ft.padding.all(12)

        _setup_file_logging()

        # Tela de licenca primeiro
        license_view = _create_license_view(page)
        page.add(license_view)
        page.update()

    except Exception as exc:
        import traceback
        err_msg = traceback.format_exc()
        # Gravar erro em arquivo
        try:
            crash_log = Path(sys.executable).parent / "crash.log" if getattr(sys, "frozen", False) else Path("crash.log")
            crash_log.write_text(err_msg, encoding="utf-8")
        except Exception:
            pass
        # Mostrar erro na tela do Flet
        page.bgcolor = "#1a1a2e"
        page.controls.clear()
        page.add(
            ft.Column([
                ft.Text("TucunareBot - Erro na Inicializacao", size=24, color="#ef4444", weight=ft.FontWeight.BOLD),
                ft.Text("Envie o conteudo abaixo para o suporte:", size=14, color="#ccc"),
                ft.TextField(value=err_msg, multiline=True, min_lines=15, max_lines=25, read_only=True, width=900, text_size=11),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16)
        )
        page.update()


def main():
    """Entry point for multi-platform mode."""
    try:
        ft.app(target=_flet_main, view=ft.AppView.WEB_BROWSER)
    except Exception as exc:
        import traceback
        err_msg = traceback.format_exc()
        try:
            crash_log = Path(sys.executable).parent / "crash.log" if getattr(sys, "frozen", False) else Path("crash.log")
            crash_log.write_text(err_msg, encoding="utf-8")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
