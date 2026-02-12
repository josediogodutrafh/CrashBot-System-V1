"""
Strategy Panel - Setup, baixas, martingale state, bet table (Flet).
"""

import flet as ft

from src.gui.theme import (
    BG_CARD, NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW, NEON_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container, section_title,
)

# UI refs
_txt_setup = None
_txt_baixos = None
_txt_state = None
_txt_pending = None
_bets_column = None


def create() -> ft.Container:
    global _txt_setup, _txt_baixos, _txt_state, _txt_pending, _bets_column

    _txt_setup = ft.Text("Setup: ---", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    _txt_baixos = ft.Text("0/6", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY,
                           font_family="Consolas")
    _txt_state = ft.Text("Aguardando gatilho...", size=12, color=TEXT_DIM)
    _txt_pending = ft.Text("", size=11, color=NEON_PURPLE)
    _bets_column = ft.Column([], spacing=2)

    content = ft.Column([
        section_title("ESTRATEGIA", ft.Icons.PSYCHOLOGY),
        ft.Divider(color=TEXT_DIM, height=8),

        _txt_setup,

        ft.Row([
            ft.Text("Baixas consecutivas:", size=12, color=TEXT_SECONDARY),
            _txt_baixos,
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),

        _txt_state,

        ft.Divider(color=TEXT_DIM, height=8),

        ft.Text("Apostas por Ciclo", size=11, color=TEXT_DIM),
        _bets_column,

        _txt_pending,
    ], spacing=4)

    return card_container(content)


def update(state: dict) -> None:
    setup_display = state.get("setup_display", "N/A")
    baixos = state.get("baixos_consecutivos", 0)
    trigger = state.get("baixos_trigger", 6)
    baixos_display = state.get("baixos_display", f"{baixos}/{trigger}")
    active = state.get("martingale_active", False)
    dobra = state.get("dobra_atual", 0)
    max_d = state.get("max_dobras", 0)
    n_cycles = state.get("n_cycles", 1)
    cycle_info = state.get("cycle_info")
    bets_by_cycle = state.get("bets_by_cycle", [])
    pending = state.get("pending_swap")

    _txt_setup.value = f"Setup: {setup_display}"
    _txt_baixos.value = str(baixos_display)

    # Color based on proximity to trigger
    if baixos >= trigger:
        _txt_baixos.color = NEON_RED
    elif baixos >= trigger - 2:
        _txt_baixos.color = NEON_YELLOW
    else:
        _txt_baixos.color = TEXT_PRIMARY

    if active:
        if cycle_info and n_cycles > 1:
            ci = cycle_info.get("cycle", 0)
            tc = cycle_info.get("total_cycles", 0)
            _txt_state.value = f"Ciclo {ci}/{tc}  |  Dobra {dobra}/{max_d}"
        else:
            _txt_state.value = f"Dobra {dobra}/{max_d}"
        _txt_state.color = NEON_GREEN
    else:
        _txt_state.value = "Aguardando gatilho..."
        _txt_state.color = TEXT_DIM

    # Rebuild bets list
    _rebuild_bets(bets_by_cycle, active, dobra, n_cycles)

    _txt_pending.value = f"Troca pendente -> {pending}" if pending else ""


def _rebuild_bets(bets_by_cycle: list, active: bool, dobra_atual: int, n_cycles: int):
    _bets_column.controls.clear()

    if not bets_by_cycle:
        _bets_column.controls.append(
            ft.Text("---", size=12, color=TEXT_DIM)
        )
        return

    current_cycle = 0
    for bet in bets_by_cycle:
        if n_cycles > 1 and bet.get("cycle", 0) != current_cycle:
            current_cycle = bet["cycle"]
            _bets_column.controls.append(
                ft.Text(f"  -- Ciclo {current_cycle} --", size=11, color=NEON_BLUE)
            )

        gpos = bet.get("global_pos", 0)
        is_current = active and gpos == dobra_atual
        marker = ">>" if is_current else "  "
        color = NEON_GREEN if is_current else TEXT_SECONDARY
        pos = bet.get("pos_in_cycle", 0)
        mult = bet.get("multiplier", 0)
        value = bet.get("value", 0)

        _bets_column.controls.append(
            ft.Text(
                f"{marker} D{pos} ({mult}x): R$ {value:.2f}",
                size=12, color=color, font_family="Consolas",
            )
        )
