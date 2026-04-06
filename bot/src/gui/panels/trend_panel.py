#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TREND PANEL
===========

Trend Monitor panel for the dashboard. Each platform gets its own instance.
Shows:
- Day classification badge (MUITO LUCRATIVO / QUENTE / NORMAL / FRIO)
- 4 key metrics (Prob. Fim+, Mediana, Var. Restante, Faixa P10-P90)
- Canvas chart 1: Percentile bands (P10/P25/P50/P75/P90) + TODAY overlay
- Canvas chart 2: Top 5 similar days overlay + TODAY

Uses flet.canvas for charts, following the pattern of history.py/financial.py.
"""

import flet as ft
import flet.canvas as cv

from src.gui.theme import (
    BG_CARD, BG_INPUT,
    NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW, NEON_CYAN,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    card_container, section_title,
)

# Chart dimensions
CHART_W = 500
CHART_H = 160
MARGIN_L = 5
MARGIN_R = 60  # space for labels on right

# Colors
TODAY_COLOR = "#FFE040FB"  # bright magenta for today's line
BAND_OUTER = "#1A4fc3f7"  # P10-P90 band (very transparent blue)
BAND_INNER = "#334fc3f7"  # P25-P75 band (semi-transparent blue)
MEDIAN_COLOR = NEON_BLUE   # P50 line
GRID_COLOR = "#252940"
ZERO_COLOR = "#5c5c7a"

# Similar days overlay colors
SIMILAR_COLORS = [
    "#CCFFD54F",  # amber
    "#CCCE93D8",  # purple
    "#CC64B5F6",  # blue
    "#CC81C784",  # green
    "#CCFF8A65",  # orange
]


class TrendPanel:
    """Instance-based trend panel. One per platform."""

    def __init__(self):
        self._canvas_bands = None
        self._canvas_similar = None
        self._badge_class = None
        self._txt_desc = None
        self._txt_n_similar = None
        self._txt_prob = None
        self._txt_median = None
        self._txt_var = None
        self._txt_range = None
        self._loading_text = None

    def create(self) -> ft.Container:
        """Build the trend monitor panel. Returns a Container."""
        self._canvas_bands = cv.Canvas([], height=CHART_H, width=float("inf"))
        self._canvas_similar = cv.Canvas([], height=CHART_H, width=float("inf"))

        self._badge_class = ft.Container(
            content=ft.Text(
                "AGUARDANDO", size=11, color="white",
                weight=ft.FontWeight.BOLD,
            ),
            bgcolor=TEXT_DIM,
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=3),
        )

        self._txt_desc = ft.Text(
            "Coletando dados do dia...",
            size=10, color=TEXT_DIM, italic=True,
        )

        self._txt_n_similar = ft.Text("", size=10, color=TEXT_DIM)

        # 4 metric cards
        self._txt_prob = ft.Text("--", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
        self._txt_median = ft.Text("--", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
        self._txt_var = ft.Text("--", size=14, color=TEXT_SECONDARY)
        self._txt_range = ft.Text("--", size=14, color=TEXT_SECONDARY)

        self._loading_text = ft.Text(
            "Carregando perfis historicos...", size=10, color=NEON_YELLOW,
        )

        def _metric_card(label: str, value_ctrl: ft.Text) -> ft.Container:
            return ft.Container(
                content=ft.Column([
                    ft.Text(label, size=9, color=TEXT_SECONDARY),
                    value_ctrl,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                bgcolor=BG_INPUT,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )

        metrics = ft.Row([
            _metric_card("PROB. FIM +", self._txt_prob),
            _metric_card("MEDIANA ESPERADA", self._txt_median),
            _metric_card("VAR. RESTANTE", self._txt_var),
            _metric_card("FAIXA P10-P90", self._txt_range),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER, wrap=True)

        content = ft.Column([
            # Header
            ft.Row([
                section_title("TREND MONITOR", ft.Icons.TRENDING_UP),
                self._badge_class,
                ft.Container(expand=True),
                self._txt_n_similar,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self._txt_desc,
            self._loading_text,
            ft.Divider(color=TEXT_DIM, height=1),
            metrics,
            ft.Divider(color=TEXT_DIM, height=1),
            ft.Text("Faixas de Percentil (projecao 24h)", size=10, color=TEXT_DIM),
            self._canvas_bands,
            ft.Divider(color=TEXT_DIM, height=1),
            ft.Text("Cenarios Analogos (top 5)", size=10, color=TEXT_DIM),
            self._canvas_similar,
        ], spacing=6)

        return card_container(content)

    def update(self, state: dict) -> None:
        """Update trend panel with new analysis state."""
        if not state:
            return

        ready = state.get("ready", False)
        profiles_loaded = state.get("profiles_loaded", False)
        error = state.get("error", "")

        # Loading state
        if self._loading_text:
            if error:
                self._loading_text.value = f"Erro: {error}"
                self._loading_text.color = NEON_RED
                self._loading_text.visible = True
            elif not profiles_loaded:
                n = state.get("profiles_count", 0)
                self._loading_text.value = "Carregando perfis historicos..."
                self._loading_text.visible = True
            elif not ready:
                n = state.get("profiles_count", 0)
                r = state.get("total_rounds_today", 0)
                self._loading_text.value = f"{n} perfis | {r} rounds hoje | Aguardando 2h+ de dados..."
                self._loading_text.color = NEON_YELLOW
                self._loading_text.visible = True
            else:
                self._loading_text.visible = False

        if not ready:
            return

        # Classification badge
        day_class = state.get("day_class", "AGUARDANDO")
        day_color = state.get("day_class_color", TEXT_DIM)
        if self._badge_class:
            # Display-friendly name (replace underscore)
            display_name = day_class.replace("_", " ")
            self._badge_class.content.value = display_name
            self._badge_class.bgcolor = day_color

        # Description
        if self._txt_desc:
            desc = state.get("day_class_desc", "")
            consensus = state.get("consensus_pct", 0)
            n_sim = state.get("n_similar_found", 0)
            if n_sim > 0 and consensus > 0:
                self._txt_desc.value = f"{consensus:.0f}% dos dias similares concordam"
            else:
                self._txt_desc.value = desc

        # N similar
        if self._txt_n_similar:
            n = state.get("n_similar_found", 0)
            self._txt_n_similar.value = f"{n} dias similares" if n > 0 else ""

        # Metrics
        prob = state.get("prob_positive_end", 0)
        if self._txt_prob:
            self._txt_prob.value = f"{prob:.0f}%"
            self._txt_prob.color = NEON_GREEN if prob >= 60 else (NEON_RED if prob < 40 else TEXT_PRIMARY)

        median = state.get("median_expected", 0)
        if self._txt_median:
            self._txt_median.value = f"{median:+.1f}"
            self._txt_median.color = NEON_GREEN if median > 0 else (NEON_RED if median < 0 else TEXT_PRIMARY)

        var = state.get("remaining_variation", 0)
        if self._txt_var:
            self._txt_var.value = f"{var:+.1f}"

        p10 = state.get("range_p10", 0)
        p90 = state.get("range_p90", 0)
        if self._txt_range:
            self._txt_range.value = f"{p10:+.0f} a {p90:+.0f}"

        # Draw charts
        self._draw_percentile_bands(state)
        self._draw_similar_days(state)

    # -- Chart Drawing --

    def _draw_percentile_bands(self, state: dict):
        """Draw percentile bands chart with TODAY overlay."""
        if not self._canvas_bands:
            return

        bands = {
            "p10": state.get("band_p10", []),
            "p25": state.get("band_p25", []),
            "p50": state.get("band_p50", []),
            "p75": state.get("band_p75", []),
            "p90": state.get("band_p90", []),
        }
        today = state.get("today_curve", [])
        current_hour = state.get("current_hour", 0)

        if not bands["p50"] or len(bands["p50"]) < 24:
            self._canvas_bands.shapes = []
            return

        shapes = self._draw_chart_base(bands, today)

        # P10-P90 band (vertical fill lines)
        for hour in range(24):
            x = _x_pos(hour)
            y_top = _y_pos(bands["p90"][hour], bands, today)
            y_bot = _y_pos(bands["p10"][hour], bands, today)
            shapes.append(cv.Line(
                x, y_top, x, y_bot,
                paint=ft.Paint(color=BAND_OUTER, stroke_width=CHART_W / 24),
            ))

        # P25-P75 band (darker)
        for hour in range(24):
            x = _x_pos(hour)
            y_top = _y_pos(bands["p75"][hour], bands, today)
            y_bot = _y_pos(bands["p25"][hour], bands, today)
            shapes.append(cv.Line(
                x, y_top, x, y_bot,
                paint=ft.Paint(color=BAND_INNER, stroke_width=CHART_W / 24),
            ))

        # P50 median line
        for i in range(23):
            x1 = _x_pos(i)
            y1 = _y_pos(bands["p50"][i], bands, today)
            x2 = _x_pos(i + 1)
            y2 = _y_pos(bands["p50"][i + 1], bands, today)
            shapes.append(cv.Line(x1, y1, x2, y2,
                                  paint=ft.Paint(color=MEDIAN_COLOR, stroke_width=1.5)))

        # TODAY line
        self._draw_today_line(shapes, today, bands, current_hour)

        # NOW marker
        self._draw_now_marker(shapes, current_hour)

        # Legend
        shapes.append(cv.Text(CHART_W - MARGIN_R + 5, 5, "P50",
                               style=ft.TextStyle(size=8, color=MEDIAN_COLOR)))
        shapes.append(cv.Text(CHART_W - MARGIN_R + 5, 17, "HOJE",
                               style=ft.TextStyle(size=8, color=TODAY_COLOR)))

        self._canvas_bands.shapes = shapes

    def _draw_similar_days(self, state: dict):
        """Draw similar days overlay chart."""
        if not self._canvas_similar:
            return

        similar = state.get("similar_days", [])
        today = state.get("today_curve", [])
        current_hour = state.get("current_hour", 0)
        bands = {
            "p10": state.get("band_p10", []),
            "p90": state.get("band_p90", []),
        }

        if not similar:
            self._canvas_similar.shapes = []
            return

        # Collect all values for Y-range
        all_vals = list(today)
        for sd in similar:
            all_vals.extend(sd.get("curve", []))

        if not all_vals:
            return

        shapes = self._draw_chart_base_from_vals(all_vals)

        # Draw similar day curves
        for idx, sd in enumerate(similar):
            curve = sd.get("curve", [])
            color = SIMILAR_COLORS[idx % len(SIMILAR_COLORS)]
            corr = sd.get("correlation", 0)

            for i in range(len(curve) - 1):
                x1 = _x_pos(i)
                y1 = _y_pos_raw(curve[i], all_vals)
                x2 = _x_pos(i + 1)
                y2 = _y_pos_raw(curve[i + 1], all_vals)
                shapes.append(cv.Line(x1, y1, x2, y2,
                                      paint=ft.Paint(color=color, stroke_width=1.5)))

            # Label at end
            if curve:
                end_y = _y_pos_raw(curve[-1], all_vals)
                label = f"{sd['date'][-5:]} r={corr:.2f}"
                shapes.append(cv.Text(
                    CHART_W - MARGIN_R + 3, end_y - 5, label,
                    style=ft.TextStyle(size=7, color=color.replace("CC", "FF")),
                ))

        # TODAY line (on top, bold)
        if today and len(today) > 1:
            for i in range(len(today) - 1):
                x1 = _x_pos(i)
                y1 = _y_pos_raw(today[i], all_vals)
                x2 = _x_pos(i + 1)
                y2 = _y_pos_raw(today[i + 1], all_vals)
                shapes.append(cv.Line(x1, y1, x2, y2,
                                      paint=ft.Paint(color=TODAY_COLOR, stroke_width=3)))
            # End dot
            last_x = _x_pos(len(today) - 1)
            last_y = _y_pos_raw(today[-1], all_vals)
            shapes.append(cv.Circle(last_x, last_y, 4,
                                    paint=ft.Paint(color=TODAY_COLOR,
                                                   style=ft.PaintingStyle.FILL)))

        # NOW marker
        self._draw_now_marker(shapes, current_hour)

        self._canvas_similar.shapes = shapes

    def _draw_chart_base(self, bands: dict, today: list) -> list:
        """Draw grid and zero line. Returns shapes list."""
        all_vals = (
            bands.get("p10", []) + bands.get("p90", []) + today
        )
        return self._draw_chart_base_from_vals(all_vals)

    def _draw_chart_base_from_vals(self, all_vals: list) -> list:
        """Draw grid and zero line from a flat list of all values."""
        shapes = []

        # Hour grid lines
        for gh in [0, 6, 12, 18, 23]:
            gx = _x_pos(gh)
            shapes.append(cv.Line(gx, 0, gx, CHART_H,
                                  paint=ft.Paint(color=GRID_COLOR, stroke_width=0.5)))
            shapes.append(cv.Text(gx - 5, CHART_H - 10, f"{gh}h",
                                  style=ft.TextStyle(size=8, color=TEXT_DIM)))

        # Zero line
        if all_vals:
            zero_y = _y_pos_raw(0, all_vals)
            shapes.append(cv.Line(MARGIN_L, zero_y, CHART_W - MARGIN_R, zero_y,
                                  paint=ft.Paint(color=ZERO_COLOR, stroke_width=1)))
            shapes.append(cv.Text(MARGIN_L, zero_y - 12, "0",
                                  style=ft.TextStyle(size=8, color=ZERO_COLOR)))

        return shapes

    def _draw_today_line(self, shapes: list, today: list, bands: dict, current_hour: int):
        """Draw TODAY's curve on the chart."""
        if not today or len(today) < 2:
            return

        for i in range(len(today) - 1):
            x1 = _x_pos(i)
            y1 = _y_pos(today[i], bands, today)
            x2 = _x_pos(i + 1)
            y2 = _y_pos(today[i + 1], bands, today)
            shapes.append(cv.Line(x1, y1, x2, y2,
                                  paint=ft.Paint(color=TODAY_COLOR, stroke_width=3)))

        # End dot
        last_x = _x_pos(len(today) - 1)
        last_y = _y_pos(today[-1], bands, today)
        shapes.append(cv.Circle(last_x, last_y, 4,
                                paint=ft.Paint(color=TODAY_COLOR,
                                               style=ft.PaintingStyle.FILL)))

    def _draw_now_marker(self, shapes: list, current_hour: int):
        """Draw vertical AGORA line at current hour."""
        now_x = _x_pos(current_hour)
        shapes.append(cv.Line(now_x, 0, now_x, CHART_H,
                              paint=ft.Paint(color=NEON_YELLOW, stroke_width=1)))
        shapes.append(cv.Text(now_x + 3, 2, "AGORA",
                              style=ft.TextStyle(size=8, color=NEON_YELLOW)))


# -- Helper functions (module-level for performance) --

def _x_pos(hour: int) -> float:
    """Convert hour (0-23) to X pixel coordinate."""
    usable_w = CHART_W - MARGIN_L - MARGIN_R
    return MARGIN_L + (hour / 23) * usable_w


def _y_pos(val: float, bands: dict, today: list) -> float:
    """Convert value to Y pixel using bands+today for range."""
    all_vals = bands.get("p10", []) + bands.get("p90", []) + today
    return _y_pos_raw(val, all_vals)


def _y_pos_raw(val: float, all_vals: list) -> float:
    """Convert value to Y pixel given all values for range calculation."""
    if not all_vals:
        return CHART_H / 2
    y_min = min(all_vals) - 1
    y_max = max(all_vals) + 1
    y_range = y_max - y_min if y_max != y_min else 1
    return CHART_H - ((val - y_min) / y_range) * (CHART_H - 20) - 10
