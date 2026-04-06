"""
CrashBot Flet Theme - Dark Gaming Style.

Color palette, card/button factories, explosion color helper.
"""

import flet as ft


# =============================================================================
# COLOR PALETTE - Dark Gaming
# =============================================================================

# Backgrounds
BG_MAIN = "#0f1120"
BG_CARD = "#1a1d2e"
BG_CARD_HOVER = "#222640"
BG_HEADER = "#141728"
BG_INPUT = "#252940"

# Neon accents
NEON_GREEN = ft.Colors.GREEN_400
NEON_RED = ft.Colors.RED_400
NEON_BLUE = "#4fc3f7"
NEON_YELLOW = ft.Colors.AMBER_400
NEON_PURPLE = "#b388ff"
NEON_CYAN = "#00e5ff"

# Text
TEXT_PRIMARY = "#e8eaf6"
TEXT_SECONDARY = "#9e9eb8"
TEXT_DIM = "#5c5c7a"

# Explosion colors (history grid)
COLOR_VERY_LOW = ft.Colors.RED_400       # < 1.5x
COLOR_LOW = ft.Colors.AMBER_400          # < 2.0x
COLOR_MEDIUM = ft.Colors.GREEN_400       # < 5.0x
COLOR_HIGH = "#00e5ff"                   # >= 5.0x (cyan)

# Shadows
CARD_SHADOW = ft.BoxShadow(
    spread_radius=0, blur_radius=12,
    color="#00000060", offset=ft.Offset(0, 4),
)
NEON_GLOW_GREEN = ft.BoxShadow(
    spread_radius=1, blur_radius=8,
    color="#66BB6A40", offset=ft.Offset(0, 0),
)
NEON_GLOW_BLUE = ft.BoxShadow(
    spread_radius=1, blur_radius=8,
    color="#4fc3f740", offset=ft.Offset(0, 0),
)


# =============================================================================
# HELPERS
# =============================================================================

def get_explosion_color(value: float) -> str:
    """Get Flet color string for an explosion value."""
    if value < 1.5:
        return COLOR_VERY_LOW
    elif value < 2.0:
        return COLOR_LOW
    elif value < 5.0:
        return COLOR_MEDIUM
    else:
        return COLOR_HIGH


def card_container(content: ft.Control, **kwargs) -> ft.Container:
    """Wrap content in a styled dark card with rounded corners and shadow."""
    defaults = dict(
        bgcolor=BG_CARD,
        border_radius=16,
        padding=20,
        shadow=CARD_SHADOW,
    )
    defaults.update(kwargs)
    return ft.Container(content=content, **defaults)


def section_title(text: str, icon: str = None) -> ft.Row:
    """Create a styled section header."""
    items = []
    if icon:
        items.append(ft.Icon(icon, size=18, color=NEON_BLUE))
    items.append(ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color=NEON_BLUE))
    return ft.Row(items, spacing=6)


def neon_button(
    text: str,
    icon: str = None,
    color: str = NEON_BLUE,
    on_click=None,
    width: int = None,
    height: int = 36,
    data=None,
) -> ft.ElevatedButton:
    """Create a styled neon button."""
    items = []
    if icon:
        items.append(ft.Icon(icon, size=16, color="white"))
    items.append(ft.Text(text, size=12, color="white", weight=ft.FontWeight.BOLD))

    return ft.ElevatedButton(
        content=ft.Row(items, spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(
            bgcolor=color,
            padding=ft.padding.symmetric(horizontal=12, vertical=4),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=on_click,
        width=width,
        height=height,
        data=data,
    )


def outline_button(
    text: str,
    icon: str = None,
    color: str = NEON_BLUE,
    on_click=None,
    width: int = None,
    height: int = 36,
    data=None,
) -> ft.OutlinedButton:
    """Create a styled outline button."""
    items = []
    if icon:
        items.append(ft.Icon(icon, size=14, color=color))
    items.append(ft.Text(text, size=11, color=color, weight=ft.FontWeight.W_500))

    return ft.OutlinedButton(
        content=ft.Row(items, spacing=4, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, color),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=on_click,
        width=width,
        height=height,
        data=data,
    )


def stat_row(label: str, value: str, color: str = TEXT_PRIMARY) -> ft.Row:
    """Create a label: value row for stats display."""
    return ft.Row([
        ft.Text(f"{label}:", size=12, color=TEXT_SECONDARY),
        ft.Text(value, size=12, color=color, weight=ft.FontWeight.W_500),
    ], spacing=6)
