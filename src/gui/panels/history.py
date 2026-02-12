"""
History Panel - Last 30 explosions with colors + sparkline chart (Flet).
"""

import flet as ft
import flet.canvas as cv

from src.gui.theme import (
    BG_CARD, NEON_BLUE, NEON_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    COLOR_VERY_LOW, COLOR_LOW, COLOR_MEDIUM, COLOR_HIGH,
    get_explosion_color, card_container, section_title,
)

# UI refs
_canvas = None
_grid_column = None


def create() -> ft.Container:
    global _canvas, _grid_column

    _canvas = cv.Canvas([], height=120, width=float("inf"))
    _grid_column = ft.Column([], spacing=2)

    legend = ft.Row([
        ft.Text("<1.5x", size=10, color=COLOR_VERY_LOW),
        ft.Text("<2.0x", size=10, color=COLOR_LOW),
        ft.Text("<5.0x", size=10, color=COLOR_MEDIUM),
        ft.Text("5.0x+", size=10, color=COLOR_HIGH),
    ], spacing=16)

    content = ft.Column([
        section_title("HISTORICO DE EXPLOSOES", ft.Icons.HISTORY),
        ft.Divider(color=TEXT_DIM, height=8),
        _canvas,
        _grid_column,
        legend,
    ], spacing=4)

    return card_container(content)


def update(state: dict) -> None:
    explosion_history = state.get("explosion_history", [])
    ultimos = list(explosion_history)[-30:] if explosion_history else []

    # Update canvas chart
    _draw_explosion_chart(ultimos)

    # Update text grid
    _grid_column.controls.clear()

    if not ultimos:
        _grid_column.controls.append(
            ft.Text("Aguardando explosoes...", size=12, color=TEXT_DIM)
        )
        return

    # Build rows of 6 values
    row_items = []
    for i, valor in enumerate(ultimos):
        color = get_explosion_color(valor)
        row_items.append(
            ft.Text(f"{valor:.2f}x", size=12, color=color, font_family="Consolas",
                    weight=ft.FontWeight.W_500)
        )
        if len(row_items) == 6 or i == len(ultimos) - 1:
            _grid_column.controls.append(ft.Row(row_items, spacing=12))
            row_items = []


def _draw_explosion_chart(data: list):
    """Draw explosion values as sparkline with 2.0x threshold."""
    if not _canvas:
        return

    w = 500  # approximate width
    h = 110
    shapes = []

    if len(data) < 2:
        # Empty chart - just draw threshold
        threshold_y = h * 0.6
        shapes.append(cv.Line(0, threshold_y, w, threshold_y,
                               paint=ft.Paint(color=NEON_RED, stroke_width=1,
                                              style=ft.PaintingStyle.STROKE)))
        shapes.append(cv.Text(w - 35, threshold_y - 12, "2.0x",
                               style=ft.TextStyle(size=9, color=NEON_RED)))
        _canvas.shapes = shapes
        return

    min_v = min(min(data), 1.0)
    max_v = max(max(data), 3.0)
    v_range = max_v - min_v if max_v != min_v else 1

    def y_pos(v):
        return h - ((v - min_v) / v_range) * (h - 20) - 10

    # Grid lines
    for gv in [1.0, 2.0, 3.0, 5.0]:
        if min_v <= gv <= max_v:
            gy = y_pos(gv)
            shapes.append(cv.Line(0, gy, w, gy,
                                   paint=ft.Paint(color="#252940", stroke_width=1)))

    # 2.0x threshold line (red)
    threshold_y = y_pos(2.0)
    shapes.append(cv.Line(0, threshold_y, w, threshold_y,
                           paint=ft.Paint(color=NEON_RED, stroke_width=1.5,
                                          style=ft.PaintingStyle.STROKE)))
    shapes.append(cv.Text(w - 35, threshold_y - 12, "2.0x",
                           style=ft.TextStyle(size=9, color=NEON_RED)))

    # Value line
    points = []
    for i, v in enumerate(data):
        x = (i / (len(data) - 1)) * w if len(data) > 1 else w / 2
        y = y_pos(v)
        points.append((x, y))

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        shapes.append(cv.Line(x1, y1, x2, y2,
                               paint=ft.Paint(color=NEON_BLUE, stroke_width=2)))

    # Dots for each value (colored by explosion range)
    for i, (px, py) in enumerate(points):
        dot_color = get_explosion_color(data[i])
        shapes.append(cv.Circle(px, py, 3,
                                 paint=ft.Paint(color=dot_color, style=ft.PaintingStyle.FILL)))

    _canvas.shapes = shapes
