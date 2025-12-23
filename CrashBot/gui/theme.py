#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

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

    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvAll):
            # ─────────────────────────────────────────────────────────────────
            # Cores de fundo
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, Colors.BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Colors.BG_MEDIUM)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, Colors.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, Colors.BG_MEDIUM)

            # ─────────────────────────────────────────────────────────────────
            # Frames e painéis
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, Colors.BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, Colors.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, Colors.PRIMARY_ACTIVE)

            # ─────────────────────────────────────────────────────────────────
            # Títulos
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, Colors.BG_MEDIUM)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, Colors.PRIMARY_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, Colors.BG_DARK)

            # ─────────────────────────────────────────────────────────────────
            # Botões
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_Button, Colors.PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Colors.PRIMARY_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, Colors.PRIMARY_ACTIVE)

            # ─────────────────────────────────────────────────────────────────
            # Headers
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_Header, Colors.BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, Colors.PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, Colors.PRIMARY_ACTIVE)

            # ─────────────────────────────────────────────────────────────────
            # Tabs
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_Tab, Colors.BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, Colors.PRIMARY_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, Colors.PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, Colors.BG_MEDIUM)
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, Colors.BG_LIGHT)

            # ─────────────────────────────────────────────────────────────────
            # Texto
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_Text, Colors.TEXT_PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, Colors.TEXT_DISABLED)

            # ─────────────────────────────────────────────────────────────────
            # Checkboxes e sliders
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, Colors.PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, Colors.PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, Colors.PRIMARY_HOVER)

            # ─────────────────────────────────────────────────────────────────
            # Scrollbar
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, Colors.BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, Colors.BG_PANEL)
            dpg.add_theme_color(
                dpg.mvThemeCol_ScrollbarGrabHovered, Colors.BORDER_LIGHT
            )
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, Colors.PRIMARY)

            # ─────────────────────────────────────────────────────────────────
            # Separadores e bordas
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_Separator, Colors.BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_Border, Colors.BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))

            # ─────────────────────────────────────────────────────────────────
            # Plots
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, Colors.BG_MEDIUM)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, Colors.BG_DARK)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, Colors.BORDER)
            dpg.add_theme_color(dpg.mvPlotCol_Line, Colors.PRIMARY)

            # ─────────────────────────────────────────────────────────────────
            # Estilos
            # ─────────────────────────────────────────────────────────────────
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4)

            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, Spacing.MD, Spacing.MD)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, Spacing.SM, Spacing.SM)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, Spacing.SM, Spacing.SM)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, Spacing.SM, Spacing.SM)

            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)

    dpg.bind_theme(theme_id)
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
    if hover is None:
        hover = tuple(min(c + 30, 255) for c in color[:3]) + (color[3],)
    if active is None:
        active = tuple(max(c - 20, 0) for c in color[:3]) + (color[3],)

    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hover)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, active)

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
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Colors.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Border, Colors.BORDER)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)

    return theme_id


def create_card_theme() -> int:
    """Cria tema para cards."""
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Colors.BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_Border, Colors.BORDER_LIGHT)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 10)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, Spacing.LG, Spacing.LG)

    return theme_id


def create_input_theme() -> int:
    """Cria tema para inputs."""
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvInputText):
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, Colors.BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, Colors.BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, Colors.BG_LIGHT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, Spacing.MD, Spacing.SM)

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

    with dpg.font_registry() as font_reg:
        # Fonte padrão
        if font_path:
            try:
                dpg.add_font(font_path, FontSizes.NORMAL)
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
