"""
Header Panel - Time, WS status, setup, meta progress, premium (Flet).
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


def create() -> ft.Container:
    global _txt_time, _txt_ws, _txt_setup, _txt_premium
    global _txt_pending, _bar_meta, _txt_meta

    _txt_time = ft.Text("--:--:--", size=14, color=TEXT_PRIMARY,
                         font_family="Consolas", weight=ft.FontWeight.BOLD)
    _txt_ws = ft.Text("WS: ---", size=12, color=TEXT_DIM)
    _txt_setup = ft.Text("Setup: ---", size=12, color=TEXT_SECONDARY)
    _txt_premium = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=NEON_GREEN)
    _txt_pending = ft.Text("", size=11, color=NEON_PURPLE)
    _bar_meta = ft.ProgressBar(value=0, bar_height=6, color=NEON_GREEN, bgcolor="#252940", width=200)
    _txt_meta = ft.Text("Meta: 0%", size=11, color=TEXT_SECONDARY)

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
        content=top_row,
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
    phase = state.get("ws_phase", "unknown")
    if connected:
        _txt_ws.value = f"WS: ON {phase.upper()}"
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
