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
import sys
import threading
import time
import tkinter as tk
import winsound
from datetime import datetime, timedelta
from typing import Dict, Optional

import pyautogui
import pyperclip
import pytz
import requests

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
from src.bot.setups import BaseSetup, SetupInteligente, SETUP_LIST
from src.gui.app_mode import get_setup, get_display_name
from src.bot.bankroll import BankrollManager
from src.bot.calibration import get_profile, validate_profile, load_profiles
from src.bot.schedule import ScheduleManager
from src.bot.menu import HotKeyListener
from src.ws.capture import CrashWSCapture, GamePhase

# ==============================================================================
# CONSTANTES
# ==============================================================================
API_URL = CONFIG_API_URL
BRASILIA_TZ = pytz.timezone("America/Sao_Paulo")


logger = logging.getLogger(__name__)


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
        meta_pct: float = 20,
        stop_loss_pct: float = 100,
        session_hours: float = 0,
        gain_action: str = "encerrar",
        gain_suspend_hours: float = 0,
        gain_reinvest_pct: float = 0,
        loss_action: str = "encerrar",
        loss_suspend_hours: float = 0,
        premium_only: bool = False,
        headless: bool = False,
        profile_name: str = "",
    ):
        self.logger = logging.getLogger(__name__)
        self.headless = headless
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
            logger.info("Alertas do Telegram HABILITADOS")
        else:
            logger.info("Alertas do Telegram DESABILITADOS")

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
            stop_loss_percent=stop_loss_pct,
        )
        self.schedule = ScheduleManager(premium_only=premium_only)

        # Duracao da sessao (0 = sem limite)
        self.session_hours = session_hours

        # Acoes ao atingir stop gain/loss
        self.gain_action = gain_action              # encerrar/suspender/reinvestir
        self.gain_suspend_hours = gain_suspend_hours
        self.gain_reinvest_pct = gain_reinvest_pct
        self.loss_action = loss_action              # encerrar/suspender
        self.loss_suspend_hours = loss_suspend_hours

        # Controle de suspensao
        self._suspended_until: Optional[datetime] = None

        # Pausado
        self.paused = False

        # Último estado premium (para detectar transições)
        self._last_premium_state: Optional[bool] = None

        # Estado
        self.running = False
        self._stop_requested = False  # set by _on_stop, checked during connection
        self.session_start = datetime.now()
        self.explosions = []
        self.round_count = 0
        self.initial_balance = None
        self.current_balance = None
        self.balance_history = []

        # Apostas
        self.executed_bet_pending: Optional[Dict] = None
        self.last_round_id: Optional[int] = None

        # Flag: primeiro saldo WS recebido (para ajustar bankroll_base)
        self._ws_balance_initialized = False

        # Controle de apostas da sessao
        self.session_hits = 0
        self.session_misses = 0
        self.session_profit = 0.0  # lucro/prejuizo acumulado em R$

        # Thread-Safety
        self.balance_lock = threading.Lock()

        # Threads
        self.ws_thread = None
        self.ui_thread = None

        # Áreas (apenas para apostas - opcional)
        self.screen_areas = {}
        self.last_action = ""
        self.selected_profile = ""

        # Logger (basicConfig only for non-frozen standalone mode)
        if not getattr(sys, "frozen", False):
            logging.basicConfig(
                level=logging.WARNING,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        self.last_balance_alert_time = time.time()

        # Hot-key listener
        self.hotkey_listener: Optional[HotKeyListener] = None

        # Configurar áreas de aposta
        if not self.headless:
            self.selected_profile = self.setup_screen_areas()
        elif profile_name:
            # Headless (GUI Flet): carregar perfil especifico selecionado na config
            self.selected_profile = self._load_named_profile(profile_name)
        else:
            # Headless sem perfil: carregar primeiro perfil automaticamente
            self.selected_profile = self._load_default_profile()

        setup_raw = self.active_setup.name if self.active_setup else "N/A"
        setup_display = get_display_name(setup_raw)
        self.logger.info(f"BotController inicializado! Sessao: {self.db_manager.session_id}")
        self.logger.info(f"Estrategia: {setup_display} ({setup_raw})")

    def load_config(self) -> Dict:
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar config: {e}")
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
            display = get_display_name(setup_name)
            self.last_action = f"Troca: {display} ({setup_name})"
        except ValueError as e:
            self.logger.error(f"Setup inválido: {e}")

    def _on_meta_cycle(self):
        """Callback do hot-key para ciclar meta (+10% a cada F8)."""
        current = self.bankroll.meta_percent
        next_pct = current + 10
        if next_pct > 100:
            next_pct = 10
        self.bankroll.set_meta(next_pct)
        valor = self.bankroll.meta_value
        self.last_action = f"Meta alterada → {next_pct:.0f}% (R$ {valor:.2f})"

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
        """Callback do hot-key/GUI para encerrar."""
        self.last_action = "Encerrando..."
        self.running = False
        self._stop_requested = True

    # ── Profile Selection ──────────────────────────────────────────────

    def select_profile(self):
        profiles = self.config.get("profiles", {})
        print("\nPerfis disponiveis:")
        print("  0. NOVA CALIBRAGEM")

        profile_keys = list(profiles.keys())
        for i, profile in enumerate(profile_keys, 1):
            dados = profiles[profile]
            campos = len([v for v in dados.values() if v])
            print(f"  {i}. {profile} ({campos} campos)")

        while True:
            try:
                choice = int(input("\nSelecione o perfil: "))
                if choice == 0:
                    name, data = self.run_calibration_wizard()
                    if name and data:
                        return name, data
                    continue
                if 1 <= choice <= len(profiles):
                    selected = profile_keys[choice - 1]
                    print(f"Perfil '{selected}' selecionado")
                    return selected, profiles[selected]
                print("Numero invalido.")
            except ValueError:
                print("Digite um numero valido.")

    def setup_screen_areas(self):
        """Configura areas de tela para apostas (opcional).

        Com WebSocket, so precisamos de 3 areas:
          - Campo valor da aposta
          - Campo multiplicador alvo
          - Botao apostar

        Se nao houver perfil, o bot opera em modo observacao.
        """
        if not self.config:
            return ""

        profiles = self.config.get("profiles", {})

        print("\nConfigurar perfil de aposta:")
        print("  0. Pular (modo observacao)")
        print("  N. NOVA CALIBRAGEM")

        profile_keys = list(profiles.keys())
        for i, profile in enumerate(profile_keys, 1):
            dados = profiles[profile]
            campos = len([v for v in dados.values() if v])
            print(f"  {i}. {profile} ({campos} campos)")

        try:
            entrada = input("\nSelecione (numero ou N): ").strip().upper()

            if entrada == "N":
                name, data = self.run_calibration_wizard()
                if name and data:
                    self.screen_areas = {
                        "bet_value_1": data.get("bet_value_area_1"),
                        "target_1": data.get("target_area_1"),
                        "bet_button_1": data.get("bet_button_area_1"),
                    }
                    print(f"Perfil '{name}' criado e carregado!")
                    return name
                print("Modo observacao")
                return ""

            choice = int(entrada)
            if choice == 0:
                print("Modo observacao")
                return ""
            if 1 <= choice <= len(profile_keys):
                selected = profile_keys[choice - 1]
                profile_data = profiles[selected]

                self.screen_areas = {
                    "bet_value_1": profile_data.get("bet_value_area_1"),
                    "target_1": profile_data.get("target_area_1"),
                    "bet_button_1": profile_data.get("bet_button_area_1"),
                }

                print(f"Perfil '{selected}' carregado")
                return selected
        except (ValueError, IndexError):
            pass

        print("Modo observacao")
        return ""

    def _load_named_profile(self, name: str) -> str:
        """Carrega um perfil especifico pelo nome (via calibration module)."""
        profile_data = get_profile(name)
        if not profile_data or not validate_profile(profile_data):
            self.logger.warning(f"Perfil '{name}' invalido - modo observacao")
            return ""

        self.screen_areas = {
            "bet_value_1": profile_data.get("bet_value_area_1"),
            "target_1": profile_data.get("target_area_1"),
            "bet_button_1": profile_data.get("bet_button_area_1"),
        }

        if self.can_execute_bets():
            self.logger.info(f"Perfil '{name}' carregado (via GUI)")
            return name

        self.screen_areas = {}
        return ""

    def _load_default_profile(self) -> str:
        """Carrega o primeiro perfil de calibracao automaticamente (headless)."""
        profiles = load_profiles()
        if not profiles:
            self.logger.warning("Nenhum perfil calibrado - modo observacao")
            return ""

        # Usar o primeiro perfil disponivel
        profile_name = list(profiles.keys())[0]
        return self._load_named_profile(profile_name)

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

            # Primeiro saldo WS: ajustar bankroll_base para o saldo
            # REAL da conta (evita stop gain falso)
            if not self._ws_balance_initialized:
                self._ws_balance_initialized = True
                self.logger.info(
                    f"Primeiro saldo WS: R${new_balance:.2f} "
                    f"(ajustando bankroll_base)"
                )
                with self.balance_lock:
                    self.initial_balance = new_balance
                    self.current_balance = new_balance
                self.bankroll.bankroll_base = new_balance
                self.bankroll.current_bankroll = new_balance
                self.bankroll.session_start_balance = new_balance
                self.balance_history.append(new_balance)
                self.last_action = (
                    f"Saldo detectado: R${new_balance:.2f}"
                )
                return

            with self.balance_lock:
                old_balance = self.current_balance or 0.0
                self.current_balance = new_balance
            self.balance_history.append(new_balance)
            change = new_balance - old_balance
            self.last_action = (
                f"Saldo: R${new_balance:.2f} "
                f"({change:+.2f})"
            )

            # Sincronizar bankroll manager
            self.bankroll.sync_balance(new_balance)

            # Verificar meta
            if self.bankroll.check_meta_reached():
                profit = self.bankroll.get_net_profit()
                meta_pct = self.bankroll.meta_percent
                notify_meta_reached(profit, meta_pct)
                self.last_action = (
                    f"META ATINGIDA! +{meta_pct}%"
                )

        except Exception as e:
            self.logger.error(
                f"Erro _on_balance_update: {e}"
            )

    def _on_betting_phase(self, data: Dict):
        """Callback: fase de apostas iniciou.

        Este é o momento correto para executar apostas preparadas,
        pois o formulário de aposta está ativo na tela.

        Args:
            data: {bet_left_seconds}
        """
        try:
            seconds = data.get("bet_left_seconds", 0)
            self.last_action = f"🎰 Fase apostas: {seconds}s"

            # Executar aposta preparada (se houver e nao suspenso)
            rec = self.strategy.get_prepared_bets()
            if rec and rec.ready and not self.paused:
                if self.can_execute_bets():
                    # Pequeno delay para garantir que o formulario esta renderizado
                    time.sleep(0.5)
                    self.execute_prepared_bets()
                else:
                    self.logger.warning(
                        f"Aposta preparada mas screen_areas vazio! "
                        f"Perfil: '{self.selected_profile}' | "
                        f"Areas: {list(self.screen_areas.keys())}"
                    )
                    self.last_action = "⚠️ Sem calibracao - aposta nao executada"

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
        self.logger.info("_ws_event_loop: registrando callbacks...")
        # Registrar callbacks
        self.ws_capture.on("round_end", self._on_round_end)
        self.ws_capture.on("balance_update", self._on_balance_update)
        self.ws_capture.on("betting_phase", self._on_betting_phase)
        self.ws_capture.on("phase_change", self._on_phase_change)

        # Iniciar captura (cria thread daemon interna do WS)
        try:
            self.logger.info("_ws_event_loop: chamando ws_capture.start()...")
            self.ws_capture.start()
            self.logger.info("_ws_event_loop: ws_capture.start() OK")
        except Exception as e:
            self.logger.error(f"_ws_event_loop: ws_capture.start() FALHOU: {e}")
            self.last_action = f"ERRO: Falha ao iniciar captura: {e}"
            self.running = False
            return

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
                self.last_action = f"🎯 {rec.strategy_name} (aguardando fase apostas)"

        except Exception as e:
            self.logger.error(f"Erro ao processar explosão: {e}")

    def _process_bet_result(self, explosion_value: float):
        try:
            result = self.strategy.evaluate_executed_bet(
                explosion_value, self.executed_bet_pending
            )
            with self.balance_lock:
                balance = self.current_balance or 0.0

            bet_amount = result.get("bet_1", 0.0)
            target = result.get("target_1", 0.0)
            is_hit = result["recommendation_hit"]

            # Calcular lucro/prejuizo real da aposta
            if is_hit:
                # HIT: ganho = valor apostado * (multiplicador - 1)
                bet_profit = bet_amount * (target - 1)
                self.session_hits += 1
                msg = (
                    f"HIT! {target}x | "
                    f"+R${bet_profit:.2f} | Saldo: R${balance:.2f}"
                )
                self.trigger_alert("hit", msg)
            else:
                # MISS: perda = valor apostado
                bet_profit = -bet_amount
                self.session_misses += 1
                msg = (
                    f"MISS! {target}x | "
                    f"-R${bet_amount:.2f} | Saldo: R${balance:.2f}"
                )
                self.trigger_alert("miss", msg)

            self.session_profit += bet_profit

            if self.last_round_id:
                dados_aposta = BetData(
                    rodada_id=self.last_round_id,
                    estrategia=result.get("strategy", ""),
                    aposta_1=bet_amount,
                    target_1=target,
                    aposta_2=0.0,
                    target_2=0.0,
                    resultado_1=RESULTADO_HIT if is_hit else RESULTADO_MISS,
                    resultado_2=RESULTADO_MISS,
                    lucro_liquido=bet_profit,
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

    # ── Dashboard UI (removed - now handled by src/gui/) ─────────────
    # ── Threads ────────────────────────────────────────────────────────

    def _start_threads(self):
        self.ws_thread = threading.Thread(
            target=self._ws_event_loop, daemon=True, name="ws-events"
        )
        self.ws_thread.start()

        # Hot-key listener (F1-F7: setups, F8: meta, F9: pausa, F10: sair)
        if not self.headless:
            self.hotkey_listener = HotKeyListener(
                on_setup_change=self._on_setup_change,
                on_meta_cycle=self._on_meta_cycle,
                on_pause=self._on_pause,
                on_stop=self._on_stop,
            )
            self.hotkey_listener.start()

    def _is_gui_stop_requested(self) -> bool:
        """Check if user clicked stop during connection setup."""
        return self._stop_requested

    def _run_main_loop(self):
        self.logger.info("=== _run_main_loop INICIANDO ===")
        self.last_action = "[1/3] Verificando Chrome com debug port..."

        # ── FASE 1: Garantir Chrome com debug port ────────────────
        self.logger.info("FASE 1: Verificando Chrome...")

        # Passo 1: Tentar lançar Chrome UMA VEZ (pode matar e relançar)
        if not self.ws_capture._is_chrome_debug_running():
            self.last_action = "[1/3] Lancando Chrome com debug port..."
            self.logger.info("FASE 1: Chrome debug nao detectado, lancando...")
            self.ws_capture.ensure_chrome_running()
            # ensure_chrome_running pode demorar ~20s (kill + launch + wait)

        # Passo 2: Aguardar Chrome responder na porta (max 90s)
        # NÃO chama ensure_chrome_running de novo (evita matar Chrome do usuario)
        start = time.time()
        max_wait = 90
        while not self.ws_capture._is_chrome_debug_running():
            if self._is_gui_stop_requested():
                self.logger.info("FASE 1: Stop requested")
                return

            elapsed = int(time.time() - start)
            remaining = max_wait - elapsed
            err = self.ws_capture.last_error
            if err:
                self.last_action = f"[1/3] {err} ({remaining}s)"
            else:
                self.last_action = (
                    f"[1/3] Aguardando Chrome debug port... ({remaining}s)"
                )

            if elapsed >= max_wait:
                self.last_action = (
                    "ERRO: Chrome nao respondeu na porta 9222. "
                    "Feche TODO o Chrome e tente novamente."
                )
                self.logger.error(f"FASE 1 FALHOU apos {elapsed}s")
                return

            time.sleep(2)

        self.last_action = "[1/3] Chrome OK! Buscando aba do jogo..."
        self.logger.info("FASE 1 OK: Chrome com debug port rodando")

        # ── FASE 2: Aguardar aba do jogo (max 3 min) ───────────────
        self.logger.info("FASE 2: Buscando aba do jogo...")
        max_tab_wait = 180  # seconds
        elapsed = 0
        while not self.ws_capture.has_game_tab():
            if self._is_gui_stop_requested():
                self.logger.info("FASE 2: Stop requested")
                return
            remaining = max_tab_wait - elapsed
            self.last_action = (
                f"[2/3] Abra o jogo Crash no Chrome! "
                f"({remaining}s restantes)"
            )
            time.sleep(3)
            elapsed += 3
            if elapsed >= max_tab_wait:
                self.last_action = (
                    "ERRO: Jogo nao encontrado no Chrome! "
                    "Abra o site crash/brabet no Chrome."
                )
                self.logger.error(
                    "FASE 2 FALHOU: Aba do jogo nao encontrada apos 3 min"
                )
                return

        self.last_action = "[2/3] Aba do jogo encontrada! Conectando WebSocket..."
        self.logger.info("FASE 2 OK: Aba do jogo encontrada")

        # ── FASE 3: Conectar DevTools (max 5 tentativas) ───────────
        self.logger.info("FASE 3: Conectando DevTools...")
        connected = False
        for attempt in range(1, 6):
            if self._is_gui_stop_requested():
                self.logger.info("FASE 3: Stop requested")
                return
            self.last_action = (
                f"[3/3] Conectando WebSocket... (tentativa {attempt}/5)"
            )
            self.logger.info(f"FASE 3: tentativa {attempt}/5")
            if self.ws_capture.connect():
                connected = True
                break
            self.logger.warning(
                f"FASE 3: tentativa {attempt} falhou: "
                f"{self.ws_capture.last_error}"
            )
            time.sleep(3)

        if not connected:
            ws_err = self.ws_capture.last_error or "falha desconhecida"
            self.last_action = f"ERRO: {ws_err}"
            self.logger.error(f"FASE 3 FALHOU: {ws_err}")
            return

        self.logger.info("=== FASE 3 OK: WebSocket conectado! ===")
        self.last_action = "WebSocket conectado! Iniciando captura..."

        # Saldo: usa o valor digitado pelo usuário (manual)
        account_balance = self.banca_escolhida or 100.0
        self.logger.info(f"Saldo inicial (manual): R$ {account_balance:.2f}")

        with self.balance_lock:
            self.initial_balance = account_balance
            self.current_balance = account_balance

        # Banca para estratégia
        strategy_bankroll = self.banca_escolhida or account_balance
        self.strategy.iniciar_sessao(strategy_bankroll, self.active_setup)

        self.running = True
        self.logger.info("Iniciando threads (ws_event_loop + hotkeys)...")
        self._start_threads()
        self.logger.info("Threads iniciadas OK")

        setup_raw = self.active_setup.name if self.active_setup else "N/A"
        setup_display = get_display_name(setup_raw)
        self.last_action = f"INICIADO! Estrategia: {setup_display}"

        while self.running:
            time.sleep(1)
            self._check_session_limits()

    def _check_session_limits(self):
        """Verifica limites de sessao: tempo, stop gain, stop loss, suspensao."""

        # Se esta suspenso, verifica se ja pode retomar
        if self._suspended_until:
            if datetime.now() >= self._suspended_until:
                self._suspended_until = None
                self.paused = False
                self.last_action = "Suspensao encerrada - retomando!"
                self.logger.info("Suspensao encerrada, retomando apostas")
            else:
                remaining = (
                    self._suspended_until - datetime.now()
                ).total_seconds()
                rm = int(remaining // 60)
                self.last_action = (
                    f"SUSPENSO (retoma em {rm} min)"
                )
            return

        # Tempo limite da sessao
        if self.session_hours > 0:
            elapsed = (datetime.now() - self.session_start).total_seconds()
            limit_seconds = self.session_hours * 3600
            if elapsed >= limit_seconds:
                self.last_action = (
                    f"TEMPO LIMITE ({self.session_hours:.1f}h) - "
                    "Encerrando..."
                )
                self.running = False
                return

        # Stop gain (meta de lucro)
        if self.bankroll.check_meta_reached():
            self._handle_stop_gain()
            return

        # Stop loss (perda maxima)
        if self.bankroll.check_stop_loss():
            self._handle_stop_loss()
            return

    def _handle_stop_gain(self):
        """Executa a acao configurada para stop gain."""
        lucro = self.bankroll.current_bankroll - self.bankroll.bankroll_base
        self.logger.info(
            f"STOP GAIN atingido! Lucro: R$ {lucro:.2f} | "
            f"Acao: {self.gain_action}"
        )

        if self.gain_action == "suspender":
            hrs = self.gain_suspend_hours
            self._suspended_until = datetime.now() + timedelta(hours=hrs)
            self.paused = True
            self.last_action = (
                f"STOP GAIN! Suspenso por {hrs:.1f}h"
            )

        elif self.gain_action == "reinvestir":
            pct = self.gain_reinvest_pct
            reinvest = round(lucro * pct / 100, 2)
            # Saca o lucro, reinveste parte
            self.bankroll.execute_withdrawal()
            self.bankroll.update_balance(reinvest)
            self.last_action = (
                f"STOP GAIN! Reinvestindo {pct:.0f}% = "
                f"R$ {reinvest:.2f}"
            )
            self.logger.info(
                f"Reinvestido R$ {reinvest:.2f} ({pct:.0f}% do lucro)"
            )

        else:  # encerrar
            self.last_action = "STOP GAIN atingido! Encerrando..."
            self.running = False

    def _handle_stop_loss(self):
        """Executa a acao configurada para stop loss."""
        perda = self.bankroll.bankroll_base - self.bankroll.current_bankroll
        self.logger.info(
            f"STOP LOSS atingido! Perda: R$ {perda:.2f} | "
            f"Acao: {self.loss_action}"
        )

        if self.loss_action == "suspender":
            hrs = self.loss_suspend_hours
            self._suspended_until = datetime.now() + timedelta(hours=hrs)
            self.paused = True
            self.last_action = (
                f"STOP LOSS! Suspenso por {hrs:.1f}h"
            )

        else:  # encerrar
            self.last_action = (
                f"STOP LOSS ({self.bankroll.stop_loss_percent:.0f}%) - "
                "Encerrando..."
            )
            self.running = False

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
        self.logger.info("Encerrando...")
        self.last_action = "Encerrando..."

        # Parar WebSocket capture
        try:
            self.ws_capture.stop()
        except Exception:
            pass

        if self.hotkey_listener:
            self.hotkey_listener.stop()

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

        self.logger.info("Bot encerrado.")

    # ── Calibration Wizard ─────────────────────────────────────────────

    def run_calibration_wizard(self):
        print("\n" + "=" * 50)
        print("CALIBRAGEM DE TELA")
        print("Arraste o mouse para selecionar cada campo")
        print("=" * 50)

        profile_name = input("\nNome do perfil: ") or f"Perfil_{int(time.time())}"

        print("\nComo funciona:")
        print("  1. Uma tela escura semi-transparente vai aparecer")
        print("  2. CLIQUE e ARRASTE para selecionar o campo")
        print("  3. ESC para cancelar")
        print("\nCampos a calibrar:")
        print("  - Campo de VALOR DA APOSTA (onde digitar R$)")
        print("  - Campo de MULTIPLICADOR ALVO (onde digitar 2.00x)")
        print("  - BOTAO APOSTAR (onde clicar para confirmar)")
        input("\nPressione ENTER para comecar...")

        items = [
            ("bet_value_area_1", "CAMPO VALOR DA APOSTA (R$)"),
            ("target_area_1", "CAMPO MULTIPLICADOR ALVO (2.00x)"),
            ("bet_button_area_1", "BOTÃO APOSTAR"),
        ]

        new_profile = {}
        for key, name in items:
            print(f"\n>>> Selecione: {name}")
            result = self._select_area_visual(name)

            if result:
                new_profile[key] = result
                print(f"OK: {result['width']}x{result['height']}")
            else:
                print("Cancelado")
                return None, None

        try:
            if "profiles" not in self.config:
                self.config["profiles"] = {}
            self.config["profiles"][profile_name] = new_profile

            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)

            print(f"\nPerfil '{profile_name}' criado!")
            return profile_name, new_profile
        except Exception as e:
            print(f"Erro: {e}")
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
            text="CLIQUE e ARRASTE para selecionar a area | ESC = cancelar",
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
# MAIN - Entry point now in src/gui/app.py
# ==============================================================================
def main():
    """Launch the bot via the Dear PyGui interface."""
    from src.gui.app import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
