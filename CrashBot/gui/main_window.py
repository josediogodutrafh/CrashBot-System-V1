#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false

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
from typing import Any, Callable, Dict, List, Optional, Union

# DearPyGui
try:
    import dearpygui.dearpygui as dpg

    HAS_DPG = True
except ImportError:
    HAS_DPG = False
    dpg = None  # type: ignore

# GUI Components
from gui.components import (
    add_log_line,
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
from gui.theme import (
    Colors,
    Spacing,
    apply_theme,
    create_danger_button_theme,
    create_success_button_theme,
    create_warning_button_theme,
)
from core.state import get_state

# Logger
logger = logging.getLogger(__name__)

# Type alias
ItemID = Union[int, str]


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

    def __init__(self) -> None:
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
        self._stats: Dict[str, Any] = {
            "balance": 0.0,
            "profit": 0.0,
            "win_rate": 0.0,
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
        }

        # Callbacks externos
        self._on_start: Optional[Callable[[], None]] = None
        self._on_stop: Optional[Callable[[], None]] = None
        self._on_config_change: Optional[Callable[[Dict[str, Any]], None]] = None

        # Temas de botões
        self._success_theme: Optional[ItemID] = None
        self._danger_theme: Optional[ItemID] = None
        self._warning_theme: Optional[ItemID] = None

        logger.info("MainWindow inicializada")

    # ═══════════════════════════════════════════════════════════════════════════
    # SETUP
    # ═══════════════════════════════════════════════════════════════════════════

    def setup(self) -> None:
        """Configura DearPyGui e cria interface."""
        dpg.create_context()  # type: ignore
        dpg.create_viewport(  # type: ignore
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
        dpg.setup_dearpygui()  # type: ignore
        dpg.show_viewport()  # type: ignore

        # Registra eventos
        self._register_events()

        logger.info("Interface configurada")

    def _create_main_window(self) -> None:
        """Cria janela principal."""
        with dpg.window(  # type: ignore
            tag="main_window", no_title_bar=True, no_resize=True
        ):
            # Header
            self._create_header()

            dpg.add_separator()  # type: ignore

            # Body (sidebar + main)
            with dpg.group(horizontal=True):  # type: ignore
                # Sidebar
                self._create_sidebar()

                # Separator vertical
                dpg.add_spacer(width=Spacing.MD)  # type: ignore

                # Main area
                self._create_main_area()

            dpg.add_separator()  # type: ignore

            # Footer
            self._create_footer()

        # Configura para preencher viewport
        dpg.set_primary_window("main_window", True)  # type: ignore

    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_header(self) -> None:
        """Cria header com logo e controles."""
        with dpg.group(horizontal=True):  # type: ignore
            # Logo / Título
            dpg.add_text("🚀 CRASHBOT", color=Colors.PRIMARY)  # type: ignore
            dpg.add_text("v3.0", color=Colors.TEXT_MUTED)  # type: ignore

            dpg.add_spacer(width=Spacing.XL)  # type: ignore

            # Status do bot
            self._ids["status_indicator"] = create_status_indicator(
                parent=dpg.last_container(),  # type: ignore
                label="Parado",
                status="inactive",
            )

            dpg.add_spacer(width=-1)  # type: ignore  # Push para direita

            # Botões de controle
            self._ids["btn_start"] = dpg.add_button(  # type: ignore
                label="▶ INICIAR",
                callback=self._on_start_click,
                width=120,
            )
            if self._success_theme:
                dpg.bind_item_theme(  # type: ignore
                    self._ids["btn_start"], self._success_theme
                )

            self._ids["btn_stop"] = dpg.add_button(  # type: ignore
                label="⏹ PARAR",
                callback=self._on_stop_click,
                width=120,
                enabled=False,
            )
            if self._danger_theme:
                dpg.bind_item_theme(  # type: ignore
                    self._ids["btn_stop"], self._danger_theme
                )

    # ═══════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_sidebar(self) -> None:
        """Cria sidebar com stats e configurações rápidas."""
        with dpg.child_window(width=280, border=False) as sidebar:  # type: ignore
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

            with dpg.group(horizontal=True):  # type: ignore
                self._ids["profit_card"] = create_stat_card(
                    parent=dpg.last_container(),  # type: ignore
                    label="Lucro",
                    value="R$ 0.00",
                    color=Colors.SUCCESS,
                    width=130,
                )
                self._ids["winrate_card"] = create_stat_card(
                    parent=dpg.last_container(),  # type: ignore
                    label="Win Rate",
                    value="0%",
                    color=Colors.PRIMARY,
                    width=130,
                )

            add_vertical_space(sidebar)

            with dpg.group(horizontal=True):  # type: ignore
                self._ids["wins_card"] = create_stat_card(
                    parent=dpg.last_container(),  # type: ignore
                    label="Vitórias",
                    value="0",
                    color=Colors.SUCCESS,
                    width=130,
                )
                self._ids["losses_card"] = create_stat_card(
                    parent=dpg.last_container(),  # type: ignore
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

            self._ids["trigger_text"] = dpg.add_text(  # type: ignore
                "0/8 velas baixas",
                color=Colors.TEXT_MUTED,
                tag="trigger_text",
            )

            add_vertical_space(sidebar, Spacing.LG)

            # ─────────────────────────────────────────────────────────────────
            # Seção: Configurações Rápidas
            # ─────────────────────────────────────────────────────────────────
            create_section_header(sidebar, "⚙️ CONFIG RÁPIDA")

            # Plataforma
            dpg.add_text("Plataforma:", color=Colors.TEXT_SECONDARY)  # type: ignore
            self._ids["platform_combo"] = dpg.add_combo(  # type: ignore
                items=["Brabet", "OneBra", "WinBra", "PGWin"],
                default_value="Brabet",
                callback=self._on_platform_change,
                width=-1,
            )

            add_vertical_space(sidebar)

            # Modo de risco
            dpg.add_text("Modo de Risco:", color=Colors.TEXT_SECONDARY)  # type: ignore
            self._ids["risk_combo"] = dpg.add_combo(  # type: ignore
                items=["Conservador", "Moderado", "Agressivo"],
                default_value="Conservador",
                callback=self._on_risk_change,
                width=-1,
            )

            add_vertical_space(sidebar)

            # Alvo
            dpg.add_text("Alvo:", color=Colors.TEXT_SECONDARY)  # type: ignore
            self._ids["target_input"] = dpg.add_input_float(  # type: ignore
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
        with dpg.child_window(border=False) as main_area:  # type: ignore
            self._ids["main_area"] = main_area

            with dpg.tab_bar() as tab_bar:  # type: ignore
                self._ids["tab_bar"] = tab_bar

                # Tab: Dashboard
                with dpg.tab(label="📈 Dashboard"):  # type: ignore
                    self._create_dashboard_tab()

                # Tab: Configurações
                with dpg.tab(label="⚙️ Configurações"):  # type: ignore
                    self._create_config_tab()

                # Tab: Machine Learning
                with dpg.tab(label="🤖 IA / ML"):  # type: ignore
                    self._create_ml_tab()

                # Tab: Logs
                with dpg.tab(label="📝 Logs"):  # type: ignore
                    self._create_logs_tab()

    def _create_dashboard_tab(self) -> None:
        """Cria conteúdo da tab Dashboard."""
        parent = dpg.last_container()  # type: ignore

        # Histórico de explosões
        create_section_header(parent, "🎲 Histórico de Explosões")

        self._ids["explosion_history"] = create_explosion_history(
            parent=dpg.last_container(),  # type: ignore
            explosions=self._explosions,
            max_display=30,
        )

        add_vertical_space(dpg.last_container(), Spacing.LG)  # type: ignore

        # Última explosão
        with dpg.group(horizontal=True):  # type: ignore
            dpg.add_text("Última explosão:", color=Colors.TEXT_SECONDARY)  # type: ignore
            self._ids["last_explosion"] = dpg.add_text(  # type: ignore
                "-.-- x",
                color=Colors.TEXT_MUTED,
            )

            dpg.add_spacer(width=Spacing.XL)  # type: ignore

            dpg.add_text("Dobra atual:", color=Colors.TEXT_SECONDARY)  # type: ignore
            self._ids["current_dobra"] = dpg.add_text(  # type: ignore
                "1",
                color=Colors.PRIMARY,
            )

        add_vertical_space(dpg.last_container(), Spacing.LG)  # type: ignore

        # Gráfico de resultados
        create_section_header(dpg.last_container(), "📊 Performance")  # type: ignore

        with dpg.plot(  # type: ignore
            label="Saldo ao Longo do Tempo", height=250, width=-1
        ):
            dpg.add_plot_legend()  # type: ignore
            dpg.add_plot_axis(dpg.mvXAxis, label="Rodada")  # type: ignore

            with dpg.plot_axis(dpg.mvYAxis, label="Saldo (R$)"):  # type: ignore
                self._ids["balance_series"] = dpg.add_line_series(  # type: ignore
                    [],
                    [],
                    label="Saldo",
                )

    def _create_config_tab(self) -> None:
        """Cria conteúdo da tab Configurações."""
        with dpg.group():  # type: ignore
            # Configurações de Estratégia
            with dpg.collapsing_header(  # type: ignore
                label="Estratégia", default_open=True
            ):
                with dpg.group(horizontal=True):  # type: ignore
                    with dpg.group():  # type: ignore
                        dpg.add_text("Threshold (vela baixa):")  # type: ignore
                        self._ids["config_threshold"] = dpg.add_input_float(  # type: ignore
                            default_value=2.0,
                            min_value=1.5,
                            max_value=3.0,
                            step=0.1,
                            width=150,
                        )

                    dpg.add_spacer(width=Spacing.XL)  # type: ignore

                    with dpg.group():  # type: ignore
                        dpg.add_text("Velas necessárias:")  # type: ignore
                        self._ids["config_lows_needed"] = dpg.add_input_int(  # type: ignore
                            default_value=8,
                            min_value=4,
                            max_value=15,
                            width=150,
                        )

                add_vertical_space(dpg.last_container())  # type: ignore

                with dpg.group(horizontal=True):  # type: ignore
                    with dpg.group():  # type: ignore
                        dpg.add_text("Aposta base (divisor):")  # type: ignore
                        self._ids["config_divisor"] = dpg.add_input_int(  # type: ignore
                            default_value=15,
                            min_value=5,
                            max_value=50,
                            width=150,
                        )

                    dpg.add_spacer(width=Spacing.XL)  # type: ignore

                    with dpg.group():  # type: ignore
                        dpg.add_text("Máximo de dobras:")  # type: ignore
                        self._ids["config_max_dobra"] = dpg.add_input_int(  # type: ignore
                            default_value=4,
                            min_value=1,
                            max_value=8,
                            width=150,
                        )

            add_vertical_space(dpg.last_container())  # type: ignore

            # Configurações de Monitor
            with dpg.collapsing_header(label="Monitor", default_open=True):  # type: ignore
                dpg.add_text("Selecione o monitor:")  # type: ignore
                self._ids["config_monitor"] = dpg.add_combo(  # type: ignore
                    items=["Monitor 1", "Monitor 2"],
                    default_value="Monitor 1",
                    width=200,
                )

                add_vertical_space(dpg.last_container())  # type: ignore

                dpg.add_button(  # type: ignore
                    label="🔧 Abrir Calibração",
                    callback=self._on_open_calibration,
                    width=200,
                )

            add_vertical_space(dpg.last_container())  # type: ignore

            # Botões de ação
            with dpg.group(horizontal=True):  # type: ignore
                dpg.add_button(  # type: ignore
                    label="💾 Salvar Configurações",
                    callback=self._on_save_config,
                    width=180,
                )

                dpg.add_button(  # type: ignore
                    label="🔄 Restaurar Padrões",
                    callback=self._on_restore_defaults,
                    width=180,
                )

    def _create_ml_tab(self) -> None:
        """Cria conteúdo da tab Machine Learning."""
        with dpg.group():
            # 1. Status dos modelos
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

            # 2. Decision Engine (Extraído)
            self._create_ml_decision_section()

            add_vertical_space(dpg.last_container())

            # 3. Ações (Extraído anteriormente)
            self._create_ml_training_section()

    def _create_ml_decision_section(self) -> None:
        """Cria a seção de pesos de decisão da aba ML."""
        with dpg.collapsing_header(label="Decision Engine", default_open=True):
            dpg.add_text("Pesos das fontes de decisão:", color=Colors.TEXT_SECONDARY)

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

    def _create_ml_training_section(self) -> None:
        """Cria a seção de treinamento da aba ML."""
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
        with dpg.group(horizontal=True):  # type: ignore
            dpg.add_text("Filtrar:", color=Colors.TEXT_SECONDARY)  # type: ignore
            self._ids["log_filter"] = dpg.add_combo(  # type: ignore
                items=["Todos", "Info", "Warning", "Error", "Success"],
                default_value="Todos",
                width=120,
            )

            dpg.add_spacer(width=-1)  # type: ignore

            dpg.add_button(  # type: ignore
                label="🗑️ Limpar",
                callback=self._on_clear_logs,
                width=100,
            )

        add_vertical_space(dpg.last_container())  # type: ignore

        # Log viewer
        self._ids["log_viewer"] = create_log_viewer(
            parent=dpg.last_container(),  # type: ignore
            height=400,
            max_lines=500,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_footer(self) -> None:
        """Cria footer."""
        with dpg.group(horizontal=True):  # type: ignore
            self._ids["footer_status"] = dpg.add_text(  # type: ignore
                "Pronto",
                color=Colors.TEXT_MUTED,
            )

            dpg.add_spacer(width=-1)  # type: ignore

            dpg.add_text(  # type: ignore
                "© 2024 TucunaréBot",
                color=Colors.TEXT_MUTED,
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _register_events(self) -> None:
        """Registra handlers de eventos."""
        # TODO: Integrar com core.events quando disponível
        # Por enquanto, os handlers são chamados manualmente
        pass

    def handle_explosion(self, value: float) -> None:
        """Handle para nova explosão - chamado externamente."""
        self._explosions.append(value)

        # Atualiza UI
        dpg.set_value(self._ids["last_explosion"], f"{value:.2f}x")  # type: ignore

        color = Colors.SUCCESS if value >= 2.0 else Colors.DANGER
        dpg.configure_item(self._ids["last_explosion"], color=color)  # type: ignore

        # Atualiza histórico
        update_explosion_history(
            self._ids["explosion_history"],
            self._explosions[-30:],
        )

    def handle_bet_placed(self, amount: float, target: float) -> None:
        """Handle para aposta realizada."""
        add_log_line(
            self._ids["log_viewer"],
            f"Aposta: R$ {amount:.2f} @ {target:.2f}x",
            level="info",
        )

    def handle_bet_won(self, profit: float) -> None:
        """Handle para vitória."""
        self._stats["wins"] += 1
        self._update_stats_display()

        # Usando o método self.log existente
        self.log(f"WIN! Lucro: R$ {profit:.2f}", level="success")

    def handle_bet_lost(self, amount: float) -> None:
        """Handle para derrota."""
        self._stats["losses"] += 1
        self._update_stats_display()

        add_log_line(
            self._ids["log_viewer"],
            f"LOSS: -R$ {amount:.2f}",
            level="error",
        )

    def handle_balance_update(self, balance: float) -> None:
        """Handle para atualização de saldo."""
        self._stats["balance"] = balance

        update_stat_card(
            self._ids["balance_card"],
            value=f"R$ {balance:.2f}",
        )

    def handle_trigger_progress(self, current: int, needed: int) -> None:
        """Handle para progresso do gatilho."""
        progress = current / needed if needed > 0 else 0

        update_progress_bar(self._ids["trigger_progress"], progress)
        dpg.set_value(  # type: ignore
            self._ids["trigger_text"], f"{current}/{needed} velas baixas"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CALLBACKS
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_start_click(self) -> None:
        """Callback do botão Iniciar."""
        self._bot_running = True

        # Atualiza UI
        dpg.configure_item(self._ids["btn_start"], enabled=False)  # type: ignore
        dpg.configure_item(self._ids["btn_stop"], enabled=True)  # type: ignore

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

        def confirm_stop() -> None:
            self._bot_running = False

            dpg.configure_item(self._ids["btn_start"], enabled=True)  # type: ignore
            dpg.configure_item(self._ids["btn_stop"], enabled=False)  # type: ignore

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

    def _on_platform_change(self, sender: Any, value: str) -> None:
        """Callback para mudança de plataforma."""
        state = get_state()
        state.session.platform = value
        add_log_line(
            self._ids["log_viewer"],
            f"Plataforma alterada: {value}",
            level="info",
        )

    def _on_risk_change(self, sender: Any, value: str) -> None:
        """Callback para mudança de modo de risco."""
        add_log_line(
            self._ids["log_viewer"],
            f"Modo de risco alterado: {value}",
            level="info",
        )

    def _on_target_change(self, sender: Any, value: float) -> None:
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
        on_start: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        on_config_change: Optional[Callable[[Dict[str, Any]], None]] = None,
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

        while dpg.is_dearpygui_running():  # type: ignore
            dpg.render_dearpygui_frame()  # type: ignore

        self._running = False
        dpg.destroy_context()  # type: ignore

    def stop(self) -> None:
        """Para a aplicação."""
        self._running = False
        dpg.stop_dearpygui()  # type: ignore


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
        exp_value = random.uniform(1.0, 5.0)
        app._explosions.append(round(exp_value, 2))

    app.log("Interface carregada com sucesso!", "success")
    app.run()
