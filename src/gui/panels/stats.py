"""
Stats Panel - Win/loss bars, sequences, WS stats (Flet).
"""

import time

import flet as ft

from src.gui.theme import (
    BG_CARD, NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container, section_title, stat_row,
)

# UI refs
_win_bar = None
_loss_bar = None
_txt_wins_label = None
_txt_loss_label = None
_stats_column = None


def create() -> ft.Container:
    global _win_bar, _loss_bar, _txt_wins_label, _txt_loss_label, _stats_column

    _txt_wins_label = ft.Text("Wins: 0", size=11, color=NEON_GREEN, text_align=ft.TextAlign.CENTER)
    _txt_loss_label = ft.Text("Breaks: 0", size=11, color=NEON_RED, text_align=ft.TextAlign.CENTER)

    _win_bar = ft.Container(
        height=0, width=60, bgcolor=NEON_GREEN,
        border_radius=ft.border_radius.only(top_left=4, top_right=4),
        alignment=ft.Alignment(0, 1),
    )
    _loss_bar = ft.Container(
        height=0, width=60, bgcolor=NEON_RED,
        border_radius=ft.border_radius.only(top_left=4, top_right=4),
        alignment=ft.Alignment(0, 1),
    )

    chart_area = ft.Row([
        ft.Column([
            ft.Container(content=_win_bar, height=80, alignment=ft.Alignment(0, 1)),
            _txt_wins_label,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
        ft.Container(width=20),
        ft.Column([
            ft.Container(content=_loss_bar, height=80, alignment=ft.Alignment(0, 1)),
            _txt_loss_label,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)

    _stats_column = ft.Column([], spacing=2)

    content = ft.Column([
        section_title("ESTATISTICAS", ft.Icons.BAR_CHART),
        ft.Divider(color=TEXT_DIM, height=8),
        chart_area,
        ft.Divider(color=TEXT_DIM, height=8),
        _stats_column,
    ], spacing=4)

    return card_container(content)


def update(state: dict) -> None:
    total_seqs = state.get("total_sequences", 0)
    total_wins = state.get("total_wins", 0)
    total_breaks = state.get("total_breaks", 0)
    total_profit = state.get("total_profit", 0.0)
    wins_by_dobra = state.get("wins_by_dobra", {})
    meta_reached = state.get("meta_reached", False)
    meta_progress = state.get("meta_progress", 0.0)

    # Update win/loss bars (scale to max 80px)
    max_val = max(total_wins, total_breaks, 1)
    _win_bar.height = max(2, (total_wins / max_val) * 70)
    _loss_bar.height = max(2, (total_breaks / max_val) * 70)
    _txt_wins_label.value = f"Wins: {total_wins}"
    _txt_loss_label.value = f"Breaks: {total_breaks}"

    # Rebuild stats rows
    _stats_column.controls.clear()

    _stats_column.controls.append(stat_row("Sequencias", str(total_seqs), TEXT_PRIMARY))
    _stats_column.controls.append(stat_row("Vitorias", str(total_wins), NEON_GREEN))

    for dobra_key in sorted(wins_by_dobra.keys()):
        count = wins_by_dobra[dobra_key]
        baixas = 5 + int(dobra_key)
        _stats_column.controls.append(
            stat_row(f"  D{dobra_key} ({baixas}+ baixas)", str(count), TEXT_DIM)
        )

    _stats_column.controls.append(stat_row("Quebras", str(total_breaks), NEON_RED))

    _stats_column.controls.append(ft.Container(height=4))

    profit_color = NEON_GREEN if total_profit >= 0 else NEON_RED
    _stats_column.controls.append(stat_row("LUCRO TOTAL", f"R$ {total_profit:+.2f}", profit_color))

    meta_str = f"{meta_progress * 100:.1f}%"
    if meta_reached:
        meta_str += "  ATINGIDA!"
    meta_color = NEON_GREEN if meta_reached else NEON_YELLOW
    _stats_column.controls.append(stat_row("Meta", meta_str, meta_color))

    _stats_column.controls.append(ft.Divider(color=TEXT_DIM, height=8))

    # WS stats
    ws_frames = state.get("ws_frames", 0)
    ws_rounds = state.get("ws_rounds", 0)
    ws_errors = state.get("ws_errors", 0)
    ws_uptime = state.get("ws_uptime", 0)
    ws_last = state.get("ws_last_frame", 0)

    _stats_column.controls.append(stat_row("WS Frames", str(ws_frames), TEXT_SECONDARY))
    _stats_column.controls.append(stat_row("WS Rounds", str(ws_rounds), TEXT_SECONDARY))

    if ws_errors > 0:
        _stats_column.controls.append(stat_row("WS Erros", str(ws_errors), NEON_RED))

    mins = int(ws_uptime // 60)
    secs = int(ws_uptime % 60)
    _stats_column.controls.append(stat_row("WS Uptime", f"{mins}m {secs}s", TEXT_DIM))

    if ws_last > 0:
        ago = time.time() - ws_last
        _stats_column.controls.append(stat_row("Ultimo frame", f"{ago:.0f}s atras", TEXT_DIM))
