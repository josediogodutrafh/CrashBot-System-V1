#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - GUI MODULE

Interface gráfica com DearPyGui.

Módulos:
- theme: Tema e estilos visuais
- components: Componentes reutilizáveis
- main_window: Janela principal

Uso:
    from ui.gui import MainWindow

    app = MainWindow()
    app.setup()
    app.run()
"""

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO DE DEPENDÊNCIA
# ═══════════════════════════════════════════════════════════════════════════════

try:
    import dearpygui.dearpygui as dpg

    HAS_DEARPYGUI = True
except ImportError:
    HAS_DEARPYGUI = False
    dpg = None

# ═══════════════════════════════════════════════════════════════════════════════
# THEME
# ═══════════════════════════════════════════════════════════════════════════════

from gui.components import (  # Stat cards; Status indicator; Progress bar; Explosion display; Log viewer; Dialogs; Helpers
    add_horizontal_space,
    add_log_line,
    add_tooltip,
    add_vertical_space,
    clear_log_viewer,
    create_explosion_display,
    create_explosion_history,
    create_log_viewer,
    create_modal,
    create_progress_bar,
    create_section_header,
    create_stat_card,
    create_status_indicator,
    show_confirm_dialog,
    show_info_dialog,
    update_explosion_display,
    update_explosion_history,
    update_progress_bar,
    update_stat_card,
    update_status_indicator,
)
from gui.main_window import MainWindow
from gui.theme import (
    Colors,
    FontSizes,
    Spacing,
    apply_theme,
    create_card_theme,
    create_danger_button_theme,
    create_panel_theme,
    create_secondary_button_theme,
    create_success_button_theme,
    create_warning_button_theme,
    get_status_color,
    setup_fonts,
)

# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Flag
    "HAS_DEARPYGUI",
    # Theme
    "Colors",
    "Spacing",
    "FontSizes",
    "apply_theme",
    "create_success_button_theme",
    "create_danger_button_theme",
    "create_warning_button_theme",
    "create_secondary_button_theme",
    "create_panel_theme",
    "create_card_theme",
    "setup_fonts",
    "get_status_color",
    # Components
    "create_stat_card",
    "update_stat_card",
    "create_status_indicator",
    "update_status_indicator",
    "create_progress_bar",
    "update_progress_bar",
    "create_explosion_display",
    "update_explosion_display",
    "create_explosion_history",
    "update_explosion_history",
    "create_log_viewer",
    "add_log_line",
    "clear_log_viewer",
    "create_modal",
    "show_confirm_dialog",
    "show_info_dialog",
    "add_tooltip",
    "create_section_header",
    "add_vertical_space",
    "add_horizontal_space",
    # Main Window
    "MainWindow",
]


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK START
# ═══════════════════════════════════════════════════════════════════════════════


def run_gui() -> None:
    """
    Função de conveniência para iniciar a GUI.

    Uso:
        from ui.gui import run_gui
        run_gui()
    """
    if not HAS_DEARPYGUI:
        raise ImportError(
            "DearPyGui não encontrado. " "Instale com: pip install dearpygui"
        )

    app = MainWindow()
    app.setup()
    app.run()
