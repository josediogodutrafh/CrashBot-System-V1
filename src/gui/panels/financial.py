"""
Financial Panel - Caixa, banca, saldo, profit, stop gain/loss, balance sparkline (Flet).
"""

from datetime import datetime

import flet as ft
import flet.canvas as cv

from src.gui.theme import (
    BG_CARD, NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container, section_title,
)

# UI refs
_txt_caixa = None
_txt_banca = None
_txt_saldo = None
_txt_rounds = None
_txt_tempo = None
_bar_sg = None
_txt_sg = None
_bar_sl = None
_txt_sl = None
_txt_apostas = None
_txt_balanco = None
_canvas = None

# Balance history
_balance_history = []
_max_points = 100


def create() -> ft.Container:
    global _txt_caixa, _txt_banca, _txt_saldo, _txt_rounds, _txt_tempo
    global _bar_sg, _txt_sg, _bar_sl, _txt_sl
    global _txt_apostas, _txt_balanco, _canvas

    _txt_caixa = ft.Text("R$ 0.00", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    _txt_banca = ft.Text("R$ 0.00", size=14, color=TEXT_SECONDARY)
    _txt_saldo = ft.Text("R$ 0.00", size=20, weight=ft.FontWeight.BOLD, color=NEON_BLUE)
    _txt_rounds = ft.Text("Rodadas: 0", size=12, color=TEXT_DIM)
    _txt_tempo = ft.Text("", size=12, color=TEXT_DIM)

    _bar_sg = ft.ProgressBar(value=0, bar_height=10, color=NEON_GREEN, bgcolor="#252940")
    _txt_sg = ft.Text("Stop Gain: 0%", size=11, color=TEXT_SECONDARY)
    _bar_sl = ft.ProgressBar(value=0, bar_height=10, color=NEON_RED, bgcolor="#252940")
    _txt_sl = ft.Text("Stop Loss: 0%", size=11, color=TEXT_SECONDARY)

    _txt_apostas = ft.Text("Apostas: nenhuma", size=12, color=TEXT_SECONDARY)
    _txt_balanco = ft.Text("Balanco: R$ +0.00", size=14, weight=ft.FontWeight.BOLD, color=NEON_GREEN)

    _canvas = cv.Canvas([], height=100, width=float("inf"))

    content = ft.Column([
        section_title("STATUS FINANCEIRO", ft.Icons.ACCOUNT_BALANCE_WALLET),
        ft.Divider(color=TEXT_DIM, height=8),

        # Key metrics
        ft.Row([
            ft.Column([
                ft.Text("Caixa", size=11, color=TEXT_DIM),
                _txt_caixa,
            ], spacing=2),
            ft.Column([
                ft.Text("Banca", size=11, color=TEXT_DIM),
                _txt_banca,
            ], spacing=2),
            ft.Column([
                ft.Text("Saldo Atual", size=11, color=TEXT_DIM),
                _txt_saldo,
            ], spacing=2),
        ], spacing=30),

        ft.Row([_txt_rounds, ft.Container(width=20), _txt_tempo], spacing=4),

        ft.Divider(color=TEXT_DIM, height=8),

        # Stop Gain
        _txt_sg,
        _bar_sg,

        # Stop Loss
        ft.Container(height=4),
        _txt_sl,
        _bar_sl,

        ft.Divider(color=TEXT_DIM, height=8),

        _txt_apostas,
        _txt_balanco,

        ft.Divider(color=TEXT_DIM, height=8),

        ft.Text("Evolucao do Saldo", size=11, color=TEXT_DIM),
        _canvas,
    ], spacing=4)

    return card_container(content)


def update(state: dict) -> None:
    global _balance_history

    caixa = state.get("caixa", 0)
    banca = state.get("banca", 0)
    n_bancas = state.get("n_bancas", 0)
    saldo = state.get("saldo", 0)
    rounds = state.get("round_count", 0)
    hits = state.get("session_hits", 0)
    misses = state.get("session_misses", 0)
    profit = state.get("session_profit", 0)

    _txt_caixa.value = f"R$ {caixa:.2f}"
    _txt_banca.value = f"R$ {banca:.2f} ({n_bancas:.1f}x)"
    _txt_saldo.value = f"R$ {saldo:.2f}"
    _txt_rounds.value = f"Rodadas: {rounds}"

    # Time
    start = state.get("session_start", 0)
    session_hours = state.get("session_hours", 0)
    if start > 0:
        elapsed = datetime.now().timestamp() - start
        hours = int(elapsed // 3600)
        mins = int((elapsed % 3600) // 60)
        if session_hours > 0:
            remaining = max(0, session_hours * 3600 - elapsed)
            rh = int(remaining // 3600)
            rm = int((remaining % 3600) // 60)
            _txt_tempo.value = f"Tempo: {hours}h {mins}m (resta {rh}h {rm}m)"
        else:
            _txt_tempo.value = f"Tempo: {hours}h {mins}m"

    # Stop Gain
    sg_pct = state.get("stop_gain_pct", 20)
    sg_val = state.get("stop_gain_value", 0)
    meta_prog = state.get("meta_progress", 0)
    _bar_sg.value = min(meta_prog, 1.0)
    _txt_sg.value = f"Stop Gain: {sg_pct:.0f}% caixa = R${sg_val:.0f} ({meta_prog*100:.0f}%)"

    # Stop Loss
    sl_pct = state.get("stop_loss_pct", 100)
    sl_val = state.get("stop_loss_value", 0)
    loss_prog = state.get("loss_progress", 0)
    _bar_sl.value = min(loss_prog, 1.0)
    _txt_sl.value = f"Stop Loss: {sl_pct:.0f}% caixa = R${sl_val:.0f} ({loss_prog*100:.0f}%)"

    # Bets
    total = hits + misses
    if total > 0:
        wr = hits / total * 100
        _txt_apostas.value = f"Apostas: {hits} hits / {misses} misses ({wr:.0f}%)"
    else:
        _txt_apostas.value = "Apostas: nenhuma ainda"

    # Balance
    color = NEON_GREEN if profit >= 0 else NEON_RED
    _txt_balanco.value = f"Balanco: R$ {profit:+.2f}"
    _txt_balanco.color = color

    # Balance sparkline via canvas
    if saldo > 0:
        _balance_history.append(saldo)
        if len(_balance_history) > _max_points:
            _balance_history.pop(0)
        if len(_balance_history) >= 2:
            _draw_sparkline(_balance_history)


def _draw_sparkline(data: list):
    """Draw a sparkline chart on the canvas."""
    if not _canvas or len(data) < 2:
        return

    w = 500  # approximate canvas width
    h = 90
    min_v = min(data)
    max_v = max(data)
    v_range = max_v - min_v if max_v != min_v else 1

    # Build line points
    points = []
    for i, v in enumerate(data):
        x = (i / (len(data) - 1)) * w
        y = h - ((v - min_v) / v_range) * (h - 10) - 5
        points.append((x, y))

    # Build shapes
    shapes = []

    # Grid lines (3 horizontal)
    for j in range(3):
        gy = 10 + j * (h - 20) / 2
        shapes.append(cv.Line(0, gy, w, gy, paint=ft.Paint(color="#252940", stroke_width=1)))

    # Main line
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        shapes.append(cv.Line(x1, y1, x2, y2,
                               paint=ft.Paint(color=NEON_BLUE, stroke_width=2)))

    # End dot
    if points:
        lx, ly = points[-1]
        shapes.append(cv.Circle(lx, ly, 3,
                                 paint=ft.Paint(color=NEON_BLUE, style=ft.PaintingStyle.FILL)))

    _canvas.shapes = shapes
