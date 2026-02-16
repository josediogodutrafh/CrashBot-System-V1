"""
Header Panel - Time, WS status, setup, meta progress, premium (Flet).

Includes a STATUS BAR below the header that shows connection phase,
last action, and errors - always visible at the top of the dashboard.
"""

from datetime import datetime

import flet as ft

from src.gui.theme import (
    BG_HEADER, NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW, NEON_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container,
)

# UI refs
_txt_time = None
_txt_ws = None
_txt_setup = None
_txt_premium = None
_txt_pending = None
_bar_meta = None
_txt_meta = None
_txt_status = None      # Status bar (last_action) - always visible
_icon_status = None
_container_status = None


def create() -> ft.Container:
    global _txt_time, _txt_ws, _txt_setup, _txt_premium
    global _txt_pending, _bar_meta, _txt_meta
    global _txt_status, _icon_status, _container_status

    _txt_time = ft.Text("--:--:--", size=14, color=TEXT_PRIMARY,
                         font_family="Consolas", weight=ft.FontWeight.BOLD)
    _txt_ws = ft.Text("WS: ---", size=12, color=TEXT_DIM)
    _txt_setup = ft.Text("Setup: ---", size=12, color=TEXT_SECONDARY)
    _txt_premium = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=NEON_GREEN)
    _txt_pending = ft.Text("", size=11, color=NEON_PURPLE)
    _bar_meta = ft.ProgressBar(value=0, bar_height=6, color=NEON_GREEN, bgcolor="#252940", width=200)
    _txt_meta = ft.Text("Meta: 0%", size=11, color=TEXT_SECONDARY)

    # Status bar - shows last_action, connection phase, errors
    _icon_status = ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=NEON_BLUE)
    _txt_status = ft.Text(
        "Iniciando...", size=13, color=NEON_BLUE,
        weight=ft.FontWeight.W_500,
        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        expand=True,
    )
    _container_status = ft.Container(
        content=ft.Row([_icon_status, _txt_status], spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="#1a1d35",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
    )

    top_row = ft.Row([
        ft.Row([
            ft.Icon(ft.Icons.ROCKET_LAUNCH, size=20, color=NEON_GREEN),
            ft.Text("CRASHBOT", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ], spacing=6),
        ft.VerticalDivider(width=1, color=TEXT_DIM),
        _txt_time,
        ft.VerticalDivider(width=1, color=TEXT_DIM),
        _txt_ws,
        ft.VerticalDivider(width=1, color=TEXT_DIM),
        _txt_setup,
        ft.VerticalDivider(width=1, color=TEXT_DIM),
        _txt_premium,
        _txt_pending,
        ft.Container(expand=True),
        ft.Column([_txt_meta, _bar_meta], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END),
    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)

    return ft.Container(
        content=ft.Column([top_row, _container_status], spacing=6),
        bgcolor=BG_HEADER,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
    )


def update(state: dict) -> None:
    # Time
    try:
        from pytz import timezone
        now = datetime.now(timezone("America/Sao_Paulo"))
        _txt_time.value = now.strftime("%H:%M:%S")
    except Exception:
        _txt_time.value = datetime.now().strftime("%H:%M:%S")

    # WS status
    connected = state.get("ws_connected", False)
    ws_phase = state.get("ws_phase", "unknown")
    if connected:
        _txt_ws.value = f"WS: ON {ws_phase.upper()}"
        _txt_ws.color = NEON_GREEN
    else:
        _txt_ws.value = "WS: OFF"
        _txt_ws.color = NEON_RED

    # Setup
    display = state.get("setup_display", "N/A")
    _txt_setup.value = f"Setup: {display}"

    # Premium
    premium = state.get("premium_status", "REGULAR")
    if "PREMIUM" in premium:
        _txt_premium.value = premium
        _txt_premium.color = NEON_GREEN
    else:
        _txt_premium.value = premium
        _txt_premium.color = TEXT_DIM

    # Pending swap
    pending = state.get("pending_swap")
    _txt_pending.value = f"  >> {pending}" if pending else ""

    # Meta progress
    progress = state.get("meta_progress", 0)
    reached = state.get("meta_reached", False)
    _bar_meta.value = min(progress, 1.0)
    _bar_meta.color = NEON_YELLOW if reached else NEON_GREEN

    pct_str = f"{progress * 100:.0f}%"
    if reached:
        _txt_meta.value = f"Meta: {pct_str} ATINGIDA!"
        _txt_meta.color = NEON_YELLOW
    else:
        _txt_meta.value = f"Meta: {pct_str}"
        _txt_meta.color = TEXT_SECONDARY

    # ── Status bar (last_action) - always visible ──
    action = state.get("last_action", "")
    bot_phase = state.get("phase", "config")

    if action and _txt_status:
        _txt_status.value = action

        if "ERRO" in action:
            _txt_status.color = NEON_RED
            _txt_status.weight = ft.FontWeight.BOLD
            _icon_status.name = ft.Icons.ERROR_OUTLINE
            _icon_status.color = NEON_RED
            _container_status.bgcolor = "#2a1520"
        elif bot_phase == "connecting" or not connected:
            _txt_status.color = NEON_YELLOW
            _txt_status.weight = ft.FontWeight.W_500
            _icon_status.name = ft.Icons.WIFI_FIND
            _icon_status.color = NEON_YELLOW
            _container_status.bgcolor = "#2a2515"
        elif connected and bot_phase == "running":
            _txt_status.color = NEON_GREEN
            _txt_status.weight = ft.FontWeight.NORMAL
            _icon_status.name = ft.Icons.CHECK_CIRCLE_OUTLINE
            _icon_status.color = NEON_GREEN
            _container_status.bgcolor = "#152a1a"
        else:
            _txt_status.color = TEXT_SECONDARY
            _txt_status.weight = ft.FontWeight.NORMAL
            _icon_status.name = ft.Icons.INFO_OUTLINE
            _icon_status.color = TEXT_DIM
            _container_status.bgcolor = "#1a1d35"
