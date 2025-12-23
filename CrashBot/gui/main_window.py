#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - MAIN WINDOW

Janela principal da aplicação.

Uso:
    from gui.main_window import MainWindow

    app = MainWindow()
    app.run()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# DearPyGui
try:
    import dearpygui.dearpygui as dpg

    HAS_DPG = True
except ImportError:
    HAS_DPG = False
    dpg = None

# Core imports
from core.events import BotEvent, get_event_bus, subscribe
from core.state import BotState, RiskMode, get_state
from gui.components import (
    add_log_line,
    add_tooltip,
    add_vertical_space,
    create_explosion_history,
    create_log_viewer,
    create_progress_bar,
    create_section_header,
    create_stat_card,
    create_status_indicator,
    show_confirm_dialog,
    update_explosion_history,
    update_progress_bar,
    update_stat_card,
    update_status_indicator,
)

# Local imports
from gui.theme import (
    Colors,
    FontSizes,
    Spacing,
    apply_theme,
    create_danger_button_theme,
    create_success_button_theme,
    create_warning_button_theme,
)

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

WINDOW_TITLE = "CrashBot v3.0 - Powered by AI"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
MIN_WIDTH = 1024
MIN_HEIGHT = 600


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════


class MainWindow:
    """
    Janela principal do CrashBot.

    Layout:
    ┌──────────────────────────────────────────────────────────┐
    │  HEADER: Logo + Status + Controles                       │
    ├──────────────┬───────────────────────────────────────────┤
    │              │                                           │
    │   SIDEBAR    │              MAIN AREA                    │
    │   - Stats    │   - Tabs: Dashboard | Config | ML | Logs  │
    │   - Config   │                                           │
    │   - Actions  │                                           │
    │              │                                           │
    ├──────────────┴───────────────────────────────────────────┤
    │  FOOTER: Logs resumidos + Copyright                      │
    └──────────────────────────────────────────────────────────┘
    """

    def __init__(self):
        """Inicializa a janela principal."""
        if not HAS_DPG:
            raise ImportError(
                "DearPyGui não encontrado. Instale com: pip install dearpygui"
            )

        # Estado
        self._running = False
        self._bot_running = False

        # IDs dos elementos
        self._ids: Dict[str, Any] = {}

        # Dados
        self._explosions: List[float] = []
        self._stats = {
            "balance": 0.0,
            "profit": 0.0,
            "win_rate": 0.0,
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
        }

        # Callbacks externos
        self._on_start: Optional[Callable] = None
        self._on_stop: Optional[Callable] = None
        self._on_config_change: Optional[Callable] = None

        # Temas de botões
        self._success_theme: Optional[int] = None
        self._danger_theme: Optional[int] = None
        self._warning_theme: Optional[int] = None

        logger.info("MainWindow inicializada")

    # ═══════════════════════════════════════════════════════════════════════════
    # SETUP
    # ═══════════════════════════════════════════════════════════════════════════

    def setup(self) -> None:
        """Configura DearPyGui e cria interface."""
        dpg.create_context()
        dpg.create_viewport(
            title=WINDOW_TITLE,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_width=MIN_WIDTH,
            min_height=MIN_HEIGHT,
        )

        # Aplica tema
        apply_theme()

        # Cria temas de botões
        self._success_theme = create_success_button_theme()
        self._danger_theme = create_danger_button_theme()
        self._warning_theme = create_warning_button_theme()

        # Cria interface
        self._create_main_window()

        # Setup viewport
        dpg.setup_dearpygui()
        dpg.show_viewport()

        # Registra eventos
        self._register_events()

        logger.info("Interface configurada")

    def _create_main_window(self) -> None:
        """Cria janela principal."""
        with dpg.window(tag="main_window", no_title_bar=True, no_resize=True):
            # Header
            self._create_header()

            dpg.add_separator()

            # Body (sidebar + main)
            with dpg.group(horizontal=True):
                # Sidebar
                self._create_sidebar()

                # Separator vertical
                dpg.add_spacer(width=Spacing.MD)

                # Main area
                self._create_main_area()

            dpg.add_separator()

            # Footer
            self._create_footer()

        # Configura para preencher viewport
        dpg.set_primary_window("main_window", True)

    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_header(self) -> None:
        """Cria header com logo e controles."""
        with dpg.group(horizontal=True):
            # Logo / Título
            dpg.add_text("🚀 CRASHBOT", color=Colors.PRIMARY)
            dpg.add_text("v3.0", color=Colors.TEXT_MUTED)

            dpg.add_spacer(width=Spacing.XL)

            # Status do bot
            self._ids["status_indicator"] = create_status_indicator(
                parent=dpg.last_container(),
                label="Parado",
                status="inactive",
            )

            dpg.add_spacer(width=-1)  # Push para direita

            # Botões de controle
            self._ids["btn_start"] = dpg.add_button(
                label="▶ INICIAR",
                callback=self._on_start_click,
                width=120,
            )
            dpg.bind_item_theme(self._ids["btn_start"], self._success_theme)

            self._ids["btn_stop"] = dpg.add_button(
                label="⏹ PARAR",
                callback=self._on_stop_click,
                width=120,
                enabled=False,
            )
            dpg.bind_item_theme(self._ids["btn_stop"], self._danger_theme)

    # ═══════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_sidebar(self) -> None:
        """Cria sidebar com stats e configurações rápidas."""
        with dpg.child_window(width=280, border=False) as sidebar:
            self._ids["sidebar"] = sidebar

            # ─────────────────────────────────────────────────────────────────
            # Seção: Saldo
            # ─────────────────────────────────────────────────────────────────
            create_section_header(sidebar, "💰 SALDO")

            self._ids["balance_card"] = create_stat_card(
                parent=sidebar,
                label="Saldo Atual",
                value="R$ 0.00",
                sublabel="",
                color=Colors.GOLD,
                width=-1,
                height=80,
            )

            add_vertical_space(sidebar)

            # ─────────────────────────────────────────────────────────────────
            # Seção: Estatísticas
            # ─────────────────────────────────────────────────────────────────
            create_section_header(sidebar, "📊 ESTATÍSTICAS")

            with dpg.group(horizontal=True):
                self._ids["profit_card"] = create_stat_card(
                    parent=dpg.last_container(),
                    label="Lucro",
                    value="R$ 0.00",
                    color=Colors.SUCCESS,
                    width=130,
                )
                self._ids["winrate_card"] = create_stat_card(
                    parent=dpg.last_container(),
                    label="Win Rate",
                    value="0%",
                    color=Colors.PRIMARY,
                    width=130,
                )

            add_vertical_space(sidebar)

            with dpg.group(horizontal=True):
                self._ids["wins_card"] = create_stat_card(
                    parent=dpg.last_container(),
                    label="Vitórias",
                    value="0",
                    color=Colors.SUCCESS,
                    width=130,
                )
                self._ids["losses_card"] = create_stat_card(
                    parent=dpg.last_container(),
                    label="Derrotas",
                    value="0",
                    color=Colors.DANGER,
                    width=130,
                )

            add_vertical_space(sidebar, Spacing.LG)

            # ─────────────────────────────────────────────────────────────────
            # Seção: Gatilho
            # ─────────────────────────────────────────────────────────────────
            create_section_header(sidebar, "🎯 GATILHO")

            self._ids["trigger_progress"] = create_progress_bar(
                parent=sidebar,
                label="Progresso",
                value=0.0,
                width=-1,
            )

            dpg.add_text(
                "0/8 velas baixas", color=Colors.TEXT_MUTED, tag="trigger_text"
            )
            self._ids["trigger_text"] = "trigger_text"

            add_vertical_space(sidebar, Spacing.LG)

            # ─────────────────────────────────────────────────────────────────
            # Seção: Configurações Rápidas
            # ─────────────────────────────────────────────────────────────────
            create_section_header(sidebar, "⚙️ CONFIG RÁPIDA")

            # Modo de risco
            dpg.add_text("Modo de Risco:", color=Colors.TEXT_SECONDARY)
            self._ids["risk_combo"] = dpg.add_combo(
                items=["Conservador", "Moderado", "Agressivo"],
                default_value="Conservador",
                callback=self._on_risk_change,
                width=-1,
            )

            add_vertical_space(sidebar)

            # Alvo
            dpg.add_text("Alvo:", color=Colors.TEXT_SECONDARY)
            self._ids["target_input"] = dpg.add_input_float(
                default_value=1.85,
                min_value=1.1,
                max_value=10.0,
                step=0.05,
                format="%.2f",
                width=-1,
                callback=self._on_target_change,
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN AREA
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_main_area(self) -> None:
        """Cria área principal com tabs."""
        with dpg.child_window(border=False) as main_area:
            self._ids["main_area"] = main_area

            with dpg.tab_bar() as tab_bar:
                self._ids["tab_bar"] = tab_bar

                # Tab: Dashboard
                with dpg.tab(label="📈 Dashboard"):
                    self._create_dashboard_tab()

                # Tab: Configurações
                with dpg.tab(label="⚙️ Configurações"):
                    self._create_config_tab()

                # Tab: Machine Learning
                with dpg.tab(label="🤖 IA / ML"):
                    self._create_ml_tab()

                # Tab: Logs
                with dpg.tab(label="📝 Logs"):
                    self._create_logs_tab()

    def _create_dashboard_tab(self) -> None:
        """Cria conteúdo da tab Dashboard."""
        # Histórico de explosões
        create_section_header(dpg.last_container(), "🎲 Histórico de Explosões")

        self._ids["explosion_history"] = create_explosion_history(
            parent=dpg.last_container(),
            explosions=self._explosions,
            max_display=30,
        )

        add_vertical_space(dpg.last_container(), Spacing.LG)

        # Última explosão
        with dpg.group(horizontal=True):
            dpg.add_text("Última explosão:", color=Colors.TEXT_SECONDARY)
            self._ids["last_explosion"] = dpg.add_text(
                "-.-- x",
                color=Colors.TEXT_MUTED,
            )

            dpg.add_spacer(width=Spacing.XL)

            dpg.add_text("Dobra atual:", color=Colors.TEXT_SECONDARY)
            self._ids["current_dobra"] = dpg.add_text(
                "1",
                color=Colors.PRIMARY,
            )

        add_vertical_space(dpg.last_container(), Spacing.LG)

        # Gráfico de resultados
        create_section_header(dpg.last_container(), "📊 Performance")

        with dpg.plot(label="Saldo ao Longo do Tempo", height=250, width=-1):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Rodada")

            with dpg.plot_axis(dpg.mvYAxis, label="Saldo (R$)") as y_axis:
                self._ids["balance_series"] = dpg.add_line_series(
                    [],
                    [],
                    label="Saldo",
                )

    def _create_config_tab(self) -> None:
        """Cria conteúdo da tab Configurações."""
        with dpg.group():
            # Configurações de Estratégia
            with dpg.collapsing_header(label="Estratégia", default_open=True):
                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text("Threshold (vela baixa):")
                        self._ids["config_threshold"] = dpg.add_input_float(
                            default_value=2.0,
                            min_value=1.5,
                            max_value=3.0,
                            step=0.1,
                            width=150,
                        )

                    dpg.add_spacer(width=Spacing.XL)

                    with dpg.group():
                        dpg.add_text("Velas necessárias:")
                        self._ids["config_lows_needed"] = dpg.add_input_int(
                            default_value=8,
                            min_value=4,
                            max_value=15,
                            width=150,
                        )

                add_vertical_space(dpg.last_container())

                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text("Aposta base (divisor):")
                        self._ids["config_divisor"] = dpg.add_input_int(
                            default_value=15,
                            min_value=5,
                            max_value=50,
                            width=150,
                        )

                    dpg.add_spacer(width=Spacing.XL)

                    with dpg.group():
                        dpg.add_text("Máximo de dobras:")
                        self._ids["config_max_dobra"] = dpg.add_input_int(
                            default_value=4,
                            min_value=1,
                            max_value=8,
                            width=150,
                        )

            add_vertical_space(dpg.last_container())

            # Configurações de Monitor
            with dpg.collapsing_header(label="Monitor", default_open=True):
                dpg.add_text("Selecione o monitor:")
                self._ids["config_monitor"] = dpg.add_combo(
                    items=["Monitor 1", "Monitor 2"],
                    default_value="Monitor 1",
                    width=200,
                )

                add_vertical_space(dpg.last_container())

                dpg.add_button(
                    label="🔧 Abrir Calibração",
                    callback=self._on_open_calibration,
                    width=200,
                )

            add_vertical_space(dpg.last_container())

            # Botões de ação
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="💾 Salvar Configurações",
                    callback=self._on_save_config,
                    width=180,
                )

                dpg.add_button(
                    label="🔄 Restaurar Padrões",
                    callback=self._on_restore_defaults,
                    width=180,
                )

    def _create_ml_tab(self) -> None:
        """Cria conteúdo da tab Machine Learning."""
        with dpg.group():
            # Status dos modelos
            with dpg.collapsing_header(label="Status dos Modelos", default_open=True):
                with dpg.group(horizontal=True):
                    create_stat_card(
                        parent=dpg.last_container(),
                        label="LSTM",
                        value="Não Treinado",
                        color=Colors.TEXT_MUTED,
                        width=200,
                    )
                    create_stat_card(
                        parent=dpg.last_container(),
                        label="RL Agent",
                        value="Não Treinado",
                        color=Colors.TEXT_MUTED,
                        width=200,
                    )
                    create_stat_card(
                        parent=dpg.last_container(),
                        label="Optimizer",
                        value="Disponível",
                        color=Colors.SUCCESS,
                        width=200,
                    )

            add_vertical_space(dpg.last_container())

            # Decision Engine
            with dpg.collapsing_header(label="Decision Engine", default_open=True):
                dpg.add_text(
                    "Pesos das fontes de decisão:", color=Colors.TEXT_SECONDARY
                )

                add_vertical_space(dpg.last_container())

                dpg.add_text("Regras Fixas:")
                self._ids["weight_rules"] = dpg.add_slider_float(
                    default_value=0.4,
                    min_value=0.0,
                    max_value=1.0,
                    width=300,
                )

                dpg.add_text("LSTM:")
                self._ids["weight_lstm"] = dpg.add_slider_float(
                    default_value=0.3,
                    min_value=0.0,
                    max_value=1.0,
                    width=300,
                )

                dpg.add_text("RL Agent:")
                self._ids["weight_rl"] = dpg.add_slider_float(
                    default_value=0.3,
                    min_value=0.0,
                    max_value=1.0,
                    width=300,
                )

            add_vertical_space(dpg.last_container())

            # Ações
            with dpg.collapsing_header(label="Treinamento", default_open=True):
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="📥 Importar Dados",
                        callback=self._on_import_data,
                        width=150,
                    )

                    dpg.add_button(
                        label="🧠 Treinar LSTM",
                        callback=self._on_train_lstm,
                        width=150,
                    )

                    dpg.add_button(
                        label="🤖 Treinar RL",
                        callback=self._on_train_rl,
                        width=150,
                    )

                    dpg.add_button(
                        label="🔧 Otimizar",
                        callback=self._on_optimize,
                        width=150,
                    )

    def _create_logs_tab(self) -> None:
        """Cria conteúdo da tab Logs."""
        # Filtros
        with dpg.group(horizontal=True):
            dpg.add_text("Filtrar:", color=Colors.TEXT_SECONDARY)
            self._ids["log_filter"] = dpg.add_combo(
                items=["Todos", "Info", "Warning", "Error", "Success"],
                default_value="Todos",
                width=120,
            )

            dpg.add_spacer(width=-1)

            dpg.add_button(
                label="🗑️ Limpar",
                callback=self._on_clear_logs,
                width=100,
            )

        add_vertical_space(dpg.last_container())

        # Log viewer
        self._ids["log_viewer"] = create_log_viewer(
            parent=dpg.last_container(),
            height=400,
            max_lines=500,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_footer(self) -> None:
        """Cria footer."""
        with dpg.group(horizontal=True):
            self._ids["footer_status"] = dpg.add_text(
                "Pronto",
                color=Colors.TEXT_MUTED,
            )

            dpg.add_spacer(width=-1)

            dpg.add_text(
                "© 2024 TucunaréBot",
                color=Colors.TEXT_MUTED,
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _register_events(self) -> None:
        """Registra handlers de eventos."""
        subscribe(BotEvent.EXPLOSION_DETECTED, self._handle_explosion)
        subscribe(BotEvent.BET_PLACED, self._handle_bet_placed)
        subscribe(BotEvent.BET_WON, self._handle_bet_won)
        subscribe(BotEvent.BET_LOST, self._handle_bet_lost)
        subscribe(BotEvent.BALANCE_UPDATED, self._handle_balance_update)
        subscribe(BotEvent.TRIGGER_PROGRESS, self._handle_trigger_progress)

    def _handle_explosion(self, data: Dict) -> None:
        """Handle para nova explosão."""
        value = data.get("value", 0.0)
        self._explosions.append(value)

        # Atualiza UI (thread-safe)
        dpg.set_value(self._ids["last_explosion"], f"{value:.2f}x")

        color = Colors.SUCCESS if value >= 2.0 else Colors.DANGER
        dpg.configure_item(self._ids["last_explosion"], color=color)

        # Atualiza histórico
        update_explosion_history(
            self._ids["explosion_history"],
            self._explosions[-30:],
        )

    def _handle_bet_placed(self, data: Dict) -> None:
        """Handle para aposta realizada."""
        add_log_line(
            self._ids["log_viewer"],
            f"Aposta: R$ {data.get('amount', 0):.2f} @ {data.get('target', 0):.2f}x",
            level="info",
        )

    def _handle_bet_won(self, data: Dict) -> None:
        """Handle para vitória."""
        self._stats["wins"] += 1
        self._update_stats_display()

        add_log_line(
            self._ids["log_viewer"],
            f"WIN! Lucro: R$ {data.get('profit', 0):.2f}",
            level="success",
        )

    def _handle_bet_lost(self, data: Dict) -> None:
        """Handle para derrota."""
        self._stats["losses"] += 1
        self._update_stats_display()

        add_log_line(
            self._ids["log_viewer"],
            f"LOSS: -R$ {data.get('amount', 0):.2f}",
            level="error",
        )

    def _handle_balance_update(self, data: Dict) -> None:
        """Handle para atualização de saldo."""
        balance = data.get("balance", 0.0)
        self._stats["balance"] = balance

        update_stat_card(
            self._ids["balance_card"],
            value=f"R$ {balance:.2f}",
        )

    def _handle_trigger_progress(self, data: Dict) -> None:
        """Handle para progresso do gatilho."""
        current = data.get("current", 0)
        needed = data.get("needed", 8)
        progress = current / needed if needed > 0 else 0

        update_progress_bar(self._ids["trigger_progress"], progress)
        dpg.set_value(self._ids["trigger_text"], f"{current}/{needed} velas baixas")

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CALLBACKS
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_start_click(self) -> None:
        """Callback do botão Iniciar."""
        self._bot_running = True

        # Atualiza UI
        dpg.configure_item(self._ids["btn_start"], enabled=False)
        dpg.configure_item(self._ids["btn_stop"], enabled=True)

        update_status_indicator(
            self._ids["status_indicator"],
            status="running",
            label="Executando",
        )

        add_log_line(self._ids["log_viewer"], "Bot iniciado", level="success")

        # Chama callback externo
        if self._on_start:
            self._on_start()

    def _on_stop_click(self) -> None:
        """Callback do botão Parar."""

        def confirm_stop():
            self._bot_running = False

            dpg.configure_item(self._ids["btn_start"], enabled=True)
            dpg.configure_item(self._ids["btn_stop"], enabled=False)

            update_status_indicator(
                self._ids["status_indicator"],
                status="inactive",
                label="Parado",
            )

            add_log_line(self._ids["log_viewer"], "Bot parado", level="warning")

            if self._on_stop:
                self._on_stop()

        show_confirm_dialog(
            "Confirmar",
            "Deseja realmente parar o bot?",
            on_confirm=confirm_stop,
        )

    def _on_risk_change(self, sender, value) -> None:
        """Callback para mudança de modo de risco."""
        add_log_line(
            self._ids["log_viewer"],
            f"Modo de risco alterado: {value}",
            level="info",
        )

    def _on_target_change(self, sender, value) -> None:
        """Callback para mudança de alvo."""
        add_log_line(
            self._ids["log_viewer"],
            f"Alvo alterado: {value:.2f}x",
            level="info",
        )

    def _on_open_calibration(self) -> None:
        """Abre janela de calibração."""
        add_log_line(self._ids["log_viewer"], "Abrindo calibração...", level="info")
        # TODO: Implementar janela de calibração

    def _on_save_config(self) -> None:
        """Salva configurações."""
        add_log_line(self._ids["log_viewer"], "Configurações salvas", level="success")

    def _on_restore_defaults(self) -> None:
        """Restaura configurações padrão."""
        add_log_line(self._ids["log_viewer"], "Configurações restauradas", level="info")

    def _on_import_data(self) -> None:
        """Importa dados históricos."""
        add_log_line(self._ids["log_viewer"], "Importando dados...", level="info")

    def _on_train_lstm(self) -> None:
        """Treina modelo LSTM."""
        add_log_line(self._ids["log_viewer"], "Iniciando treino LSTM...", level="info")

    def _on_train_rl(self) -> None:
        """Treina agente RL."""
        add_log_line(self._ids["log_viewer"], "Iniciando treino RL...", level="info")

    def _on_optimize(self) -> None:
        """Executa otimização."""
        add_log_line(self._ids["log_viewer"], "Iniciando otimização...", level="info")

    def _on_clear_logs(self) -> None:
        """Limpa logs."""
        from gui.components import clear_log_viewer

        clear_log_viewer(self._ids["log_viewer"])

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_stats_display(self) -> None:
        """Atualiza display de estatísticas."""
        wins = self._stats["wins"]
        losses = self._stats["losses"]
        total = wins + losses

        win_rate = (wins / total * 100) if total > 0 else 0
        self._stats["win_rate"] = win_rate

        update_stat_card(self._ids["wins_card"], value=str(wins))
        update_stat_card(self._ids["losses_card"], value=str(losses))
        update_stat_card(self._ids["winrate_card"], value=f"{win_rate:.1f}%")

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def set_callbacks(
        self,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_config_change: Optional[Callable] = None,
    ) -> None:
        """Define callbacks externos."""
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_config_change = on_config_change

    def log(self, message: str, level: str = "info") -> None:
        """Adiciona mensagem ao log."""
        if "log_viewer" in self._ids:
            add_log_line(self._ids["log_viewer"], message, level)

    def update_balance(self, balance: float) -> None:
        """Atualiza saldo exibido."""
        self._stats["balance"] = balance
        update_stat_card(self._ids["balance_card"], value=f"R$ {balance:.2f}")

    def update_profit(self, profit: float) -> None:
        """Atualiza lucro exibido."""
        self._stats["profit"] = profit
        color = Colors.SUCCESS if profit >= 0 else Colors.DANGER
        update_stat_card(
            self._ids["profit_card"],
            value=f"R$ {profit:.2f}",
            color=color,
        )

    def run(self) -> None:
        """Executa o loop principal."""
        self._running = True

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        self._running = False
        dpg.destroy_context()

    def stop(self) -> None:
        """Para a aplicação."""
        self._running = False
        dpg.stop_dearpygui()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DA INTERFACE - CrashBot v3.0")
    print("=" * 60)

    app = MainWindow()
    app.setup()

    # Simula alguns dados
    import random

    for _ in range(10):
        value = random.uniform(1.0, 5.0)
        app._explosions.append(round(value, 2))

    app.log("Interface carregada com sucesso!", "success")
    app.run()
