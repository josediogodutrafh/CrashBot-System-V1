#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false

"""
CRASHBOT v3.0 - CALIBRATOR WINDOW

Interface gráfica principal do calibrador usando DearPyGui.
Design moderno e profissional estilo dashboard de trading.

Uso:
    from calibration.calibrator_window import CalibratorWindow, launch_calibrator

    # Método 1: Instanciar e mostrar
    calibrator = CalibratorWindow()
    calibrator.show()

    # Método 2: Função rápida
    launch_calibrator()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# DearPyGui
try:
    import dearpygui.dearpygui as dpg

    HAS_DPG = True
except ImportError:
    HAS_DPG = False
    dpg = None

from calibration.live_preview import (
    LivePreview,
    ReadingResult,
    ReadingStatus,
    get_live_preview,
)

# Imports internos
from calibration.profile_manager import (
    CalibrationProfile,
    ClickPoint,
    ColorConfig,
    ProfileManager,
    RegionConfig,
    get_profile_manager,
)
from calibration.region_selector import RegionSelector, SelectionMode, SelectionResult

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CORES DO TEMA
# ═══════════════════════════════════════════════════════════════════════════════


class Colors:
    """Paleta de cores do calibrador."""

    # Background
    BG_DARK = (15, 15, 20, 255)
    BG_MEDIUM = (25, 25, 35, 255)
    BG_LIGHT = (35, 35, 50, 255)
    BG_PANEL = (40, 40, 55, 255)

    # Accent
    PRIMARY = (0, 150, 255, 255)
    PRIMARY_HOVER = (30, 170, 255, 255)
    SECONDARY = (120, 80, 255, 255)

    # Status
    SUCCESS = (0, 200, 100, 255)
    WARNING = (255, 180, 0, 255)
    DANGER = (255, 70, 70, 255)

    # Texto
    TEXT_PRIMARY = (240, 240, 245, 255)
    TEXT_SECONDARY = (160, 160, 175, 255)
    TEXT_MUTED = (100, 100, 115, 255)

    # Borders
    BORDER = (60, 60, 80, 255)

    # Calibração
    REGION_BALANCE = (0, 200, 255, 255)  # Cyan
    REGION_TIMER = (255, 200, 0, 255)  # Amarelo
    REGION_HISTORY = (200, 100, 255, 255)  # Roxo
    REGION_BUTTON = (255, 100, 100, 255)  # Vermelho
    REGION_MULTIPLIER = (100, 255, 100, 255)  # Verde


# ═══════════════════════════════════════════════════════════════════════════════
# CALIBRATOR WINDOW
# ═══════════════════════════════════════════════════════════════════════════════


class CalibratorWindow:
    """
    Janela principal do calibrador.

    Interface profissional para configurar regiões de captura
    e pontos de clique do bot.

    Exemplo:
        calibrator = CalibratorWindow()
        calibrator.show()
    """

    # Dimensões da janela
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800

    # IDs dos elementos (para referência)
    TAG_MAIN_WINDOW = "calibrator_main"
    TAG_PROFILE_COMBO = "profile_combo"
    TAG_STATUS_TEXT = "status_text"
    TAG_PREVIEW_IMAGE = "preview_image"
    TAG_READINGS_GROUP = "readings_group"

    def __init__(self):
        """Inicializa o calibrador."""
        self._profile_manager = get_profile_manager()
        self._live_preview = get_live_preview()
        self._region_selector = RegionSelector()

        # Estado atual
        self._current_profile: Optional[CalibrationProfile] = None
        self._is_running = False
        self._preview_thread: Optional[threading.Thread] = None
        self._stop_preview = threading.Event()

        # IDs dos elementos de leitura
        self._reading_elements: Dict[str, int] = {}

        # Texturas para preview
        self._preview_texture_id: Optional[int] = None

        logger.debug("CalibratorWindow inicializado")

    # ═══════════════════════════════════════════════════════════════════════════
    # SETUP DA UI
    # ═══════════════════════════════════════════════════════════════════════════

    def show(self) -> None:
        """Mostra a janela do calibrador."""
        if not HAS_DPG:
            logger.error("DearPyGui não disponível")
            return

        try:
            # Inicializa DPG
            dpg.create_context()  # type: ignore

            # Aplica tema
            self._apply_theme()

            # Cria viewport
            dpg.create_viewport(  # type: ignore
                title="🎯 CrashBot - Calibrador v3.0",
                width=self.WINDOW_WIDTH,
                height=self.WINDOW_HEIGHT,
                resizable=True,
                vsync=True,
            )

            # Cria janela principal
            self._create_main_window()

            # Setup e loop
            dpg.setup_dearpygui()  # type: ignore
            dpg.show_viewport()  # type: ignore

            # Carrega perfis disponíveis
            self._refresh_profiles()

            # Inicia preview
            self._start_preview_thread()

            self._is_running = True
            dpg.start_dearpygui()  # type: ignore

        except Exception as e:
            logger.error(f"Erro ao mostrar calibrador: {e}")
            raise
        finally:
            self._cleanup()

    def _apply_theme(self) -> None:
        """Aplica o tema visual."""
        with dpg.theme() as theme:  # type: ignore
            with dpg.theme_component(dpg.mvAll):  # type: ignore
                # Cores de fundo
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_WindowBg, Colors.BG_DARK  # type: ignore
                )
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_ChildBg, Colors.BG_MEDIUM  # type: ignore
                )
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_FrameBg, Colors.BG_LIGHT  # type: ignore
                )
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_FrameBgHovered, Colors.BG_PANEL  # type: ignore
                )

                # Botões
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_Button, Colors.PRIMARY  # type: ignore
                )
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_ButtonHovered, Colors.PRIMARY_HOVER  # type: ignore
                )

                # Texto
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_Text, Colors.TEXT_PRIMARY  # type: ignore
                )

                # Bordas
                dpg.add_theme_color(  # type: ignore
                    dpg.mvThemeCol_Border, Colors.BORDER  # type: ignore
                )

                # Estilos
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
                    dpg.mvStyleVar_WindowPadding, 10, 10  # type: ignore
                )

        dpg.bind_theme(theme)  # type: ignore

    def _create_main_window(self) -> None:
        """Cria a janela principal."""
        with dpg.window(  # type: ignore
            tag=self.TAG_MAIN_WINDOW,
            label="Calibrador",
            no_title_bar=True,
            no_move=True,
            no_resize=True,
            no_collapse=True,
        ):
            # Handler de resize
            dpg.set_primary_window(self.TAG_MAIN_WINDOW, True)  # type: ignore

            # ═══════════════════════════════════════════════════════════════════
            # HEADER
            # ═══════════════════════════════════════════════════════════════════

            with dpg.group(horizontal=True):  # type: ignore
                dpg.add_text(  # type: ignore
                    "🎯 CALIBRADOR",
                    color=Colors.PRIMARY,
                )
                dpg.add_text(  # type: ignore
                    " CRASHBOT v3.0",
                    color=Colors.TEXT_SECONDARY,
                )

                dpg.add_spacer(width=20)  # type: ignore

                dpg.add_text(  # type: ignore
                    "Status:",
                    color=Colors.TEXT_MUTED,
                )
                dpg.add_text(  # type: ignore
                    "Aguardando...",
                    tag=self.TAG_STATUS_TEXT,
                    color=Colors.TEXT_SECONDARY,
                )

            dpg.add_separator()  # type: ignore
            dpg.add_spacer(height=10)  # type: ignore

            # ═══════════════════════════════════════════════════════════════════
            # LAYOUT PRINCIPAL (3 colunas)
            # ═══════════════════════════════════════════════════════════════════

            with dpg.group(horizontal=True):  # type: ignore

                # ───────────────────────────────────────────────────────────────
                # COLUNA ESQUERDA - Perfil e Regiões
                # ───────────────────────────────────────────────────────────────

                with dpg.child_window(  # type: ignore
                    width=280,
                    height=-60,
                    border=True,
                ):
                    self._create_profile_section()
                    dpg.add_spacer(height=15)  # type: ignore
                    self._create_regions_section()
                    dpg.add_spacer(height=15)  # type: ignore
                    self._create_clicks_section()

                dpg.add_spacer(width=10)  # type: ignore

                # ───────────────────────────────────────────────────────────────
                # COLUNA CENTRAL - Preview
                # ───────────────────────────────────────────────────────────────

                with dpg.child_window(  # type: ignore
                    width=-300,
                    height=-60,
                    border=True,
                ):
                    self._create_preview_section()

                dpg.add_spacer(width=10)  # type: ignore

                # ───────────────────────────────────────────────────────────────
                # COLUNA DIREITA - Leituras em tempo real
                # ───────────────────────────────────────────────────────────────

                with dpg.child_window(  # type: ignore
                    width=280,
                    height=-60,
                    border=True,
                ):
                    self._create_readings_section()

            dpg.add_spacer(height=10)  # type: ignore

            # ═══════════════════════════════════════════════════════════════════
            # FOOTER - Botões de ação
            # ═══════════════════════════════════════════════════════════════════

            with dpg.group(horizontal=True):  # type: ignore
                dpg.add_button(  # type: ignore
                    label="🎯 Calibrar Região",
                    callback=self._on_calibrate_region,
                    width=150,
                )

                dpg.add_button(  # type: ignore
                    label="📍 Calibrar Clique",
                    callback=self._on_calibrate_click,
                    width=150,
                )

                dpg.add_spacer(width=20)  # type: ignore

                dpg.add_button(  # type: ignore
                    label="🔄 Testar Tudo",
                    callback=self._on_test_all,
                    width=120,
                )

                dpg.add_spacer(width=20)  # type: ignore

                dpg.add_button(  # type: ignore
                    label="💾 Salvar",
                    callback=self._on_save_profile,
                    width=100,
                )

                dpg.add_button(  # type: ignore
                    label="↩️ Resetar",
                    callback=self._on_reset_profile,
                    width=100,
                )

                dpg.add_spacer()  # type: ignore

                dpg.add_text(  # type: ignore
                    "v3.0.0",
                    color=Colors.TEXT_MUTED,
                )

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÕES DA UI
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_profile_section(self) -> None:
        """Cria seção de gerenciamento de perfil."""
        dpg.add_text(  # type: ignore
            "📁 PERFIL",
            color=Colors.PRIMARY,
        )
        dpg.add_separator()  # type: ignore
        dpg.add_spacer(height=5)  # type: ignore

        # Combo de perfis
        dpg.add_combo(  # type: ignore
            tag=self.TAG_PROFILE_COMBO,
            items=[],
            default_value="",
            callback=self._on_profile_selected,
            width=-1,
        )

        dpg.add_spacer(height=5)  # type: ignore

        with dpg.group(horizontal=True):  # type: ignore
            dpg.add_button(  # type: ignore
                label="Novo",
                callback=self._on_new_profile,
                width=80,
            )
            dpg.add_button(  # type: ignore
                label="Duplicar",
                callback=self._on_duplicate_profile,
                width=80,
            )
            dpg.add_button(  # type: ignore
                label="Excluir",
                callback=self._on_delete_profile,
                width=80,
            )

        dpg.add_spacer(height=10)  # type: ignore

        # Info do perfil
        dpg.add_text(  # type: ignore
            "Plataforma:",
            color=Colors.TEXT_MUTED,
        )
        dpg.add_combo(  # type: ignore
            items=["Brabet", "OneBra", "WinBra", "PGWin"],
            default_value="Brabet",
            tag="profile_platform",
            width=-1,
        )

        dpg.add_text(  # type: ignore
            "Completude:",
            color=Colors.TEXT_MUTED,
        )

        with dpg.group(horizontal=True):  # type: ignore
            dpg.add_progress_bar(  # type: ignore
                tag="profile_progress",
                default_value=0.0,
                width=150,
            )
            dpg.add_text(  # type: ignore
                "0%",
                tag="profile_progress_text",
                color=Colors.TEXT_SECONDARY,
            )

    def _create_regions_section(self) -> None:
        """Cria seção de regiões de captura."""
        dpg.add_text(  # type: ignore
            "📐 REGIÕES DE CAPTURA",
            color=Colors.PRIMARY,
        )
        dpg.add_separator()  # type: ignore
        dpg.add_spacer(height=5)  # type: ignore

        # Lista de regiões
        regions = [
            ("balance", "💰 Saldo", Colors.REGION_BALANCE),
            ("timer", "⏱️ Timer", Colors.REGION_TIMER),
            ("history", "📊 Histórico", Colors.REGION_HISTORY),
            ("multiplier", "🎯 Multiplicador", Colors.REGION_MULTIPLIER),
            ("bet_button", "🔘 Botão Aposta", Colors.REGION_BUTTON),
        ]

        for region_id, label, color in regions:
            with dpg.group(horizontal=True):  # type: ignore
                dpg.add_text(  # type: ignore
                    "⬜",
                    tag=f"region_status_{region_id}",
                )
                dpg.add_text(  # type: ignore
                    label,
                    color=color[:3] + (255,),
                )
                dpg.add_spacer()  # type: ignore
                dpg.add_button(  # type: ignore
                    label="📐",
                    callback=lambda s, a, u: self._calibrate_specific_region(u),
                    user_data=region_id,
                    width=30,
                )

    def _create_clicks_section(self) -> None:
        """Cria seção de pontos de clique."""
        dpg.add_text(  # type: ignore
            "📍 PONTOS DE CLIQUE",
            color=Colors.PRIMARY,
        )
        dpg.add_separator()  # type: ignore
        dpg.add_spacer(height=5)  # type: ignore

        # Lista de pontos
        clicks = [
            ("bet_value_1", "💵 Campo Valor 1"),
            ("target_1", "🎯 Campo Multi 1"),
            ("bet_button_1", "🔘 Botão Bet 1"),
            ("bet_value_2", "💵 Campo Valor 2"),
            ("target_2", "🎯 Campo Multi 2"),
            ("bet_button_2", "🔘 Botão Bet 2"),
        ]

        for click_id, label in clicks:
            with dpg.group(horizontal=True):  # type: ignore
                dpg.add_text(  # type: ignore
                    "⬜",
                    tag=f"click_status_{click_id}",
                )
                dpg.add_text(  # type: ignore
                    label,
                    color=Colors.TEXT_SECONDARY,
                )
                dpg.add_spacer()  # type: ignore
                dpg.add_button(  # type: ignore
                    label="📍",
                    callback=lambda s, a, u: self._calibrate_specific_click(u),
                    user_data=click_id,
                    width=30,
                )

    def _create_preview_section(self) -> None:
        """Cria seção de preview da tela."""
        dpg.add_text(  # type: ignore
            "🖥️ PREVIEW DA TELA",
            color=Colors.PRIMARY,
        )
        dpg.add_separator()  # type: ignore
        dpg.add_spacer(height=5)  # type: ignore

        dpg.add_text(  # type: ignore
            "Preview com regiões marcadas aparecerá aqui",
            tag="preview_placeholder",
            color=Colors.TEXT_MUTED,
        )

        # Área para imagem de preview
        with dpg.drawlist(  # type: ignore
            tag="preview_drawlist",
            width=580,
            height=400,
        ):
            pass

        dpg.add_spacer(height=10)  # type: ignore

        with dpg.group(horizontal=True):  # type: ignore
            dpg.add_text(  # type: ignore
                "Última atualização:",
                color=Colors.TEXT_MUTED,
            )
            dpg.add_text(  # type: ignore
                "--:--:--",
                tag="preview_timestamp",
                color=Colors.TEXT_SECONDARY,
            )

            dpg.add_spacer(width=20)  # type: ignore

            dpg.add_checkbox(  # type: ignore
                label="Auto-refresh",
                tag="preview_auto_refresh",
                default_value=True,
            )

            dpg.add_button(  # type: ignore
                label="🔄 Atualizar",
                callback=self._on_refresh_preview,
                width=100,
            )

    def _create_readings_section(self) -> None:
        """Cria seção de leituras em tempo real."""
        dpg.add_text(  # type: ignore
            "📊 LEITURAS EM TEMPO REAL",
            color=Colors.PRIMARY,
        )
        dpg.add_separator()  # type: ignore
        dpg.add_spacer(height=5)  # type: ignore

        # Container para leituras
        with dpg.group(tag=self.TAG_READINGS_GROUP):  # type: ignore
            readings = [
                ("balance", "💰 Saldo", "R$ --"),
                ("timer", "⏱️ Timer", "-- s"),
                ("multiplier", "🎯 Multiplicador", "--.--x"),
                ("button", "🔘 Estado Botão", "---"),
            ]

            for reading_id, label, default in readings:
                with dpg.group():  # type: ignore
                    with dpg.group(horizontal=True):  # type: ignore
                        dpg.add_text(  # type: ignore
                            "⬜",
                            tag=f"reading_icon_{reading_id}",
                        )
                        dpg.add_text(  # type: ignore
                            label,
                            color=Colors.TEXT_SECONDARY,
                        )

                    with dpg.group(horizontal=True):  # type: ignore
                        dpg.add_text(  # type: ignore
                            default,
                            tag=f"reading_value_{reading_id}",
                            color=Colors.TEXT_PRIMARY,
                        )
                        dpg.add_spacer()  # type: ignore
                        dpg.add_text(  # type: ignore
                            "0%",
                            tag=f"reading_confidence_{reading_id}",
                            color=Colors.TEXT_MUTED,
                        )

                    dpg.add_spacer(height=10)  # type: ignore

        dpg.add_separator()  # type: ignore
        dpg.add_spacer(height=10)  # type: ignore

        # Cor capturada
        dpg.add_text(  # type: ignore
            "🎨 COR DO BOTÃO",
            color=Colors.PRIMARY,
        )
        dpg.add_spacer(height=5)  # type: ignore

        with dpg.group(horizontal=True):  # type: ignore
            dpg.add_text(  # type: ignore
                "RGB:",
                color=Colors.TEXT_MUTED,
            )
            dpg.add_text(  # type: ignore
                "(---, ---, ---)",
                tag="button_color_rgb",
                color=Colors.TEXT_SECONDARY,
            )

        with dpg.group(horizontal=True):  # type: ignore
            dpg.add_text(  # type: ignore
                "Estado:",
                color=Colors.TEXT_MUTED,
            )
            dpg.add_text(  # type: ignore
                "---",
                tag="button_color_state",
                color=Colors.TEXT_SECONDARY,
            )

        # Preview de cor
        with dpg.drawlist(  # type: ignore
            tag="color_preview",
            width=260,
            height=30,
        ):
            dpg.draw_rectangle(  # type: ignore
                (0, 0),
                (260, 30),
                fill=(50, 50, 50, 255),
                tag="color_preview_rect",
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_profile_selected(self, sender: Any, app_data: Any) -> None:
        """Callback quando perfil é selecionado."""
        profile_name = app_data

        if not profile_name:
            return

        profile = self._profile_manager.load(profile_name)

        if profile:
            self._current_profile = profile
            self._update_profile_display()
            self._set_status(f"Perfil '{profile_name}' carregado")
            logger.info(f"Perfil selecionado: {profile_name}")

    def _on_new_profile(self) -> None:
        """Callback para criar novo perfil."""
        # Gera nome único
        base_name = "brabet"
        counter = 1
        name = base_name

        while self._profile_manager.exists(name):
            name = f"{base_name}_{counter}"
            counter += 1

        # Cria perfil
        profile = self._profile_manager.create_default_profile(name)
        self._profile_manager.save(profile)

        # Atualiza UI
        self._refresh_profiles()
        dpg.set_value(self.TAG_PROFILE_COMBO, name)  # type: ignore
        self._current_profile = profile
        self._update_profile_display()

        self._set_status(f"Perfil '{name}' criado")

    def _on_duplicate_profile(self) -> None:
        """Callback para duplicar perfil."""
        if not self._current_profile:
            self._set_status("Nenhum perfil selecionado", error=True)
            return

        new_name = f"{self._current_profile.name}_copia"
        counter = 1

        while self._profile_manager.exists(new_name):
            new_name = f"{self._current_profile.name}_copia_{counter}"
            counter += 1

        new_profile = self._profile_manager.duplicate(
            self._current_profile.name,
            new_name,
        )

        if new_profile:
            self._refresh_profiles()
            dpg.set_value(self.TAG_PROFILE_COMBO, new_name)  # type: ignore
            self._current_profile = new_profile
            self._update_profile_display()
            self._set_status(f"Perfil duplicado: '{new_name}'")

    def _on_delete_profile(self) -> None:
        """Callback para excluir perfil."""
        if not self._current_profile:
            self._set_status("Nenhum perfil selecionado", error=True)
            return

        name = self._current_profile.name

        if self._profile_manager.delete(name):
            self._current_profile = None
            self._refresh_profiles()
            self._set_status(f"Perfil '{name}' excluído")

    def _on_calibrate_region(self) -> None:
        """Callback para calibrar região (genérico)."""
        self._set_status("Selecione uma região específica na lista")

    def _on_calibrate_click(self) -> None:
        """Callback para calibrar clique (genérico)."""
        self._set_status("Selecione um ponto específico na lista")

    def _calibrate_specific_region(self, region_id: str) -> None:
        """Calibra uma região específica."""
        if not self._current_profile:
            self._set_status("Crie ou selecione um perfil primeiro", error=True)
            return

        labels = {
            "balance": "Selecione a região do SALDO (R$)",
            "timer": "Selecione a região do TIMER (Bet Xs)",
            "history": "Selecione a região do HISTÓRICO (pills)",
            "multiplier": "Selecione a região do MULTIPLICADOR",
            "bet_button": "Selecione a região do BOTÃO DE APOSTA",
        }

        label = labels.get(region_id, "Selecione a região")

        # Minimiza janela do calibrador
        self._set_status(f"Calibrando {region_id}... (ESC para cancelar)")

        # Abre seletor
        result = self._region_selector.select_region(label)

        if result and result.success:
            region = RegionConfig(
                x=result.x,
                y=result.y,
                width=result.width,
                height=result.height,
            )

            # Salva no perfil
            if region_id == "balance":
                self._current_profile.balance_area = region
            elif region_id == "timer":
                self._current_profile.timer_area = region
            elif region_id == "history":
                self._current_profile.history_area = region
            elif region_id == "multiplier":
                self._current_profile.multiplier_area = region
            elif region_id == "bet_button":
                self._current_profile.bet_button_area = region

            self._update_profile_display()
            self._set_status(
                f"Região '{region_id}' calibrada: {result.width}x{result.height}"
            )
        else:
            self._set_status("Calibração cancelada")

    def _calibrate_specific_click(self, click_id: str) -> None:
        """Calibra um ponto de clique específico."""
        if not self._current_profile:
            self._set_status("Crie ou selecione um perfil primeiro", error=True)
            return

        labels = {
            "bet_value_1": "Clique no CAMPO DE VALOR da Aposta 1",
            "target_1": "Clique no CAMPO DE MULTIPLICADOR da Aposta 1",
            "bet_button_1": "Clique no BOTÃO DE APOSTA 1",
            "bet_value_2": "Clique no CAMPO DE VALOR da Aposta 2",
            "target_2": "Clique no CAMPO DE MULTIPLICADOR da Aposta 2",
            "bet_button_2": "Clique no BOTÃO DE APOSTA 2",
        }

        label = labels.get(click_id, "Clique no ponto")

        self._set_status(f"Calibrando {click_id}... (ESC para cancelar)")

        result = self._region_selector.select_point(label)

        if result and result.success:
            point = ClickPoint(x=result.x, y=result.y)

            # Salva no perfil
            if click_id == "bet_value_1":
                self._current_profile.bet_value_click_1 = point
            elif click_id == "target_1":
                self._current_profile.target_click_1 = point
            elif click_id == "bet_button_1":
                self._current_profile.bet_button_click_1 = point
            elif click_id == "bet_value_2":
                self._current_profile.bet_value_click_2 = point
            elif click_id == "target_2":
                self._current_profile.target_click_2 = point
            elif click_id == "bet_button_2":
                self._current_profile.bet_button_click_2 = point

            self._update_profile_display()
            self._set_status(f"Ponto '{click_id}' calibrado: ({result.x}, {result.y})")
        else:
            self._set_status("Calibração cancelada")

    def _on_test_all(self) -> None:
        """Callback para testar todas as leituras."""
        if not self._current_profile:
            self._set_status("Nenhum perfil selecionado", error=True)
            return

        self._set_status("Testando leituras...")
        self._update_readings()
        self._set_status("Teste concluído")

    def _on_save_profile(self) -> None:
        """Callback para salvar perfil."""
        if not self._current_profile:
            self._set_status("Nenhum perfil para salvar", error=True)
            return

        if self._profile_manager.save(self._current_profile):
            self._set_status(f"Perfil '{self._current_profile.name}' salvo!")
        else:
            self._set_status("Erro ao salvar perfil", error=True)

    def _on_reset_profile(self) -> None:
        """Callback para resetar perfil."""
        if not self._current_profile:
            return

        name = self._current_profile.name
        self._current_profile = self._profile_manager.create_default_profile(name)
        self._update_profile_display()
        self._set_status(f"Perfil '{name}' resetado")

    def _on_refresh_preview(self) -> None:
        """Callback para atualizar preview."""
        self._update_preview()

    # ═══════════════════════════════════════════════════════════════════════════
    # ATUALIZAÇÕES DA UI
    # ═══════════════════════════════════════════════════════════════════════════

    def _refresh_profiles(self) -> None:
        """Atualiza lista de perfis."""
        profiles = self._profile_manager.list_profiles()
        dpg.configure_item(  # type: ignore
            self.TAG_PROFILE_COMBO,
            items=profiles,
        )

        if profiles and not self._current_profile:
            dpg.set_value(self.TAG_PROFILE_COMBO, profiles[0])  # type: ignore
            self._on_profile_selected(None, profiles[0])

    def _update_profile_display(self) -> None:
        """Atualiza exibição do perfil atual."""
        if not self._current_profile:
            return

        profile = self._current_profile

        # Plataforma
        dpg.set_value("profile_platform", profile.platform)  # type: ignore

        # Progresso
        completion = profile.get_completion_percentage()
        dpg.set_value("profile_progress", completion / 100)  # type: ignore
        dpg.set_value("profile_progress_text", f"{completion:.0f}%")  # type: ignore

        # Status das regiões
        status = profile.get_calibration_status()

        region_map = {
            "balance": "balance",
            "timer": "timer",
            "history": "history",
            "multiplier": "multiplier",
            "bet_button": "bet_button",
        }

        for key, region_id in region_map.items():
            icon = "✅" if status.get(key, False) else "⬜"
            dpg.set_value(f"region_status_{region_id}", icon)  # type: ignore

        # Status dos cliques
        click_map = {
            "bet_value_click": "bet_value_1",
            "target_click": "target_1",
            "bet_button_click": "bet_button_1",
        }

        for key, click_id in click_map.items():
            icon = "✅" if status.get(key, False) else "⬜"
            dpg.set_value(f"click_status_{click_id}", icon)  # type: ignore

        # Cliques 2 (verificar manualmente)
        icon_v2 = "✅" if profile.bet_value_click_2 else "⬜"
        icon_t2 = "✅" if profile.target_click_2 else "⬜"
        icon_b2 = "✅" if profile.bet_button_click_2 else "⬜"

        dpg.set_value("click_status_bet_value_2", icon_v2)  # type: ignore
        dpg.set_value("click_status_target_2", icon_t2)  # type: ignore
        dpg.set_value("click_status_bet_button_2", icon_b2)  # type: ignore

    def _update_readings(self) -> None:
        """Atualiza leituras em tempo real."""
        if not self._current_profile:
            return

        try:
            results = self._live_preview.test_profile(self._current_profile)

            for reading_id, result in results.items():
                # Ícone
                dpg.set_value(  # type: ignore
                    f"reading_icon_{reading_id}",
                    result.status_icon,
                )

                # Valor
                if result.value is not None:
                    if reading_id == "balance":
                        value_text = f"R$ {result.value:,.2f}"
                    elif reading_id == "timer":
                        value_text = f"{result.value}s"
                    elif reading_id == "multiplier":
                        value_text = f"{result.value:.2f}x"
                    else:
                        value_text = str(result.value)
                else:
                    value_text = "---"

                dpg.set_value(  # type: ignore
                    f"reading_value_{reading_id}",
                    value_text,
                )

                # Confiança
                dpg.set_value(  # type: ignore
                    f"reading_confidence_{reading_id}",
                    f"{result.confidence:.0%}",
                )

            # Cor do botão
            if self._current_profile.bet_button_area:
                button_state = self._live_preview.test_button_state(
                    self._current_profile.bet_button_area,
                    self._current_profile.button_bet_ready,
                    self._current_profile.button_waiting,
                )

                r, g, b = button_state.color

                dpg.set_value(  # type: ignore
                    "button_color_rgb",
                    f"({r}, {g}, {b})",
                )

                state = (
                    "🔴 APOSTAR"
                    if button_state.is_bet_ready
                    else (
                        "🟢 AGUARDANDO"
                        if button_state.is_waiting
                        else "⬜ DESCONHECIDO"
                    )
                )

                dpg.set_value("button_color_state", state)  # type: ignore

                # Atualiza preview de cor
                dpg.configure_item(  # type: ignore
                    "color_preview_rect",
                    fill=(r, g, b, 255),
                )

        except Exception as e:
            logger.error(f"Erro ao atualizar leituras: {e}")

    def _update_preview(self) -> None:
        """Atualiza preview da tela."""
        try:
            dpg.set_value(  # type: ignore
                "preview_timestamp",
                datetime.now().strftime("%H:%M:%S"),
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar preview: {e}")

    def _set_status(self, message: str, error: bool = False) -> None:
        """Define mensagem de status."""
        color = Colors.DANGER if error else Colors.TEXT_SECONDARY
        dpg.set_value(self.TAG_STATUS_TEXT, message)  # type: ignore
        dpg.configure_item(self.TAG_STATUS_TEXT, color=color)  # type: ignore

    # ═══════════════════════════════════════════════════════════════════════════
    # PREVIEW THREAD
    # ═══════════════════════════════════════════════════════════════════════════

    def _start_preview_thread(self) -> None:
        """Inicia thread de atualização do preview."""
        self._stop_preview.clear()
        self._preview_thread = threading.Thread(
            target=self._preview_loop,
            daemon=True,
        )
        self._preview_thread.start()

    def _preview_loop(self) -> None:
        """Loop de atualização do preview."""
        while not self._stop_preview.is_set():
            try:
                # Verifica se auto-refresh está habilitado
                if dpg.get_value("preview_auto_refresh"):  # type: ignore
                    self._update_readings()
                    self._update_preview()
            except Exception as e:
                logger.error(f"Erro no preview loop: {e}")

            time.sleep(1.0)  # Atualiza a cada segundo

    # ═══════════════════════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════════════════════

    def _cleanup(self) -> None:
        """Limpa recursos."""
        self._stop_preview.set()

        if self._preview_thread:
            self._preview_thread.join(timeout=2.0)

        self._live_preview.cleanup()

        try:
            dpg.destroy_context()  # type: ignore
        except Exception:
            pass

        self._is_running = False
        logger.debug("CalibratorWindow finalizado")


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO DE LANÇAMENTO
# ═══════════════════════════════════════════════════════════════════════════════


def launch_calibrator() -> None:
    """
    Função rápida para lançar o calibrador.

    Uso:
        from calibration import launch_calibrator
        launch_calibrator()
    """
    calibrator = CalibratorWindow()
    calibrator.show()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("CRASHBOT v3.0 - CALIBRADOR")
    print("=" * 60)

    launch_calibrator()
