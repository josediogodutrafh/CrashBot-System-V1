#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BOT CONTROLLER - Multi-Setup com Hot-Swap
==========================================

Suporta 4 setups intercambiáveis (1/2, 1/2/4, 1/2/4/8, Inteligente),
metas configuráveis, horários premium e hot-swap via teclado.

Teclas de atalho:
  F1-F4  → Trocar setup
  F5     → Ciclar meta
  F6     → Toggle horários premium
  F9     → Pausar/retomar
  F10    → Encerrar
"""

# ==============================================================================
# IMPORTS
# ==============================================================================
import json
import logging
import os
import random
import threading
import time
import tkinter as tk
import winsound
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import pyautogui
import pyperclip
import pytz
import requests
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.config import PROFILES_PATH, API_URL as CONFIG_API_URL
from src.notifications import telegram as notification_manager
from src.notifications.telegram import (
    notify_meta_reached,
    notify_withdrawal,
    notify_deposit,
    notify_premium_change,
    notify_session_summary,
)
from src.data.manager import (
    RESULTADO_HIT,
    RESULTADO_MISS,
    BetData,
    DatabaseManager,
    RoundData,
)
from src.security.hwid import get_hwid
from src.bot.strategy import StrategyEngine
from src.bot.setups import BaseSetup, SetupInteligente, SETUP_LIST, get_setup
from src.bot.bankroll import BankrollManager, METAS_DISPONIVEIS
from src.bot.schedule import ScheduleManager
from src.bot.menu import (
    HotKeyListener,
    menu_configuracao_completo,
)
from src.ws.capture import CrashWSCapture, GamePhase

# ==============================================================================
# CONSTANTES
# ==============================================================================
API_URL = CONFIG_API_URL
BRASILIA_TZ = pytz.timezone("America/Sao_Paulo")


class TableType(Enum):
    DATABASE_STATS = "DATABASE_STATS"
    STRATEGY_STATS = "STRATEGY_STATS"
    FINANCIAL_SUMMARY = "FINANCIAL_SUMMARY"


# ==============================================================================
# BOT CONTROLLER
# ==============================================================================
class BotController:
    """Controlador principal - Multi-Setup com Hot-Swap."""

    def __init__(
        self,
        config_filename="profiles.json",
        caixa: float = None,
        banca_inicial: float = None,
        setup: BaseSetup = None,
        meta_pct: int = 20,
        premium_only: bool = False,
    ):
        self.console = Console()
        self.config_path = str(PROFILES_PATH)
        self.config = self.load_config()

        # Caixa (reserva total) e Banca (alocacao para apostas)
        self.caixa = caixa or banca_inicial or 500.0
        self.banca_escolhida = banca_inicial

        # Parâmetros do Bot
        bot_params = self.config.get("bot_parameters", {})
        self.cooldown_seconds = bot_params.get("cooldown_seconds", 8)
        self.stop_loss_threshold_pct = bot_params.get("stop_loss_threshold_pct", 0.50)
        self.stop_loss_alerted = False
        self.is_windows = os.name == "nt"

        # Telegram - tenta profiles.json primeiro, senão usa .env (já carregado)
        notification_config = self.config.get("notifications", {})
        token = notification_config.get("telegram_bot_token")
        chat_id = notification_config.get("telegram_chat_id")
        if token and chat_id and "COLE_SEU" not in token:
            notification_manager.load_credentials(token, chat_id)

        # Verifica se as credenciais estão ativas (de qualquer fonte)
        from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        effective_token = notification_manager.BOT_TOKEN or TELEGRAM_BOT_TOKEN
        effective_chat = notification_manager.CHAT_ID or TELEGRAM_CHAT_ID
        if effective_token and effective_chat:
            self.console.print("✅ Alertas do Telegram HABILITADOS", style="green")
        else:
            self.console.print("⚠️ Alertas do Telegram DESABILITADOS", style="yellow")
            self.console.print("   Configure em config/.env", style="dim")

        # Módulos principais
        self.ws_capture = CrashWSCapture(port=9222)
        self.strategy = StrategyEngine()
        self.db_manager = DatabaseManager()

        # Setup e gestão
        self.active_setup = setup
        self.bankroll = BankrollManager(
            caixa=self.caixa,
            banca=banca_inicial or 500.0,
            meta_percent=meta_pct,
        )
        self.schedule = ScheduleManager(premium_only=premium_only)

        # Pausado
        self.paused = False

        # Último estado premium (para detectar transições)
        self._last_premium_state: Optional[bool] = None

        # Estado
        self.running = False
        self.session_start = datetime.now()
        self.explosions = []
        self.round_count = 0
        self.initial_balance = None
        self.current_balance = None
        self.balance_history = []

        # Apostas
        self.executed_bet_pending: Optional[Dict] = None
        self.last_round_id: Optional[int] = None

        # Thread-Safety
        self.balance_lock = threading.Lock()

        # Threads
        self.ws_thread = None
        self.ui_thread = None

        # Áreas (apenas para apostas - opcional)
        self.screen_areas = {}
        self.last_action = ""
        self.selected_profile = ""

        # Logger
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

        self.last_balance_alert_time = time.time()
        self.live_display: Optional[Live] = None

        # Hot-key listener
        self.hotkey_listener: Optional[HotKeyListener] = None

        # Configurar áreas de aposta (opcional - só se quiser executar apostas)
        self.selected_profile = self.setup_screen_areas()

        setup_name = self.active_setup.name if self.active_setup else "N/A"
        self.console.print("✅ BotController inicializado!", style="green")
        self.console.print(f"📊 Sessão: {self.db_manager.session_id}", style="cyan")
        self.console.print(f"🎯 Setup: {setup_name}", style="yellow")
        self.console.print(f"📈 Meta: {meta_pct}%", style="yellow")
        if self.can_execute_bets():
            self.console.print("🎮 Modo: APOSTAS ATIVAS", style="green")
        else:
            self.console.print("👁️ Modo: SOMENTE OBSERVAÇÃO", style="yellow")

    def load_config(self) -> Dict:
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.console.print(f"❌ Erro ao carregar config: {e}", style="red")
            return {}

    def _send_telemetry(self, tipo: str, dados: str = "", lucro: float = 0.0):
        if not self.running:
            return
        endpoint = f"{API_URL}/telemetria/log"
        payload = {
            "hwid": get_hwid(),
            "sessao_id": self.db_manager.session_id,
            "tipo": tipo,
            "dados": dados,
            "lucro": lucro,
        }
        try:
            threading.Thread(
                target=requests.post,
                args=(endpoint,),
                kwargs={"json": payload, "timeout": 5},
            ).start()
        except Exception as e:
            self.logger.warning(f"Falha telemetria: {e}")

    # ── Hot-Swap Callbacks ─────────────────────────────────────────────

    def _on_setup_change(self, setup_name: str):
        """Callback do hot-key para troca de setup."""
        try:
            new_setup = get_setup(setup_name)
            self.strategy.request_swap(new_setup)
            self.active_setup = new_setup
            self.last_action = f"🔄 Troca solicitada → {setup_name}"
        except ValueError as e:
            self.logger.error(f"Setup inválido: {e}")

    def _on_meta_cycle(self):
        """Callback do hot-key para ciclar meta."""
        current = self.bankroll.meta_percent
        idx = METAS_DISPONIVEIS.index(current) if current in METAS_DISPONIVEIS else -1
        next_pct = METAS_DISPONIVEIS[(idx + 1) % len(METAS_DISPONIVEIS)]
        self.bankroll.set_meta(next_pct)
        self.last_action = f"📈 Meta alterada → {next_pct}%"

    def _on_premium_toggle(self):
        """Callback do hot-key para toggle premium."""
        new_state = self.schedule.toggle_premium_mode()
        mode = "PREMIUM" if new_state else "24/7"
        self.last_action = f"⏰ Horário → {mode}"

    def _on_pause(self):
        """Callback do hot-key para pausar/retomar."""
        self.paused = not self.paused
        state = "PAUSADO" if self.paused else "RETOMADO"
        self.last_action = f"⏸️ Bot {state}"

    def _on_stop(self):
        """Callback do hot-key para encerrar."""
        self.last_action = "🛑 Encerrando..."
        self.running = False

    # ── Profile Selection ──────────────────────────────────────────────

    def select_profile(self):
        profiles = self.config.get("profiles", {})
        self.console.print("\nPerfis disponíveis:", style="cyan")
        self.console.print("  [bold yellow]0. 🛠️ CRIAR NOVO PERFIL[/bold yellow]")

        profile_keys = list(profiles.keys())
        for i, profile in enumerate(profile_keys, 1):
            self.console.print(f"  {i}. {profile}", style="white")

        while True:
            try:
                choice = int(self.console.input("\n[green]Selecione o perfil: [/green]"))
                if choice == 0:
                    name, data = self.run_calibration_wizard()
                    if name and data:
                        return name, data
                    continue
                if 1 <= choice <= len(profiles):
                    selected = profile_keys[choice - 1]
                    self.console.print(f"✅ Perfil '{selected}' selecionado", style="green")
                    return selected, profiles[selected]
                self.console.print("Número inválido.", style="red")
            except ValueError:
                self.console.print("Digite um número válido.", style="red")

    def setup_screen_areas(self):
        """Configura áreas de tela para apostas (opcional).

        Com WebSocket, só precisamos das áreas de aposta (bet fields + button).
        Se não houver perfil, o bot opera em modo observação (conta LOWs, não aposta).
        """
        if not self.config:
            return ""

        profiles = self.config.get("profiles", {})
        if not profiles:
            self.console.print(
                "⚠️ Nenhum perfil de tela. Modo observação ativo.",
                style="yellow",
            )
            return ""

        self.console.print(
            "\n[cyan]Deseja configurar perfil de aposta?[/cyan]"
        )
        self.console.print("  [yellow]0. Pular (modo observação)[/yellow]")

        profile_keys = list(profiles.keys())
        for i, profile in enumerate(profile_keys, 1):
            self.console.print(f"  {i}. {profile}", style="white")

        try:
            choice = int(self.console.input("\n[green]Selecione: [/green]"))
            if choice == 0:
                self.console.print("👁️ Modo observação", style="yellow")
                return ""
            if 1 <= choice <= len(profiles):
                selected = profile_keys[choice - 1]
                profile_data = profiles[selected]

                self.screen_areas = {
                    "bet_value_1": profile_data.get("bet_value_area_1"),
                    "target_1": profile_data.get("target_area_1"),
                    "bet_button_1": profile_data.get("bet_button_area_1"),
                }

                self.console.print(
                    f"✅ Perfil '{selected}' carregado (apostas)", style="green"
                )
                return selected
        except (ValueError, IndexError):
            pass

        self.console.print("👁️ Modo observação", style="yellow")
        return ""

    # ── WebSocket Event Callbacks ────────────────────────────────────────

    def _on_round_end(self, data: Dict):
        """Callback: round acabou (crash value recebido via WS).

        Args:
            data: {crash, round_id, duration, begin_time, end_time}
        """
        try:
            # Pausado
            if self.paused:
                return

            # Verificar horário premium
            if not self.schedule.should_operate():
                self._check_premium_transition()
                return

            self._check_premium_transition()

            crash_value = data["crash"]
            round_id = data.get("round_id", 0)
            duration = data.get("duration", 0)

            self.logger.info(
                f"Round {round_id}: crash={crash_value:.2f}x "
                f"(duration={duration}s) [WS]"
            )
            self.process_explosion(crash_value, duration=duration)

        except Exception as e:
            self.logger.error(f"Erro _on_round_end: {e}")

    def _on_balance_update(self, data: Dict):
        """Callback: saldo atualizado via WS.

        Args:
            data: {balance, old_balance, diff}
        """
        try:
            new_balance = data["balance"]

            with self.balance_lock:
                old_balance = self.current_balance or 0.0
                self.current_balance = new_balance
            self.balance_history.append(new_balance)
            change = new_balance - old_balance
            self.last_action = f"💰 Saldo: R${new_balance:.2f} ({change:+.2f})"

            # Sincronizar bankroll manager
            self.bankroll.sync_balance(new_balance)

            # Verificar meta
            if self.bankroll.check_meta_reached():
                profit = self.bankroll.get_net_profit()
                meta_pct = self.bankroll.meta_percent
                notify_meta_reached(profit, meta_pct)
                self.last_action = f"🎯 META ATINGIDA! +{meta_pct}%"

        except Exception as e:
            self.logger.error(f"Erro _on_balance_update: {e}")

    def _on_betting_phase(self, data: Dict):
        """Callback: fase de apostas iniciou.

        Args:
            data: {bet_left_seconds}
        """
        try:
            seconds = data.get("bet_left_seconds", 0)
            self.last_action = f"🎰 Fase apostas: {seconds}s"
        except Exception as e:
            self.logger.error(f"Erro _on_betting_phase: {e}")

    def _on_phase_change(self, data: Dict):
        """Callback: fase do jogo mudou.

        Args:
            data: {old_phase, new_phase}
        """
        try:
            new_phase = data.get("new_phase", "unknown")
            phase_labels = {
                "betting": "🎰 APOSTAS",
                "pre_start": "⏳ PREPARANDO",
                "playing": "📈 JOGANDO",
                "crashed": "💥 CRASH",
                "unknown": "❓ DESCONHECIDO",
            }
            label = phase_labels.get(new_phase, new_phase)
            # Só atualiza last_action se não tiver info mais importante
            if "META" not in self.last_action and "Saldo" not in self.last_action:
                self.last_action = f"Fase: {label}"
        except Exception as e:
            self.logger.error(f"Erro _on_phase_change: {e}")

    def _ws_event_loop(self):
        """Thread principal: registra callbacks e mantém WS captura viva."""
        # Registrar callbacks
        self.ws_capture.on("round_end", self._on_round_end)
        self.ws_capture.on("balance_update", self._on_balance_update)
        self.ws_capture.on("betting_phase", self._on_betting_phase)
        self.ws_capture.on("phase_change", self._on_phase_change)

        # Iniciar captura (cria thread daemon interna do WS)
        self.ws_capture.start()

        # Manter thread viva enquanto bot estiver rodando
        while self.running:
            time.sleep(1)

    def _check_premium_transition(self):
        """Detecta transição premium/regular e notifica."""
        is_premium = self.schedule.is_premium_now()
        if self._last_premium_state is not None and is_premium != self._last_premium_state:
            info = self.schedule.get_current_info()
            notify_premium_change(is_premium, info["hour"], info["day"])

            # Adaptar setup inteligente
            if isinstance(self.active_setup, SetupInteligente):
                strength = self.schedule.get_premium_strength()
                self.active_setup.adapt(is_premium, strength)

        self._last_premium_state = is_premium

    def process_explosion(self, explosion_value: float, duration: int = 0):
        try:
            self.explosions.append({
                "value": explosion_value,
                "timestamp": datetime.now()
            })
            self.round_count += 1
            self.last_action = f"💥 EXPLOSÃO: {explosion_value:.2f}x"

            with self.balance_lock:
                current_balance = self.current_balance or 0.0

            if self.executed_bet_pending:
                self._process_bet_result(explosion_value)

            dados_rodada = RoundData(
                timestamp=datetime.now().isoformat(),
                multiplicador=explosion_value,
                duracao_rodada=float(duration),
                fase_detectada=self.ws_capture.get_game_phase(),
                saldo_momento=current_balance,
                sessao_id=self.db_manager.session_id,
            )
            self.last_round_id = self.db_manager.save_round(dados_rodada)

            triggered, _, msg = self.strategy.add_explosion_value(explosion_value)
            if msg:
                self.last_action += f" | {msg}"

            rec = self.strategy.prepare_bets_for_balance(current_balance)
            if rec:
                self.last_action = f"🎯 {rec.strategy_name}"
                if self.can_execute_bets():
                    self.execute_prepared_bets()

        except Exception as e:
            self.logger.error(f"Erro ao processar explosão: {e}")

    def _process_bet_result(self, explosion_value: float):
        try:
            result = self.strategy.evaluate_executed_bet(
                explosion_value, self.executed_bet_pending
            )
            with self.balance_lock:
                balance = self.current_balance or 0.0

            if result["recommendation_hit"]:
                msg = f"✅ HIT! Alvo: {result['target_1']}x | Saldo: R${balance:.2f}"
                self.trigger_alert("hit", msg)
            else:
                msg = f"❌ MISS! Alvo: {result['target_1']}x | Saldo: R${balance:.2f}"
                self.trigger_alert("miss", msg)

            if self.last_round_id:
                is_hit = result["recommendation_hit"]
                dados_aposta = BetData(
                    rodada_id=self.last_round_id,
                    estrategia=result.get("strategy", ""),
                    aposta_1=result.get("bet_1", 0.0),
                    target_1=result.get("target_1", 0.0),
                    aposta_2=0.0,
                    target_2=0.0,
                    resultado_1=RESULTADO_HIT if is_hit else RESULTADO_MISS,
                    resultado_2=RESULTADO_MISS,
                    lucro_liquido=0.0,
                    timestamp=datetime.now().isoformat(),
                )
                self.db_manager.save_bet(dados_aposta)

        except Exception as e:
            self.logger.error(f"Erro processar resultado: {e}")
        finally:
            self.executed_bet_pending = None

    def can_execute_bets(self) -> bool:
        required = ["bet_value_1", "target_1", "bet_button_1"]
        return all(self.screen_areas.get(area) for area in required)

    def execute_prepared_bets(self):
        try:
            rec = self.strategy.get_prepared_bets()
            if not rec or not rec.ready:
                return

            if self.fill_bet_fields_and_submit(rec.bet_1, rec.target_1):
                self.executed_bet_pending = {
                    "strategy": rec.strategy_name,
                    "bet_1": rec.bet_1,
                    "target_1": rec.target_1,
                }
                self.last_action = f"✅ Apostado R${rec.bet_1:.2f}@{rec.target_1:.2f}x"
                self.strategy.reset_prepared_bets()
        except Exception as e:
            self.logger.error(f"Erro executar aposta: {e}")

    def trigger_alert(self, alert_type: str, message: Optional[str] = None):
        """Alerta sonoro apenas. Telegram é enviado pelo strategy.py (notify_hit/miss/break)."""
        if self.is_windows:
            try:
                if alert_type == "hit":
                    winsound.Beep(1500, 150)
                elif alert_type == "miss":
                    winsound.Beep(700, 300)
                elif alert_type == "break":
                    winsound.Beep(400, 500)
                elif alert_type == "meta":
                    for _ in range(3):
                        winsound.Beep(2000, 200)
                        winsound.Beep(1500, 200)
            except Exception:
                pass

    def fill_bet_fields_and_submit(self, bet_value: float, target: float) -> bool:
        try:
            bet_str = f"{max(1.0, bet_value):.2f}"
            target_str = f"{target:.2f}"

            area_value = self.screen_areas.get("bet_value_1")
            area_target = self.screen_areas.get("target_1")
            area_button = self.screen_areas.get("bet_button_1")

            if not all([area_value, area_target, area_button]):
                return False

            self._click_and_fill(area_value, bet_str)
            time.sleep(random.uniform(0.1, 0.2))
            self._click_and_fill(area_target, target_str)
            time.sleep(random.uniform(0.1, 0.2))
            self._click_area(area_button)
            time.sleep(1.0)

            return True
        except Exception as e:
            self.logger.error(f"Erro ao preencher campos: {e}")
            return False

    def _click_and_fill(self, area: Dict, value: str):
        x = area["x"] + area["width"] // 2
        y = area["y"] + area["height"] // 2
        pyautogui.click(x, y)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("delete")
        time.sleep(0.05)
        pyperclip.copy(value)
        pyautogui.hotkey("ctrl", "v")

    def _click_area(self, area: Dict):
        x = area["x"] + area["width"] // 2
        y = area["y"] + area["height"] // 2
        pyautogui.click(x, y)

    # ── Dashboard UI ───────────────────────────────────────────────────

    def update_ui_continuously(self):
        while self.running:
            try:
                if self.live_display:
                    self.live_display.update(self.build_dashboard_layout())
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Erro UI: {e}")
                time.sleep(1)

    def build_dashboard_layout(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=5),
        )
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        layout["left"].split(
            Layout(name="info", size=12),
            Layout(name="history", ratio=1),
        )
        layout["right"].split(
            Layout(name="strategy", size=14),
            Layout(name="stats", ratio=1),
        )

        layout["header"].update(self._build_header_panel())
        layout["info"].update(self._build_info_panel())
        layout["history"].update(self._build_history_panel())
        layout["strategy"].update(self._build_strategy_panel())
        layout["stats"].update(self._build_stats_panel())
        layout["footer"].update(self._build_footer_panel())

        return layout

    def _build_header_panel(self) -> Panel:
        hora_brasilia = datetime.now(BRASILIA_TZ).strftime("%H:%M:%S")
        analysis = self.strategy.get_current_analysis()
        setup_name = analysis.get("setup_name", "N/A")
        meta_pct = self.bankroll.meta_percent
        progress = self.bankroll.get_meta_progress()

        # Barra de progresso da meta
        bar_len = 10
        filled = int(min(progress, 1.0) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        # Status WS
        ws_connected = self.ws_capture.is_connected()
        ws_phase = self.ws_capture.get_game_phase()

        # Status premium
        premium_info = self.schedule.get_current_info()
        if premium_info["is_premium"]:
            prem_str = "🟢 PREMIUM"
            if premium_info["strength"] == "strong":
                prem_str = "🟢 PREMIUM+"
        else:
            prem_str = "🔴 REGULAR"

        if self.paused:
            prem_str = "⏸️ PAUSADO"

        title = Text()
        title.append("CRASH BOT", style="bold cyan")
        title.append(" | ", style="dim")
        title.append(f"🕐 {hora_brasilia}", style="bold white")
        title.append(" | ", style="dim")

        # WS status indicator
        ws_icon = "🟢" if ws_connected else "🔴"
        title.append(f"{ws_icon} WS:{ws_phase}", style="bold white")
        title.append(" | ", style="dim")

        title.append(f"🎯 {setup_name}", style="bold yellow")
        title.append(" | ", style="dim")
        title.append(f"📈 {meta_pct}% [{bar}] {progress*100:.0f}%", style="bold green")
        title.append(" | ", style="dim")
        title.append(prem_str, style="bold")

        pending = analysis.get("pending_swap")
        if pending:
            title.append(f" | ⏳→{pending}", style="bold magenta")

        return Panel(title, style="cyan")

    def _build_info_panel(self) -> Panel:
        with self.balance_lock:
            balance = self.current_balance or 0.0
            initial = self.initial_balance or 0.0

        profit = balance - initial if initial > 0 else 0.0
        profit_color = "green" if profit >= 0 else "red"

        # Bankroll info
        net_profit = self.bankroll.get_net_profit()
        net_color = "green" if net_profit >= 0 else "red"

        text = Text()
        text.append(
            f"Caixa: R$ {self.bankroll.caixa:.2f} | "
            f"Banca: R$ {self.bankroll.banca:.2f} "
            f"({self.bankroll.n_bancas:.1f}x)\n",
            style="cyan",
        )
        text.append(f"Saldo: R$ {balance:.2f}\n", style="bold white")
        text.append(
            f"Lucro sessao: R$ {profit:+.2f}\n", style=profit_color
        )
        text.append(
            f"Lucro liquido: R$ {net_profit:+.2f}\n", style=net_color
        )
        text.append(f"Rodadas: {self.round_count}\n", style="dim")

        elapsed = (datetime.now() - self.session_start).total_seconds()
        hours = int(elapsed // 3600)
        mins = int((elapsed % 3600) // 60)
        text.append(f"Tempo: {hours}h {mins}m\n", style="dim")

        text.append(
            f"Saques: {self.bankroll.n_withdrawals} "
            f"(R$ {self.bankroll.total_withdrawn:.2f})\n",
            style="dim",
        )
        text.append(
            f"Depositos: {self.bankroll.n_deposits} "
            f"(R$ {self.bankroll.total_deposited:.2f})",
            style="dim",
        )

        return Panel(text, title="Status Financeiro")

    def _build_strategy_panel(self) -> Panel:
        analysis = self.strategy.get_current_analysis()
        setup_name = analysis.get("setup_name", "N/A")
        max_d = analysis.get("max_dobras", 0)
        n_cycles = analysis.get("n_cycles", 1)

        text = Text()
        text.append(f"Setup: {setup_name}\n", style="bold yellow")
        text.append(
            f"Baixas: {analysis['baixos_consecutivos']}\n", style="white"
        )

        is_active = analysis["martingale_active"]
        if is_active:
            dobra = analysis["dobra_atual"]
            cycle_info = analysis.get("cycle_info")
            if cycle_info and n_cycles > 1:
                ci = cycle_info["cycle"]
                tc = cycle_info["total_cycles"]
                text.append(
                    f"Ciclo {ci}/{tc} | Dobra {dobra}/{max_d}\n",
                    style="bold green",
                )
            else:
                text.append(
                    f"Dobra {dobra}/{max_d}\n",
                    style="bold green",
                )
        else:
            text.append("Aguardando gatilho...\n", style="dim")

        # Tabela de apostas por ciclo
        bets_by_cycle = analysis.get("bets_by_cycle", [])
        if bets_by_cycle:
            text.append("\nApostas:\n", style="bold white")
            current_cycle = 0
            for bet in bets_by_cycle:
                if n_cycles > 1 and bet["cycle"] != current_cycle:
                    current_cycle = bet["cycle"]
                    text.append(
                        f"  -- Ciclo {current_cycle} --\n", style="cyan"
                    )

                gpos = bet["global_pos"]
                is_current = is_active and gpos == analysis["dobra_atual"]
                marker = "-> " if is_current else "   "
                style = "bold green" if is_current else "dim"
                text.append(
                    f"{marker}D{bet['pos_in_cycle']}"
                    f" ({bet['multiplier']}x):"
                    f" R$ {bet['value']:.2f}\n",
                    style=style,
                )

        pending = analysis.get("pending_swap")
        if pending:
            text.append(
                f"\nTroca pendente -> {pending}", style="bold magenta"
            )

        return Panel(text, title="Estrategia")

    def _build_stats_panel(self) -> Panel:
        analysis = self.strategy.get_current_analysis()

        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", justify="right", style="white")

        wins_by_dobra = analysis.get("wins_by_dobra", {})
        total_wins = analysis.get("total_wins", 0)
        breaks = analysis.get("total_breaks", 0)
        total_seqs = analysis.get("total_sequences", 0)
        total_profit = analysis.get("total_profit", 0.0)

        table.add_row("📊 Sequências", str(total_seqs))
        table.add_row("✅ Vitórias", str(total_wins))

        for dobra, count in sorted(wins_by_dobra.items()):
            baixas = 5 + dobra
            table.add_row(f"   └─ Dobra {dobra} ({baixas}+ baixas)", str(count))

        table.add_row("💀 Quebras", str(breaks))
        table.add_row("", "")

        total_style = "green" if total_profit >= 0 else "red"
        table.add_row(
            "💰 LUCRO TOTAL",
            f"[bold {total_style}]R$ {total_profit:+.2f}[/bold {total_style}]",
        )

        # Meta
        meta_progress = self.bankroll.get_meta_progress()
        meta_reached = self.bankroll.check_meta_reached()
        meta_str = f"{meta_progress*100:.1f}%"
        if meta_reached:
            meta_str += " ✅ ATINGIDA"
        table.add_row("🎯 Meta", meta_str)

        # WS Capture stats
        ws_stats = self.ws_capture.get_stats()
        table.add_row("", "")
        table.add_row(
            "🔌 WS Frames",
            str(ws_stats.get("frames_received", 0)),
        )
        table.add_row(
            "🎮 WS Rounds",
            str(ws_stats.get("rounds_captured", 0)),
        )
        uptime = ws_stats.get("uptime_seconds", 0)
        table.add_row(
            "⏱️ WS Uptime",
            f"{int(uptime // 60)}m {int(uptime % 60)}s",
        )

        return Panel(table, title="📈 Estatísticas")

    def _build_history_panel(self) -> Panel:
        text = Text()

        history = self.strategy.explosion_history
        ultimos = list(history)[-30:] if history else []

        if not ultimos:
            text.append("Aguardando explosões...", style="dim")
        else:
            for i, valor in enumerate(ultimos):
                if valor < 1.5:
                    cor = "red"
                elif valor < 2.0:
                    cor = "yellow"
                elif valor < 5.0:
                    cor = "green"
                else:
                    cor = "cyan"

                text.append(f"{valor:.2f}x", style=cor)

                if i < len(ultimos) - 1:
                    text.append(" | ", style="dim")

                if (i + 1) % 5 == 0 and i < len(ultimos) - 1:
                    text.append("\n")

        return Panel(text, title="📊 Histórico (últimos 30)")

    def _build_footer_panel(self) -> Panel:
        text = Text()
        text.append(self.last_action + "\n", style="bold white")
        text.append(
            "F1:1/2  F2:1/2+1/2  F3:1/2+1/2+1/2  "
            "F4:1/2/4  F5:1/2/4+1/2/4  F6:1/2/4/8  F7:1/2/4/8/16\n",
            style="dim",
        )
        text.append(
            "F8:Meta  F9:Pausar  F10:Sair",
            style="dim",
        )

        # Horários premium de hoje
        today_hours = self.schedule.get_hours_for_today()
        if today_hours:
            hours_str = ", ".join(f"{h}h" for h in today_hours[:12])
            text.append(f"\nPremium hoje: {hours_str}", style="dim")

        return Panel(text, style="bold white")

    # ── Threads ────────────────────────────────────────────────────────

    def _start_threads(self):
        self.ws_thread = threading.Thread(
            target=self._ws_event_loop, daemon=True, name="ws-events"
        )
        self.ui_thread = threading.Thread(
            target=self.update_ui_continuously, daemon=True, name="ui"
        )

        self.ws_thread.start()
        self.ui_thread.start()

        # Hot-key listener (F1-F7: setups, F8: meta, F9: pausa, F10: sair)
        self.hotkey_listener = HotKeyListener(
            on_setup_change=self._on_setup_change,
            on_meta_cycle=self._on_meta_cycle,
            on_pause=self._on_pause,
            on_stop=self._on_stop,
        )
        self.hotkey_listener.start()

    def _run_main_loop(self):
        self.console.print("🚀 Iniciando Bot...", style="cyan")

        # Conectar ao Chrome DevTools via WebSocket
        self.console.print("🔌 Conectando ao Chrome DevTools...", style="cyan")
        if not self.ws_capture.connect():
            self.console.print(
                "❌ Falha ao conectar ao Chrome!\n"
                "   Verifique se o Chrome está aberto com:\n"
                '   --remote-debugging-port=9222 --remote-allow-origins=*',
                style="red",
            )
            return

        self.console.print("✅ WebSocket conectado ao Chrome!", style="green")

        # Saldo: usa o valor digitado pelo usuário (manual)
        account_balance = self.banca_escolhida or 100.0
        self.console.print(
            f"💰 Saldo inicial (manual): R$ {account_balance:.2f}",
            style="cyan",
        )

        with self.balance_lock:
            self.initial_balance = account_balance
            self.current_balance = account_balance

        # Banca para estratégia
        strategy_bankroll = self.banca_escolhida or account_balance
        self.strategy.iniciar_sessao(strategy_bankroll, self.active_setup)

        self.running = True
        self._start_threads()

        self.live_display = Live(
            self.build_dashboard_layout(),
            console=self.console,
            refresh_per_second=4,
            screen=True,
        )
        self.live_display.start()

        setup_name = self.active_setup.name if self.active_setup else "N/A"
        self.last_action = f"✅ INICIADO! Setup: {setup_name}"

        while self.running:
            time.sleep(1)

    def start(self):
        try:
            self._run_main_loop()
        except KeyboardInterrupt:
            self.last_action = "Encerrando..."
        except Exception as e:
            self.logger.error(f"Erro: {e}")
        finally:
            self.stop()

    def stop(self):
        if not self.running:
            return

        self.running = False
        self.console.print("Encerrando...", style="yellow")

        # Parar WebSocket capture
        try:
            self.ws_capture.stop()
        except Exception:
            pass

        if self.hotkey_listener:
            self.hotkey_listener.stop()

        if self.live_display:
            self.live_display.stop()
            self.console.clear()

        try:
            with self.balance_lock:
                final = self.current_balance
            self.db_manager.close_session(final)
        except Exception:
            pass

        # Enviar resumo via Telegram
        try:
            summary = self.bankroll.get_session_summary()
            notify_session_summary(summary)
        except Exception:
            pass

        self.show_summary()

    def show_summary(self):
        self.console.clear()
        duration = datetime.now() - self.session_start

        analysis = self.strategy.get_current_analysis()
        bank_summary = self.bankroll.get_session_summary()

        text = Text()
        text.append("=" * 55 + "\n", style="cyan")
        text.append("📊 RESUMO FINAL DA SESSÃO\n", style="bold cyan")
        text.append("=" * 55 + "\n", style="cyan")

        text.append(f"\n⏱️ Duração: {int(duration.total_seconds() // 60)} minutos\n")
        text.append(f"💥 Explosões: {len(self.explosions)}\n")
        text.append(f"🎯 Setup: {analysis.get('setup_name', 'N/A')}\n")

        with self.balance_lock:
            inicial = self.initial_balance or 0
            final = self.current_balance or 0

        profit = final - inicial
        color = "green" if profit >= 0 else "red"
        text.append(f"\n💰 Saldo Inicial: R$ {inicial:.2f}\n")
        text.append(f"💰 Saldo Final: R$ {final:.2f}\n")
        text.append("📈 Lucro Sessão: ", style="white")
        text.append(f"R$ {profit:+.2f}\n", style=color)

        net = bank_summary["net_profit"]
        net_color = "green" if net >= 0 else "red"
        text.append("📊 Lucro Líquido: ", style="white")
        text.append(f"R$ {net:+.2f}\n", style=net_color)

        text.append(f"\n💳 Total Sacado: R$ {bank_summary['total_withdrawn']:.2f}\n")
        text.append(f"💳 Total Depositado: R$ {bank_summary['total_deposited']:.2f}\n")
        text.append(f"💳 Saques: {bank_summary['n_withdrawals']}\n")
        text.append(f"💳 Depósitos: {bank_summary['n_deposits']}\n")

        if bank_summary["total_deposited"] > 0:
            roi = bank_summary["roi"]
            text.append(f"📊 ROI: {roi:+.1f}%\n", style=net_color)

        text.append("\n" + "=" * 55 + "\n", style="yellow")
        text.append("🎯 ESTATÍSTICAS\n", style="bold yellow")
        text.append("=" * 55 + "\n", style="yellow")

        wins_by_dobra = analysis.get("wins_by_dobra", {})
        total_wins = analysis.get("total_wins", 0)
        breaks = analysis.get("total_breaks", 0)
        total_profit = analysis.get("total_profit", 0.0)

        text.append(f"\n✅ Vitórias: {total_wins}\n", style="green")
        for dobra, count in sorted(wins_by_dobra.items()):
            baixas = 5 + dobra
            text.append(f"   Dobra {dobra} ({baixas}+ baixas): {count}\n")

        text.append(f"\n💀 Quebras: {breaks}\n", style="red")

        tp_color = "green" if total_profit >= 0 else "red"
        text.append(f"💰 Lucro estratégia: ", style="white")
        text.append(f"R$ {total_profit:+.2f}\n", style=tp_color)

        self.console.print(Panel(text, title="Resumo da Sessão", border_style="cyan"))
        self.console.input("\n[cyan]Pressione Enter para sair...[/cyan]")

    # ── Calibration Wizard ─────────────────────────────────────────────

    def run_calibration_wizard(self):
        self.console.clear()
        self.console.print(
            Panel(
                "[bold yellow]CALIBRAÇÃO VISUAL[/bold yellow]\n"
                "[white]Arraste o mouse para selecionar as áreas[/white]",
                border_style="yellow"
            )
        )

        profile_name = self.console.input(
            "\n[cyan]Nome do perfil: [/cyan]"
        ) or f"Perfil_{int(time.time())}"

        self.console.print("\n[green]Instruções:[/green]")
        self.console.print("  • Uma tela escura vai aparecer")
        self.console.print("  • CLIQUE e ARRASTE para selecionar a área")
        self.console.print("  • ESC para cancelar")
        self.console.input("\n[yellow]Pressione ENTER para começar...[/yellow]")

        items = [
            ("bet_value_area_1", "CAMPO VALOR DA APOSTA"),
            ("target_area_1", "CAMPO TARGET (multiplicador alvo)"),
            ("bet_button_area_1", "BOTÃO APOSTAR"),
        ]

        new_profile = {}
        for key, name in items:
            self.console.print(f"\n[cyan]>>> Selecione: {name}[/cyan]")
            result = self._select_area_visual(name)

            if result:
                new_profile[key] = result
                self.console.print(
                    f"[green]✅ OK: {result['width']}x{result['height']}[/green]"
                )
            else:
                self.console.print("[red]❌ Cancelado[/red]")
                return None, None

        try:
            if "profiles" not in self.config:
                self.config["profiles"] = {}
            self.config["profiles"][profile_name] = new_profile

            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)

            self.console.print(
                f"\n[bold green]✅ Perfil '{profile_name}' criado![/bold green]"
            )
            return profile_name, new_profile
        except Exception as e:
            self.console.print(f"[red]❌ Erro: {e}[/red]")
            return None, None

    def _select_area_visual(self, title):
        result = {"x": 0, "y": 0, "width": 0, "height": 0}

        def on_press(event):
            nonlocal start_x, start_y
            start_x = event.x
            start_y = event.y
            if rect[0]:
                canvas.delete(rect[0])
            rect[0] = canvas.create_rectangle(
                start_x, start_y, start_x, start_y,
                outline='#00FF00', width=3
            )

        def on_drag(event):
            if rect[0]:
                canvas.coords(rect[0], start_x, start_y, event.x, event.y)

        def on_release(event):
            x1 = min(start_x, event.x)
            y1 = min(start_y, event.y)
            x2 = max(start_x, event.x)
            y2 = max(start_y, event.y)

            width = x2 - x1
            height = y2 - y1

            if width > 5 and height > 5:
                result["x"] = x1
                result["y"] = y1
                result["width"] = width
                result["height"] = height

            root.quit()
            root.destroy()

        def on_cancel(event):
            result["width"] = 0
            root.quit()
            root.destroy()

        start_x, start_y = 0, 0
        rect = [None]

        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-alpha', 0.3)
        root.attributes('-topmost', True)
        root.configure(bg='black')

        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        canvas = tk.Canvas(
            root, width=screen_w, height=screen_h,
            bg='black', highlightthickness=0, cursor='cross'
        )
        canvas.pack()

        canvas.create_text(
            screen_w // 2, 40,
            text=f"🎯 {title}",
            font=('Arial', 28, 'bold'), fill='white'
        )
        canvas.create_text(
            screen_w // 2, 80,
            text="CLIQUE e ARRASTE para selecionar | ESC = cancelar",
            font=('Arial', 16), fill='yellow'
        )

        canvas.bind('<ButtonPress-1>', on_press)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        root.bind('<Escape>', on_cancel)

        root.mainloop()

        if result["width"] > 0:
            return result
        return None


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    console = Console()
    bot = None

    try:
        console.clear()
        console.print(
            Panel(
                Text("CRASH BOT - Multi-Setup com Hot-Swap", justify="center"),
                style="cyan bold"
            )
        )
        console.print()
        console.print("Gatilho: 6 baixas consecutivas", style="yellow")
        console.print("Target: 1.90x - 2.05x (randomico)", style="yellow")
        console.print("Hot-swap: F1-F7 durante execucao", style="yellow")
        console.print()

        # Menu de configuracao completo
        config = menu_configuracao_completo(console)

        console.print()
        console.input("[green]Pressione Enter para iniciar o bot...[/green]")

        bot = BotController(
            caixa=config["caixa"],
            banca_inicial=config["banca"],
            setup=config["setup"],
            meta_pct=config["meta_pct"],
            premium_only=config["premium_only"],
        )
        bot.start()

    except KeyboardInterrupt:
        console.print("\nInterrompido pelo usuário.", style="yellow")
    except Exception:
        console.print_exception()
    finally:
        if bot and bot.running:
            bot.stop()
        console.print("\nBot encerrado.", style="green")


if __name__ == "__main__":
    main()
