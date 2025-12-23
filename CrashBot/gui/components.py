#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - GUI COMPONENTS

Componentes reutilizáveis para a interface.

Uso:
    from gui.components import (
        create_stat_card,
        create_progress_ring,
        create_status_indicator,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# DearPyGui
# ... imports anteriores ...

# CORREÇÃO AQUI:
try:
    import dearpygui.dearpygui as dpg
except ImportError:
    # Se falhar, paramos o script aqui mesmo.
    # Assim o Pylance entende que dpg nunca será None nas linhas abaixo.
    raise ImportError(
        "A biblioteca DearPyGui não foi encontrada. "
        "Instale com: pip install dearpygui"
    ) from None

# Local imports
from gui.theme import Colors, Spacing

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# TYPE ALIASES
# ═══════════════════════════════════════════════════════════════════════════════

ItemID = Union[int, str]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER - Verifica se DPG está disponível
# ═══════════════════════════════════════════════════════════════════════════════


def _require_dpg() -> None:
    """Verifica se DearPyGui está disponível."""
    if dpg is None:
        raise ImportError(
            "DearPyGui não está instalado. Instale com: pip install dearpygui"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STAT CARD
# ═══════════════════════════════════════════════════════════════════════════════


def create_stat_card(
    parent: ItemID,
    label: str,
    value: str,
    sublabel: str = "",
    color: Tuple[int, int, int, int] = Colors.PRIMARY,
    width: int = 150,
    height: int = 80,
) -> Dict[str, ItemID]:
    """
    Cria um card de estatística.

    Args:
        parent: ID do container pai
        label: Título do card
        value: Valor principal
        sublabel: Texto secundário
        color: Cor do valor
        width: Largura
        height: Altura

    Returns:
        Dicionário com IDs dos elementos
    """
    _require_dpg()

    ids: Dict[str, ItemID] = {}

    with dpg.child_window(
        parent=parent, width=width, height=height, border=True
    ) as card:
        ids["card"] = card
        ids["label"] = dpg.add_text(label, color=Colors.TEXT_SECONDARY)
        ids["value"] = dpg.add_text(value, color=color)

        if sublabel:
            ids["sublabel"] = dpg.add_text(sublabel, color=Colors.TEXT_MUTED)

    return ids


def update_stat_card(
    ids: Dict[str, ItemID],
    value: Optional[str] = None,
    sublabel: Optional[str] = None,
    color: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    """Atualiza valores de um stat card."""
    _require_dpg()

    if value is not None and "value" in ids:
        dpg.set_value(ids["value"], value)
    if sublabel is not None and "sublabel" in ids:
        dpg.set_value(ids["sublabel"], sublabel)
    if color is not None and "value" in ids:
        dpg.configure_item(ids["value"], color=color)


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS INDICATOR
# ═══════════════════════════════════════════════════════════════════════════════


def create_status_indicator(
    parent: ItemID,
    label: str,
    status: str = "inactive",
) -> Dict[str, ItemID]:
    """
    Cria indicador de status com bolinha colorida.

    Args:
        parent: ID do container pai
        label: Texto do status
        status: "active", "inactive", "warning", "error"

    Returns:
        Dicionário com IDs
    """
    _require_dpg()

    ids: Dict[str, ItemID] = {}

    status_colors = {
        "active": Colors.SUCCESS,
        "inactive": Colors.TEXT_MUTED,
        "warning": Colors.WARNING,
        "error": Colors.DANGER,
        "running": Colors.PRIMARY,
    }

    color = status_colors.get(status, Colors.TEXT_MUTED)

    with dpg.group(parent=parent, horizontal=True) as group:
        ids["group"] = group

        with dpg.drawlist(width=12, height=12) as drawlist:
            ids["drawlist"] = drawlist
            ids["circle"] = dpg.draw_circle(
                center=(6, 6),
                radius=5,
                color=color,
                fill=color,
            )

        ids["label"] = dpg.add_text(label, color=Colors.TEXT_SECONDARY)

    return ids


def update_status_indicator(
    ids: Dict[str, ItemID],
    status: str,
    label: Optional[str] = None,
) -> None:
    """Atualiza indicador de status."""
    _require_dpg()

    status_colors = {
        "active": Colors.SUCCESS,
        "inactive": Colors.TEXT_MUTED,
        "warning": Colors.WARNING,
        "error": Colors.DANGER,
        "running": Colors.PRIMARY,
    }

    color = status_colors.get(status, Colors.TEXT_MUTED)

    if "circle" in ids:
        dpg.configure_item(ids["circle"], color=color, fill=color)

    if label is not None and "label" in ids:
        dpg.set_value(ids["label"], label)


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS BAR
# ═══════════════════════════════════════════════════════════════════════════════


def create_progress_bar(
    parent: ItemID,
    label: str = "",
    value: float = 0.0,
    width: int = -1,
    color: Tuple[int, int, int, int] = Colors.PRIMARY,
    show_percentage: bool = True,
) -> Dict[str, ItemID]:
    """
    Cria barra de progresso customizada.

    Args:
        parent: ID do container pai
        label: Texto da label
        value: Valor inicial (0.0 - 1.0)
        width: Largura (-1 para auto)
        color: Cor da barra
        show_percentage: Se mostra percentual

    Returns:
        Dicionário com IDs
    """
    _require_dpg()

    ids: Dict[str, ItemID] = {}

    with dpg.group(parent=parent) as group:
        ids["group"] = group

        if label:
            with dpg.group(horizontal=True):
                ids["label"] = dpg.add_text(label, color=Colors.TEXT_SECONDARY)
                if show_percentage:
                    dpg.add_spacer(width=-1)
                    ids["percentage"] = dpg.add_text(
                        f"{value * 100:.0f}%",
                        color=Colors.TEXT_MUTED,
                    )

        ids["progress"] = dpg.add_progress_bar(
            default_value=value,
            width=width,
        )

    return ids


def update_progress_bar(
    ids: Dict[str, ItemID],
    value: float,
    color: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    """Atualiza barra de progresso."""
    _require_dpg()

    if "progress" in ids:
        dpg.set_value(ids["progress"], value)

    if "percentage" in ids:
        dpg.set_value(ids["percentage"], f"{value * 100:.0f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLOSION DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════


def create_explosion_display(
    parent: ItemID,
    value: float = 0.0,
    size: str = "large",
) -> Dict[str, ItemID]:
    """
    Cria display de explosão com cor dinâmica.

    Args:
        parent: ID do container pai
        value: Valor da explosão
        size: "small", "medium", "large"

    Returns:
        Dicionário com IDs
    """
    _require_dpg()

    ids: Dict[str, ItemID] = {}

    # Determina cor
    if value < 1.5:
        color = Colors.DANGER
    elif value < 2.0:
        color = Colors.WARNING
    else:
        color = Colors.SUCCESS

    with dpg.group(parent=parent) as group:
        ids["group"] = group
        ids["value"] = dpg.add_text(
            f"{value:.2f}x",
            color=color,
        )

    return ids


def update_explosion_display(ids: Dict[str, ItemID], value: float) -> None:
    """Atualiza display de explosão."""
    _require_dpg()

    # Determina cor
    if value < 1.5:
        color = Colors.DANGER
    elif value < 2.0:
        color = Colors.WARNING
    else:
        color = Colors.SUCCESS

    if "value" in ids:
        dpg.set_value(ids["value"], f"{value:.2f}x")
        dpg.configure_item(ids["value"], color=color)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLOSION HISTORY
# ═══════════════════════════════════════════════════════════════════════════════


def create_explosion_history(
    parent: ItemID,
    explosions: Optional[List[float]] = None,
    max_display: int = 20,
) -> Dict[str, Any]:
    """
    Cria histórico visual de explosões.

    Args:
        parent: ID do container pai
        explosions: Lista de explosões
        max_display: Máximo de itens exibidos

    Returns:
        Dicionário com IDs e dados
    """
    _require_dpg()

    ids: Dict[str, Any] = {"items": [], "max_display": max_display}

    if explosions is None:
        explosions = []

    with dpg.group(parent=parent, horizontal=True) as group:
        ids["group"] = group

        for value in explosions[-max_display:]:
            item_id = _create_explosion_chip(group, value)
            ids["items"].append(item_id)

    return ids


def _create_explosion_chip(parent: ItemID, value: float) -> ItemID:
    """Cria chip de explosão."""
    _require_dpg()

    # Cor baseada no valor
    if value < 1.5:
        bg_color = Colors.DANGER_DARK
        text_color = Colors.TEXT_PRIMARY
    elif value < 2.0:
        bg_color = Colors.WARNING_DARK
        text_color = Colors.BG_DARK
    else:
        bg_color = Colors.SUCCESS_DARK
        text_color = Colors.TEXT_PRIMARY

    # Cria botão como chip
    chip_id = dpg.add_button(
        label=f"{value:.2f}",
        parent=parent,
        width=50,
        height=25,
        enabled=False,
    )

    # Aplica tema de cor
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg_color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_color)
            dpg.add_theme_color(dpg.mvThemeCol_Text, text_color)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 12)

    dpg.bind_item_theme(chip_id, theme)

    return chip_id


def update_explosion_history(
    ids: Dict[str, Any],
    explosions: List[float],
) -> None:
    """Atualiza histórico de explosões."""
    _require_dpg()

    # Remove itens antigos
    for item_id in ids["items"]:
        if dpg.does_item_exist(item_id):
            dpg.delete_item(item_id)

    ids["items"].clear()

    # Adiciona novos
    max_display = ids.get("max_display", 20)
    for value in explosions[-max_display:]:
        item_id = _create_explosion_chip(ids["group"], value)
        ids["items"].append(item_id)


# ═══════════════════════════════════════════════════════════════════════════════
# LOG VIEWER
# ═══════════════════════════════════════════════════════════════════════════════


def create_log_viewer(
    parent: ItemID,
    height: int = 200,
    max_lines: int = 100,
) -> Dict[str, Any]:
    """
    Cria visualizador de logs.

    Args:
        parent: ID do container pai
        height: Altura do viewer
        max_lines: Máximo de linhas

    Returns:
        Dicionário com IDs e funções
    """
    _require_dpg()

    ids: Dict[str, Any] = {"lines": [], "max_lines": max_lines}

    with dpg.child_window(parent=parent, height=height, border=True) as window:
        ids["window"] = window
        ids["text_group"] = dpg.add_group()

    return ids


def add_log_line(
    ids: Dict[str, Any],
    message: str,
    level: str = "info",
) -> None:
    """
    Adiciona linha ao log viewer.

    Args:
        ids: IDs do log viewer
        message: Mensagem
        level: "info", "warning", "error", "success", "debug"
    """
    _require_dpg()

    level_colors = {
        "info": Colors.TEXT_PRIMARY,
        "warning": Colors.WARNING,
        "error": Colors.DANGER,
        "success": Colors.SUCCESS,
        "debug": Colors.TEXT_MUTED,
    }

    color = level_colors.get(level, Colors.TEXT_PRIMARY)

    # Remove linhas antigas se necessário
    max_lines = ids.get("max_lines", 100)
    while len(ids["lines"]) >= max_lines:
        old_id = ids["lines"].pop(0)
        if dpg.does_item_exist(old_id):
            dpg.delete_item(old_id)

    # Adiciona nova linha
    from datetime import datetime

    timestamp = datetime.now().strftime("%H:%M:%S")
    full_message = f"[{timestamp}] {message}"

    line_id = dpg.add_text(
        full_message,
        parent=ids["text_group"],
        color=color,
    )
    ids["lines"].append(line_id)

    # Scroll para baixo
    dpg.set_y_scroll(ids["window"], dpg.get_y_scroll_max(ids["window"]))


def clear_log_viewer(ids: Dict[str, Any]) -> None:
    """Limpa log viewer."""
    _require_dpg()

    for line_id in ids["lines"]:
        if dpg.does_item_exist(line_id):
            dpg.delete_item(line_id)
    ids["lines"].clear()


# ═══════════════════════════════════════════════════════════════════════════════
# MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════


def create_modal(
    title: str,
    message: str,
    buttons: Optional[List[Tuple[str, Callable[[], Any]]]] = None,
    width: int = 400,
    height: int = 150,
) -> ItemID:
    """
    Cria modal dialog.

    Args:
        title: Título do modal
        message: Mensagem
        buttons: Lista de (label, callback)
        width: Largura
        height: Altura

    Returns:
        ID do modal
    """
    _require_dpg()

    if buttons is None:
        buttons = [("OK", lambda: None)]

    with dpg.window(
        label=title,
        modal=True,
        no_close=True,
        no_resize=True,
        width=width,
        height=height,
    ) as modal:
        dpg.add_text(message, wrap=width - 40)
        dpg.add_spacer(height=20)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=-1)
            for btn_label, callback in buttons:

                def make_callback(
                    cb: Callable[[], Any], m: ItemID = modal
                ) -> Callable[[], None]:
                    def wrapper() -> None:
                        cb()
                        dpg.delete_item(m)

                    return wrapper

                dpg.add_button(
                    label=btn_label,
                    callback=make_callback(callback, modal),
                    width=80,
                )

    # Centraliza
    dpg.split_frame()
    viewport_width = dpg.get_viewport_client_width()
    viewport_height = dpg.get_viewport_client_height()
    dpg.set_item_pos(
        modal,
        [(viewport_width - width) // 2, (viewport_height - height) // 2],
    )

    return modal


def show_confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable[[], Any],
    on_cancel: Optional[Callable[[], Any]] = None,
) -> ItemID:
    """Mostra diálogo de confirmação."""
    buttons: List[Tuple[str, Callable[[], Any]]] = [
        ("Cancelar", on_cancel or (lambda: None)),
        ("Confirmar", on_confirm),
    ]
    return create_modal(title, message, buttons)


def show_info_dialog(title: str, message: str) -> ItemID:
    """Mostra diálogo informativo."""
    return create_modal(title, message, [("OK", lambda: None)])


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLTIP
# ═══════════════════════════════════════════════════════════════════════════════


def add_tooltip(item: ItemID, text: str) -> ItemID:
    """
    Adiciona tooltip a um item.

    Args:
        item: ID do item
        text: Texto do tooltip

    Returns:
        ID do tooltip
    """
    _require_dpg()

    with dpg.tooltip(parent=item) as tooltip:
        dpg.add_text(text, color=Colors.TEXT_SECONDARY)
    return tooltip


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION HEADER
# ═══════════════════════════════════════════════════════════════════════════════


def create_section_header(
    parent: ItemID,
    title: str,
    collapsible: bool = False,
) -> ItemID:
    """
    Cria cabeçalho de seção.

    Args:
        parent: ID do container pai
        title: Título da seção
        collapsible: Se pode colapsar

    Returns:
        ID do header ou grupo
    """
    _require_dpg()

    if collapsible:
        return dpg.add_collapsing_header(
            label=title,
            parent=parent,
            default_open=True,
        )

    with dpg.group(parent=parent) as group:
        dpg.add_text(title, color=Colors.TEXT_SECONDARY)
        dpg.add_separator()
    return group


# ═══════════════════════════════════════════════════════════════════════════════
# SPACER
# ═══════════════════════════════════════════════════════════════════════════════


def add_vertical_space(parent: ItemID, height: int = Spacing.MD) -> ItemID:
    """Adiciona espaço vertical."""
    _require_dpg()
    return dpg.add_spacer(parent=parent, height=height)


def add_horizontal_space(parent: ItemID, width: int = Spacing.MD) -> ItemID:
    """Adiciona espaço horizontal."""
    _require_dpg()
    return dpg.add_spacer(parent=parent, width=width)
