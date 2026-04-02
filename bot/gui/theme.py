#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false

"""
CRASHBOT v3.0 - GUI THEME

Tema e estilos para a interface DearPyGui.
Design moderno inspirado em interfaces de trading.

Uso:
    from gui.theme import apply_theme, Colors

    apply_theme()
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

# DearPyGui
try:
    import dearpygui.dearpygui as dpg

    HAS_DPG = True
except ImportError:
    HAS_DPG = False
    dpg = None

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CORES
# ═══════════════════════════════════════════════════════════════════════════════


class Colors:
    """Paleta de cores do CrashBot."""

    # Background
    BG_DARK = (15, 15, 20, 255)
    BG_MEDIUM = (25, 25, 35, 255)
    BG_LIGHT = (35, 35, 50, 255)
    BG_PANEL = (40, 40, 55, 255)

    # Accent
    PRIMARY = (0, 150, 255, 255)  # Azul principal
    PRIMARY_HOVER = (30, 170, 255, 255)
    PRIMARY_ACTIVE = (0, 120, 220, 255)

    SECONDARY = (120, 80, 255, 255)  # Roxo
    SECONDARY_HOVER = (140, 100, 255, 255)

    # Status
    SUCCESS = (0, 200, 100, 255)  # Verde
    SUCCESS_DARK = (0, 150, 75, 255)

    WARNING = (255, 180, 0, 255)  # Amarelo
    WARNING_DARK = (200, 140, 0, 255)

    DANGER = (255, 70, 70, 255)  # Vermelho
    DANGER_DARK = (200, 50, 50, 255)

    # Texto
    TEXT_PRIMARY = (240, 240, 245, 255)
    TEXT_SECONDARY = (160, 160, 175, 255)
    TEXT_MUTED = (100, 100, 115, 255)
    TEXT_DISABLED = (70, 70, 85, 255)

    # Gráficos
    CHART_GREEN = (0, 230, 118, 255)
    CHART_RED = (255, 82, 82, 255)
    CHART_BLUE = (66, 165, 245, 255)
    CHART_YELLOW = (255, 213, 79, 255)
    CHART_PURPLE = (186, 104, 200, 255)

    # Borders
    BORDER = (60, 60, 80, 255)
    BORDER_LIGHT = (80, 80, 100, 255)

    # Especiais
    GOLD = (255, 215, 0, 255)
    SILVER = (192, 192, 192, 255)


# ═══════════════════════════════════════════════════════════════════════════════
# FONTES
# ═══════════════════════════════════════════════════════════════════════════════


class FontSizes:
    """Tamanhos de fonte."""

    SMALL = 13
    NORMAL = 15
    MEDIUM = 17
    LARGE = 20
    XLARGE = 24
    TITLE = 28
    HEADER = 32


# ═══════════════════════════════════════════════════════════════════════════════
# ESPAÇAMENTOS
# ═══════════════════════════════════════════════════════════════════════════════


class Spacing:
    """Espaçamentos padrão."""

    NONE = 0
    XS = 2
    SM = 5
    MD = 10
    LG = 15
    XL = 20
    XXL = 30


# ═══════════════════════════════════════════════════════════════════════════════
# APLICAR TEMA
# ═══════════════════════════════════════════════════════════════════════════════

_theme_id: Optional[int] = None
_font_registry: Optional[int] = None


def apply_theme() -> int:
    """
    Aplica o tema global do CrashBot.

    Returns:
        ID do tema criado
    """
    global _theme_id

    if not HAS_DPG:
        raise ImportError("DearPyGui não encontrado")

    with dpg.theme() as theme_id:  # type: ignore
        with dpg.theme_component(dpg.mvAll):  # type: ignore
            # ─────────────────────────────────────────────────────────────────
            # Cores de fundo
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_WindowBg, Colors.BG_DARK  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ChildBg, Colors.BG_MEDIUM  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_PopupBg, Colors.BG_PANEL  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_MenuBarBg, Colors.BG_MEDIUM  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Frames e painéis
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_FrameBg, Colors.BG_LIGHT  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_FrameBgHovered, Colors.BG_PANEL  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_FrameBgActive, Colors.PRIMARY_ACTIVE  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Títulos
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TitleBg, Colors.BG_MEDIUM  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TitleBgActive, Colors.PRIMARY_ACTIVE  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TitleBgCollapsed, Colors.BG_DARK  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Botões
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Button, Colors.PRIMARY  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ButtonHovered, Colors.PRIMARY_HOVER  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ButtonActive, Colors.PRIMARY_ACTIVE  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Headers
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Header, Colors.BG_LIGHT  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_HeaderHovered, Colors.PRIMARY  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_HeaderActive, Colors.PRIMARY_ACTIVE  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Tabs
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Tab, Colors.BG_LIGHT  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TabHovered, Colors.PRIMARY_HOVER  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TabActive, Colors.PRIMARY  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TabUnfocused, Colors.BG_MEDIUM  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TabUnfocusedActive, Colors.BG_LIGHT  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Texto
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Text, Colors.TEXT_PRIMARY  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_TextDisabled, Colors.TEXT_DISABLED  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Checkboxes e sliders
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_CheckMark, Colors.PRIMARY  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_SliderGrab, Colors.PRIMARY  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_SliderGrabActive, Colors.PRIMARY_HOVER  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Scrollbar
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ScrollbarBg, Colors.BG_DARK  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ScrollbarGrab, Colors.BG_PANEL  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ScrollbarGrabHovered, Colors.BORDER_LIGHT  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ScrollbarGrabActive, Colors.PRIMARY  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Separadores e bordas
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Separator, Colors.BORDER  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Border, Colors.BORDER  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0)  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Plots
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(  # type: ignore
                dpg.mvPlotCol_FrameBg, Colors.BG_MEDIUM  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvPlotCol_PlotBg, Colors.BG_DARK  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvPlotCol_PlotBorder, Colors.BORDER  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvPlotCol_Line, Colors.PRIMARY  # type: ignore
            )

            # ─────────────────────────────────────────────────────────────────
            # Estilos
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_WindowRounding, 8  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ChildRounding, 6  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_FrameRounding, 4  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_PopupRounding, 6  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ScrollbarRounding, 4  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_GrabRounding, 4  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_TabRounding, 4  # type: ignore
            )

            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_WindowPadding, Spacing.MD, Spacing.MD  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_FramePadding, Spacing.SM, Spacing.SM  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ItemSpacing, Spacing.SM, Spacing.SM  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ItemInnerSpacing, Spacing.SM, Spacing.SM  # type: ignore
            )

            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_WindowBorderSize, 1  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ChildBorderSize, 1  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_FrameBorderSize, 0  # type: ignore
            )

    dpg.bind_theme(theme_id)  # type: ignore
    _theme_id = theme_id

    logger.info("Tema aplicado com sucesso")
    return theme_id


def create_button_theme(
    color: Tuple[int, int, int, int],
    hover: Optional[Tuple[int, int, int, int]] = None,
    active: Optional[Tuple[int, int, int, int]] = None,
) -> int:
    """
    Cria tema para botão com cor customizada.

    Args:
        color: Cor base do botão
        hover: Cor ao passar mouse
        active: Cor ao clicar

    Returns:
        ID do tema
    """
    # Calcular cores hover e active usando 'or' para simplificar
    # Se 'hover' for None, executa o cálculo da tupla à direita.
    hover_color: Tuple[int, int, int, int] = hover or (
        min(color[0] + 30, 255),
        min(color[1] + 30, 255),
        min(color[2] + 30, 255),
        color[3],
    )

    # O mesmo para 'active'
    active_color: Tuple[int, int, int, int] = active or (
        max(color[0] - 20, 0),
        max(color[1] - 20, 0),
        max(color[2] - 20, 0),
        color[3],
    )

    with dpg.theme() as theme_id:  # type: ignore
        with dpg.theme_component(dpg.mvButton):  # type: ignore
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Button, color  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ButtonHovered, hover_color  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ButtonActive, active_color  # type: ignore
            )

    return theme_id


def create_success_button_theme() -> int:
    """Cria tema de botão verde (sucesso)."""
    return create_button_theme(Colors.SUCCESS, Colors.SUCCESS_DARK)


def create_danger_button_theme() -> int:
    """Cria tema de botão vermelho (perigo)."""
    return create_button_theme(Colors.DANGER, Colors.DANGER_DARK)


def create_warning_button_theme() -> int:
    """Cria tema de botão amarelo (aviso)."""
    return create_button_theme(Colors.WARNING, Colors.WARNING_DARK)


def create_secondary_button_theme() -> int:
    """Cria tema de botão secundário (roxo)."""
    return create_button_theme(Colors.SECONDARY, Colors.SECONDARY_HOVER)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMAS ESPECÍFICOS
# ═══════════════════════════════════════════════════════════════════════════════


def create_panel_theme() -> int:
    """Cria tema para painéis."""
    with dpg.theme() as theme_id:  # type: ignore
        with dpg.theme_component(dpg.mvChildWindow):  # type: ignore
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ChildBg, Colors.BG_PANEL  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Border, Colors.BORDER  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ChildRounding, 8  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ChildBorderSize, 1  # type: ignore
            )

    return theme_id


def create_card_theme() -> int:
    """Cria tema para cards."""
    with dpg.theme() as theme_id:  # type: ignore
        with dpg.theme_component(dpg.mvChildWindow):  # type: ignore
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_ChildBg, Colors.BG_LIGHT  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_Border, Colors.BORDER_LIGHT  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_ChildRounding, 10  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_WindowPadding, Spacing.LG, Spacing.LG  # type: ignore
            )

    return theme_id


def create_input_theme() -> int:
    """Cria tema para inputs."""
    with dpg.theme() as theme_id:  # type: ignore
        with dpg.theme_component(dpg.mvInputText):  # type: ignore
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_FrameBg, Colors.BG_DARK  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_FrameBgHovered, Colors.BG_LIGHT  # type: ignore
            )
            dpg.add_theme_color(  # type: ignore
                dpg.mvThemeCol_FrameBgActive, Colors.BG_LIGHT  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_FrameRounding, 6  # type: ignore
            )
            dpg.add_theme_style(  # type: ignore
                dpg.mvStyleVar_FramePadding, Spacing.MD, Spacing.SM  # type: ignore
            )

    return theme_id


# ═══════════════════════════════════════════════════════════════════════════════
# FONTES
# ═══════════════════════════════════════════════════════════════════════════════


def setup_fonts(font_path: Optional[str] = None) -> int:
    """
    Configura fontes do aplicativo.

    Args:
        font_path: Caminho para fonte TTF customizada

    Returns:
        ID do registro de fontes
    """
    global _font_registry

    with dpg.font_registry() as font_reg:  # type: ignore
        # Fonte padrão
        if font_path:
            try:
                dpg.add_font(font_path, FontSizes.NORMAL)  # type: ignore
                logger.info(f"Fonte carregada: {font_path}")
            except Exception as e:
                logger.warning(f"Erro ao carregar fonte: {e}")

    _font_registry = font_reg
    return font_reg


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def get_status_color(status: str) -> Tuple[int, int, int, int]:
    """
    Retorna cor baseada no status.

    Args:
        status: "success", "warning", "danger", "info"

    Returns:
        Tupla RGBA
    """
    colors = {
        "success": Colors.SUCCESS,
        "warning": Colors.WARNING,
        "danger": Colors.DANGER,
        "error": Colors.DANGER,
        "info": Colors.PRIMARY,
        "muted": Colors.TEXT_MUTED,
    }
    return colors.get(status.lower(), Colors.TEXT_PRIMARY)


def rgba_to_hex(color: Tuple[int, int, int, int]) -> str:
    """Converte RGBA para hex string."""
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
