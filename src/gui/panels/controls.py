"""
Controls Panel - Setup buttons, meta, pause, stop, last action (Flet).
"""

import flet as ft

from src.gui.theme import (
    BG_CARD, NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW, NEON_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container, outline_button, neon_button,
)
from src.gui.app_mode import get_setup_buttons

# Callbacks
_on_setup_change = None
_on_meta_cycle = None
_on_pause = None
_on_stop = None

# UI refs
_txt_action = None
_txt_premium = None
_btn_pause = None
_btn_pause_icon = None
_btn_pause_text = None


def set_callbacks(on_setup_change=None, on_meta_cycle=None, on_pause=None, on_stop=None):
    global _on_setup_change, _on_meta_cycle, _on_pause, _on_stop
    _on_setup_change = on_setup_change
    _on_meta_cycle = on_meta_cycle
    _on_pause = on_pause
    _on_stop = on_stop


def create() -> ft.Container:
    global _txt_action, _txt_premium, _btn_pause, _btn_pause_icon, _btn_pause_text

    _txt_action = ft.Text("Aguardando...", size=12, color=TEXT_SECONDARY)
    _txt_premium = ft.Text("", size=11, color=NEON_PURPLE)

    # Setup buttons row (dynamic from app_mode)
    setup_btns = []
    for label, internal in get_setup_buttons():
        setup_btns.append(outline_button(
            text=label, color=NEON_BLUE,
            on_click=_handle_setup, data=internal,
            height=32,
        ))

    # Pause button with mutable inner refs
    _btn_pause_icon = ft.Icon(ft.Icons.PAUSE, size=16, color="white")
    _btn_pause_text = ft.Text("F9 Pause", size=12, color="white", weight=ft.FontWeight.BOLD)
    _btn_pause = ft.ElevatedButton(
        content=ft.Row([_btn_pause_icon, _btn_pause_text],
                        spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(
            bgcolor=NEON_BLUE,
            padding=ft.padding.symmetric(horizontal=12, vertical=4),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=_handle_pause,
        height=32,
    )

    content = ft.Column([
        ft.Row(
            setup_btns + [
                neon_button("F8 Meta", icon=ft.Icons.LOOP,
                            color=NEON_YELLOW, on_click=_handle_meta, height=32),
                _btn_pause,
                neon_button("F10 Stop", icon=ft.Icons.STOP,
                            color=NEON_RED, on_click=_handle_stop, height=32),
            ],
            wrap=True, spacing=6, run_spacing=6,
        ),
        ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=TEXT_DIM),
            _txt_action,
            ft.Container(expand=True),
            _txt_premium,
        ], spacing=6),
    ], spacing=6)

    return card_container(content, padding=12)


def update(state: dict) -> None:
    action = state.get("last_action", "")
    if _txt_action and action:
        _txt_action.value = action
        # Highlight errors in red, bold
        if "ERRO" in action:
            _txt_action.color = NEON_RED
            _txt_action.weight = ft.FontWeight.BOLD
        else:
            _txt_action.color = TEXT_SECONDARY
            _txt_action.weight = None

    paused = state.get("paused", False)
    if _btn_pause_text:
        _btn_pause_text.value = "F9 Resume" if paused else "F9 Pause"
    if _btn_pause_icon:
        _btn_pause_icon.name = ft.Icons.PLAY_ARROW if paused else ft.Icons.PAUSE

    # Premium hours
    hours = state.get("premium_hours_today", [])
    if _txt_premium and hours:
        hours_str = ", ".join(f"{h[0]}h-{h[1]}h" for h in hours if isinstance(h, (list, tuple)))
        _txt_premium.value = f"Premium hoje: {hours_str}" if hours_str else ""


def _handle_setup(e):
    if _on_setup_change and e.control.data:
        _on_setup_change(e.control.data)


def _handle_meta(e):
    if _on_meta_cycle:
        _on_meta_cycle()


def _handle_pause(e):
    if _on_pause:
        _on_pause()


def _handle_stop(e):
    if _on_stop:
        _on_stop()
