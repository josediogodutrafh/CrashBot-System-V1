#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BOT CONTROLLER - ML (Versão Comercial com Modos de Risco)
"""

# ==============================================================================
# 1. IMPORTS DE BIBLIOTECAS PADRÃO
# ==============================================================================
import json
import logging
import os
import random
import sys
import threading
import time
import winsound
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Union

# ==============================================================================
# 2. IMPORTS DE TERCEIROS (PIP)
# ==============================================================================
import numpy as np
import pyautogui
import pyperclip
import requests
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ==============================================================================
# 3. CORREÇÃO DE CAMINHO (Mantemos aqui, é necessário)
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ==============================================================================
# 4. IMPORTS DO SEU PROJETO
# ==============================================================================
# Usamos # noqa: E402 no final de cada linha para silenciar o Flake8
import notification_manager  # noqa: E402
from config import BASE_DIR  # noqa: E402

# AQUI ESTÁ A CORREÇÃO: Unifique o import do database em uma linha só
from database_manager import RESULTADO_HIT  # noqa: E402
from database_manager import RESULTADO_MISS  # noqa: E402
from database_manager import BetData  # noqa: E402
from database_manager import DatabaseManager  # noqa: E402
from database_manager import RoundData  # noqa: E402
from learning_engine import LearningEngine  # noqa: E402
from security import get_hwid  # noqa: E402
from strategy_engine import RiskMode, StrategyEngine  # noqa: E402
from vision.vision_system import VisionSystem  # noqa: E402

# ==============================================================================
# 5. CONSTANTES GLOBAIS
# ==============================================================================
API_URL = "https://crash-api-jose.onrender.com"


class TableType(Enum):
    """Define os tipos de tabelas pré-configuradas da UI."""

    DATABASE_STATS = "DATABASE_STATS"
    STRATEGY_STATS = "STRATEGY_STATS"
    FINANCIAL_SUMMARY = "FINANCIAL_SUMMARY"


class BotController:
    """Controlador principal - Versão Comercial com Modos de Risco."""

    _TABLE_CONFIGS: Dict[TableType, Dict] = {
        TableType.DATABASE_STATS: {
            "title": "Estatísticas do Database",
            "columns": [
                ("Métrica", {"style": "white"}),
                ("Valor", {"style": "bold white"}),
            ],
        },
        TableType.STRATEGY_STATS: {
            "title": "",
            "border_style": "dim",
            "header_style": "bold magenta",
            "columns": [
                ("Estratégia", {"style": "cyan"}),
                ("T", {"justify": "right"}),
                ("H", {"justify": "right", "style": "green"}),
                ("M", {"justify": "right", "style": "red"}),
                ("H%", {"justify": "right"}),
            ],
        },
        TableType.FINANCIAL_SUMMARY: {
            "title": "Resultado Financeiro",
            "columns": [
                ("Item", {"style": "white"}),
                ("Valor", {"style": "bold white"}),
            ],
        },
    }

    def __init__(self, config_filename="config.json"):
        # Inicialização do 'rich'
        self.console = Console()

        self.config_path = os.path.join(BASE_DIR, config_filename)
        self.config = self.load_config()

        # Carregar Parâmetros do Bot
        bot_params = self.config.get("bot_parameters", {})
        self.cooldown_seconds = bot_params.get("cooldown_seconds", 8)
        self.balance_check_interval = bot_params.get("balance_check_interval", 3.0)
        self.balance_change_threshold_pct = bot_params.get(
            "balance_change_threshold_pct", 30
        )
        self.frame_interval = bot_params.get("frame_interval", 0.05)

        self.stop_loss_threshold_pct = bot_params.get("stop_loss_threshold_pct", 0.50)
        self.stop_loss_alerted = False
        self.is_windows = os.name == "nt"

        notification_config = self.config.get("notifications", {})
        token = notification_config.get("telegram_bot_token")
        chat_id = notification_config.get("telegram_chat_id")

        if token and chat_id and "COLE_SEU" not in token:
            notification_manager.load_credentials(token, chat_id)
            self.console.print("✅ Alertas do Telegram HABILITADOS", style="green")
        else:
            self.console.print(
                "⚠️  Alertas do Telegram DESABILITADOS (Token/ChatID não configurados).",
                style="yellow",
            )

        # Módulos principais
        self.vision = VisionSystem(str(self.config_path))
        self.learning_engine = LearningEngine()
        self.strategy = StrategyEngine(learning_engine=self.learning_engine)
        self.db_manager = DatabaseManager()

        # Estado do bot
        self.running = False
        self.session_start = datetime.now()

        # Dados da sessão
        self.explosions = []
        self.round_count = 0
        self.initial_balance = None
        self.current_balance = None
        self.balance_history = []

        # Modo de risco selecionado
        self.selected_risk_mode: Optional[RiskMode] = None
        self._pending_risk_mode: Optional[RiskMode] = None

        # Gerenciamento de apostas
        self.executed_bet_pending: Optional[Dict] = None
        self.last_round_id: Optional[int] = None

        # Thread-Safety
        self.balance_lock = threading.Lock()
        self.buffer_lock = threading.Lock()

        # Threading
        self.capture_thread = None
        self.detect_thread = None
        self.ui_thread = None
        self.balance_thread = None

        # Buffer para detecção
        self.frame_buffer = deque(maxlen=10)

        # Áreas da tela
        self.screen_areas = {}
        self.last_action = ""
        self.selected_profile = ""

        # Logger
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
        )

        self.last_balance_alert_time = time.time()
        self.live_display: Optional[Live] = None

        # Configurar áreas da tela
        self.selected_profile = self.setup_screen_areas()

        # Perguntar apenas o modo de risco (banca será detectada depois)
        risk_mode = self._perguntar_configuracoes_sessao()
        self.selected_risk_mode = risk_mode

        # A sessão será iniciada após detectar o saldo em _run_main_loop()
        # Guardamos o modo para usar depois
        self._pending_risk_mode = risk_mode

        self.console.print("✅ BotController inicializado com sucesso!", style="green")
        self.console.print(
            f"📊 Database Manager ativo: {self.db_manager.session_id}", style="cyan"
        )

    def _perguntar_configuracoes_sessao(self) -> RiskMode:
        """Coleta apenas o modo de risco. Banca será detectada automaticamente."""
        self.console.print("\n[bold cyan]━━━ CONFIGURAÇÃO DA SESSÃO ━━━[/bold cyan]")

        # Menu de Modo de Risco (Simplificado - sem detalhes técnicos)
        self.console.print("\n[bold yellow]🎯 ESCOLHA SEU MODO DE RISCO:[/bold yellow]")
        self.console.print("")
        self.console.print(
            "  [green]1. CONSERVADOR[/green] - Menor risco, ganhos consistentes"
        )
        self.console.print("")
        self.console.print(
            "  [yellow]2. MODERADO[/yellow] - Equilíbrio entre risco e retorno"
        )
        self.console.print("")
        self.console.print("  [red]3. AGRESSIVO[/red] - Maior risco, maiores retornos")
        self.console.print("")

        risk_mode = self._obter_escolha_valida(
            prompt="Escolha (1-3): ",
            opcoes={
                "1": RiskMode.CONSERVADOR,
                "2": RiskMode.MODERADO,
                "3": RiskMode.AGRESSIVO,
            },
        )

        # Exibe confirmação
        mode_colors = {
            RiskMode.CONSERVADOR: "green",
            RiskMode.MODERADO: "yellow",
            RiskMode.AGRESSIVO: "red",
        }
        color = mode_colors[risk_mode]
        self.console.print(
            f"\n✅ Modo [{color}]{risk_mode.name}[/{color}] selecionado!",
            style="bold",
        )

        return risk_mode

    def _obter_escolha_valida(self, prompt: str, opcoes: Dict[str, Any]) -> Any:
        """Helper genérico para obter uma escolha válida."""
        while True:
            try:
                escolha = self.console.input(f"[green]{prompt}[/green]")
                if escolha in opcoes:
                    return opcoes[escolha]
                else:
                    self.console.print("Opção inválida! Tente novamente.", style="red")
            except Exception as e:
                self.console.print(f"Erro: {e}", style="red")

    def load_config(self) -> Dict:
        """Carrega configuração."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.console.print(
                f"❌ Erro ao carregar {self.config_path}: {e}", style="red"
            )
            return {}

    def _send_telemetry(self, tipo: str, dados: str = "", lucro: float = 0.0):
        """Envia dados de telemetria para o servidor (não-bloqueante)."""
        if not self.running and not self.db_manager.session_id:
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
            self.logger.warning(f"Falha ao enviar telemetria: {e}")

    def select_profile(self):
        """Seleção de perfil."""
        profiles = self.config.get("profiles", {})

        self.console.print("\nPerfis disponíveis:", style="cyan")
        self.console.print(
            "  [bold yellow]0. 🛠️  CRIAR NOVO PERFIL (CALIBRAR TELA)[/bold yellow]"
        )

        profile_keys = list(profiles.keys())
        for i, profile in enumerate(profile_keys, 1):
            self.console.print(f"  {i}. {profile}", style="white")

        while True:
            try:
                choice_str = self.console.input(
                    "\n[green]Selecione o perfil (0 para calibrar): [/green]"
                )
                choice = int(choice_str)

                if choice == 0:
                    name, data = self.run_calibration_wizard()
                    if name and data:
                        return name, data
                    else:
                        continue

                if 1 <= choice <= len(profiles):
                    selected_profile = profile_keys[choice - 1]
                    profile_data = profiles[selected_profile]
                    self.console.print(
                        f"✅ Perfil '{selected_profile}' selecionado", style="green"
                    )
                    return selected_profile, profile_data
                else:
                    self.console.print("Número inválido.", style="red")
            except ValueError:
                self.console.print("Digite um número válido.", style="red")

    def setup_screen_areas(self):
        """Configura áreas da tela baseado no perfil selecionado."""
        if not self.config:
            self.console.print("❌ Config não carregado!", style="red")
            return ""

        profiles = self.config.get("profiles", {})
        if not profiles:
            self.console.print("❌ Nenhum perfil encontrado no config!", style="red")
            return ""

        profile_name, profile_data = self.select_profile()

        self.players = self.config.get("jogadores", [])
        self.max_time = self.config.get("tempo_horas", 8) * 3600
        self.max_rounds = self.config.get("max_rodadas", 1000)
        self.target_profit = self.config.get("meta_lucro_total", 1000)
        self.start_hour = self.config.get("horario_inicio", 9)

        self.screen_areas = {
            "balance": profile_data.get("balance_area"),
            "multiplier": profile_data.get("multiplier_area"),
            "bet_detection": profile_data.get("bet_area"),
            "bet_value_1": profile_data.get("bet_value_area_1"),
            "target_1": profile_data.get("target_area_1"),
            "bet_value_2": profile_data.get("bet_value_area_2"),
            "target_2": profile_data.get("target_area_2"),
            "bet_button_1": profile_data.get("bet_button_area_1"),
            "bet_button_2": profile_data.get("bet_button_area_2"),
            "bet_value_click_1": profile_data.get("bet_value_click_1"),
            "target_click_1": profile_data.get("target_click_1"),
            "bet_value_click_2": profile_data.get("bet_value_click_2"),
            "target_click_2": profile_data.get("target_click_2"),
        }

        self.console.print(f"✅ Perfil '{profile_name}' carregado", style="green")

        critical_areas = ["balance", "multiplier", "bet_detection"]
        if missing_areas := [
            area for area in critical_areas if not self.screen_areas.get(area)
        ]:
            self.console.print(
                f"⚠️ Áreas não configuradas: {missing_areas}", style="yellow"
            )

        bet_areas = ["bet_value_1", "target_1", "bet_button_1"]
        configured_bet_areas = sum(
            bool(self.screen_areas.get(area)) for area in bet_areas
        )
        self.console.print(
            f"📍 Áreas de aposta configuradas: {configured_bet_areas}/{len(bet_areas)}",
            style="cyan",
        )
        if configured_bet_areas == len(bet_areas):
            self.console.print("✅ Apostas automáticas: HABILITADAS", style="green")
        else:
            self.console.print(
                "⚠️ Apostas automáticas: LIMITADAS (algumas áreas não calibradas)",
                style="yellow",
            )

        return profile_name

    def detect_balance_continuously(self):
        """Thread para detectar saldo continuamente."""
        last_check = 0
        check_interval = self.balance_check_interval

        while self.running:
            try:
                if time.time() - last_check < check_interval:
                    time.sleep(0.2)
                    continue

                balance_area = self.screen_areas.get("balance")

                if not balance_area:
                    continue

                with self.balance_lock:
                    current_balance_snapshot = self.current_balance

                new_balance = self.vision.get_balance(
                    balance_area, current_balance_snapshot
                )

                if new_balance and new_balance != current_balance_snapshot:
                    if validated_balance := self._validate_and_confirm_balance_change(
                        new_balance, current_balance_snapshot
                    ):
                        with self.balance_lock:
                            old_balance = self.current_balance or 0.0
                            self.current_balance = validated_balance
                            initial_balance_snapshot = self.initial_balance

                        self.balance_history.append(validated_balance)
                        change = validated_balance - old_balance
                        self.last_action = (
                            f"💰 Saldo: R${validated_balance:.2f} "
                            f"([green]{change:+.2f}[/green])"
                        )

                        if initial_balance_snapshot:
                            self._check_and_trigger_stop_loss(
                                validated_balance, initial_balance_snapshot
                            )

                last_check = time.time()

            except Exception as e:
                self.logger.error(f"Erro na detecção de saldo: {e}")
                time.sleep(1)

    def _validate_and_confirm_balance_change(
        self, new_balance: float, current_balance: Optional[float]
    ) -> Optional[float]:
        """Valida uma mudança drástica de saldo."""
        if not current_balance or current_balance == 0:
            return new_balance

        change_percent = (abs(new_balance - current_balance) / current_balance) * 100
        if change_percent <= self.balance_change_threshold_pct:
            return new_balance

        self.console.print(
            f"⚠️  Mudança drástica de saldo detectada ({change_percent:.1f}%). "
            "Confirmando...",
            style="yellow",
        )
        time.sleep(1)

        balance_area = self.screen_areas.get("balance")
        if not balance_area:
            return None

        with self.balance_lock:
            current_balance_snapshot = self.current_balance

        confirmed_balance = self.vision.get_balance(
            balance_area, current_balance_snapshot
        )

        if not confirmed_balance or abs(confirmed_balance - new_balance) > 5:
            self.console.print(
                f"❌ Confirmação falhou. Descartando leitura: {new_balance:.2f}",
                style="red",
            )
            return None

        return confirmed_balance

    def _check_and_trigger_stop_loss(
        self, current_balance: float, initial_balance: float
    ):
        """Verifica a condição de stop-loss e dispara o alerta."""
        if self.stop_loss_alerted:
            return

        if initial_balance > 0 and current_balance < (
            initial_balance * (1 - self.stop_loss_threshold_pct)
        ):
            loss_pct = (1 - (current_balance / initial_balance)) * 100
            msg = (
                f"🚨 *ALERTA DE STOP-LOSS!* 🚨\n"
                f"Banca caiu abaixo de {self.stop_loss_threshold_pct:.0%} do inicial.\n\n"
                f"Início: R$ {initial_balance:.2f}\n"
                f"Atual: R$ {current_balance:.2f}\n"
                f"Perda: -{loss_pct:.1f}%"
            )
            self.trigger_alert("stop_loss", msg)
            self.stop_loss_alerted = True

    def capture_multipliers_continuously(self):
        """Thread para capturar multiplicadores continuamente."""
        while self.running:
            try:
                if multiplier_area := self.screen_areas.get("multiplier"):
                    multiplier = self.vision.get_multiplier(multiplier_area)

                    if multiplier and 1.0 <= multiplier <= 999.99:
                        frame_data = {"timestamp": time.time(), "value": multiplier}

                        with self.buffer_lock:
                            self.frame_buffer.append(frame_data)

                time.sleep(self.frame_interval)

            except Exception as e:
                self.logger.error(f"Erro na captura: {e}")
                time.sleep(0.1)

    def detect_bet_and_process(self):
        """Thread principal de detecção e processamento."""
        last_explosion_time = 0
        cooldown = self.cooldown_seconds

        while self.running:
            try:
                current_time = time.time()

                if current_time - last_explosion_time < cooldown:
                    time.sleep(0.1)
                    continue

                bet_area = self.screen_areas.get("bet_detection")

                if not bet_area:
                    time.sleep(1)
                    continue

                if self.vision.detect_bet_text(bet_area):
                    current_time_str = datetime.now().strftime("%H:%M:%S")
                    self.last_action = f"🎯 APOSTA DETECTADA! {current_time_str}"

                    explosion_value = None
                    with self.buffer_lock:
                        buffer_copy = list(self.frame_buffer)

                    for i in range(len(buffer_copy) - 1, -1, -1):
                        frame = buffer_copy[i]
                        if frame["value"] and 1.0 <= frame["value"] <= 999.0:
                            explosion_value = frame["value"]
                            break

                    if explosion_value:
                        self.process_explosion(explosion_value, current_time)
                        last_explosion_time = current_time

                        with self.buffer_lock:
                            self.frame_buffer.clear()
                    else:
                        self.last_action = "❌ Aposta detectada mas sem valor válido"

                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Erro na detecção: {e}")
                self.last_action = f"❌ Erro na detecção: {e}"
                time.sleep(1)

    def process_explosion(self, explosion_value: float, timestamp: float):
        """Processa uma explosão detectada."""
        try:
            self.explosions.append(
                {"value": explosion_value, "timestamp": datetime.now()}
            )
            self.round_count += 1
            self.last_action = f"💥 EXPLOSÃO: {explosion_value:.2f}x"

            self._send_telemetry(
                tipo="round", dados=f"Explosao: {explosion_value:.2f}x", lucro=0.0
            )

            with self.balance_lock:
                current_balance = self.current_balance or 0.0

            self._handle_previous_bet_result(explosion_value)

            dados_rodada = RoundData(
                timestamp=datetime.now().isoformat(),
                multiplicador=explosion_value,
                duracao_rodada=0.0,
                fase_detectada="N/A",
                saldo_momento=current_balance,
                sessao_id=self.db_manager.session_id,
            )
            rodada_id = self.db_manager.save_round(dados_rodada)
            self.last_round_id = rodada_id

            if not self._check_game_state_for_next_round(current_balance):
                return

            self._prepare_next_round_bet(current_balance, explosion_value)

        except Exception as e:
            self.logger.error(f"Erro ao processar explosão: {e}")
            self.last_action = f"❌ Erro ao processar explosão: {e}"

    def _check_game_state_for_next_round(self, current_balance: float) -> bool:
        """Verifica se o bot está suspenso ou atingiu a meta."""
        if self.strategy.esta_suspenso():
            tempo_restante = self.strategy.get_tempo_restante_suspensao()
            horas = tempo_restante // 3600
            minutos = (tempo_restante % 3600) // 60
            self.last_action = (
                f"🏆 META BATIDA! Suspensão: {horas}h {minutos}min restantes"
            )

            if self.strategy.check_suspension_ended(current_balance):
                msg = (
                    "✅ *OPERAÇÕES RETOMADAS!*\n"
                    "Período de suspensão (meta) terminado."
                )
                self.trigger_alert("resume", msg)

            return False

        elif self._check_profit_target_reached(current_balance):
            return False

        else:
            return True

    def _check_profit_target_reached(self, current_balance: float) -> bool:
        """Verifica se a meta de lucro foi atingida."""
        if self.strategy.checar_meta_lucro(current_balance):
            if (
                self.strategy.banca_inicial is None
                or self.strategy.meta_lucro_percentual is None
            ):
                self.logger.error("Falha ao suspender: Dados da estratégia são None.")
                return True

            meta_valor_abs = self.strategy.banca_inicial * (
                1 + self.strategy.meta_lucro_percentual
            )

            self.last_action = "🏆 META ATINGIDA! Suspendendo por 4 horas..."

            msg = (
                f"🏆 *META DE LUCRO ATINGIDA!* 🏆\n"
                f"Meta: R$ {meta_valor_abs:.2f}\n"
                f"Saldo Atual: R$ {current_balance:.2f}\n"
                f"Operações suspensas por 4 horas."
            )
            self.trigger_alert("suspend", msg)
            return True

        return False

    def _prepare_next_round_bet(self, current_balance: float, explosion_value: float):
        """Processa a estratégia e prepara a próxima aposta."""
        strategy_activated, _, veto_message = self.strategy.add_explosion_value(
            explosion_value
        )
        if veto_message:
            self.last_action += f" | [yellow]{veto_message}[/yellow]"

        if recommendation := self.strategy.prepare_bets_for_balance(current_balance):
            self.last_action = (
                f"🎯 ESTRATÉGIA PREPARADA: {recommendation.strategy_name}"
            )
            if self.can_execute_bets():
                self.last_action += " | 🚀 EXECUTANDO IMEDIATAMENTE"
                self.execute_prepared_bets()
            else:
                self.last_action += " | ⚠️ Áreas de aposta não calibradas"

    def _handle_previous_bet_result(self, explosion_value: float):
        """Processa o resultado da aposta pendente."""
        if not self.executed_bet_pending:
            return

        try:
            self._process_bet_evaluation(explosion_value, self.executed_bet_pending)

        except Exception as e:
            self.logger.error(f"Erro ao processar resultado da aposta anterior: {e}")
            self.last_action += " | ❌ Erro aposta ant."
        finally:
            self.executed_bet_pending = None

    def _process_bet_evaluation(self, explosion_value: float, executed_bet: dict):
        """Avalia, alerta e salva o resultado da aposta."""
        with self.balance_lock:
            current_balance = self.current_balance or 0.0

        result = self.strategy.evaluate_executed_bet(explosion_value, executed_bet)
        strategy_name = result.get("strategy", "Estratégia")

        base_msg = (
            f"Alvo: {result['target_1']}x | Explodiu: {explosion_value}x\n"
            f"*Saldo Atual: R$ {current_balance:.2f}*"
        )

        if result["recommendation_hit"]:
            hit_status = "[green]✅ HIT[/green]"
            msg_meta = ""
            try:
                if self.strategy.banca_inicial and self.strategy.meta_lucro_percentual:
                    meta_abs = self.strategy.banca_inicial * (
                        1 + self.strategy.meta_lucro_percentual
                    )
                    falta_para_meta = meta_abs - current_balance

                    if falta_para_meta > 0:
                        msg_meta = f"\n*Falta para Meta: R$ {falta_para_meta:.2f}*"
            except Exception as e:
                self.logger.error(f"Erro ao calcular meta restante: {e}")
            msg = f"✅ *HIT!* | {strategy_name}\n{base_msg}{msg_meta}"
            self.trigger_alert("hit", msg)
        else:
            hit_status = "[red]❌ MISS[/red]"
            msg = f"❌ *MISS!* | {strategy_name}\n{base_msg}"
            self.trigger_alert("miss", msg)

        self.last_action += f" | {hit_status}"

        if self.last_round_id:
            resultado_aposta_1 = (
                RESULTADO_HIT if result["recommendation_hit"] else RESULTADO_MISS
            )

            dados_aposta = BetData(
                rodada_id=self.last_round_id,
                estrategia=result.get("strategy", "Estratégia"),
                aposta_1=result.get("bet_1", 0.0),
                target_1=result.get("target_1", 0.0),
                aposta_2=0.0,
                target_2=0.0,
                resultado_1=resultado_aposta_1,
                resultado_2=RESULTADO_MISS,
                lucro_liquido=result.get("profit_loss", 0.0),
                timestamp=datetime.now().isoformat(),
            )

            self.db_manager.save_bet(dados_aposta)

            self._send_telemetry(
                tipo="bet",
                dados=f"Resultado: {resultado_aposta_1}",
                lucro=dados_aposta.lucro_liquido,
            )

    def can_execute_bets(self) -> bool:
        """Verifica apenas áreas do BET 1."""
        required_areas = ["bet_value_1", "target_1", "bet_button_1"]

        if missing_areas := [
            area_name
            for area_name in required_areas
            if not self.screen_areas.get(area_name)
        ]:
            self.console.print(
                f"❌ Áreas não configuradas: {missing_areas}", style="red"
            )
            return False

        return True

    def execute_prepared_bets(self):
        """Executa apenas BET 1."""
        try:
            recommendation = self.strategy.get_prepared_bets()

            if not recommendation or not recommendation.ready:
                return

            self.last_action = f"⚡ EXECUTANDO BET 1: {recommendation.strategy_name}"

            self.console.print("DEBUG EXECUÇÃO RÁPIDA (SÓ BET 1):", style="magenta")
            self.console.print(
                f"  Aposta 1: R${recommendation.bet_1:.2f} "
                f"@ {recommendation.target_1:.2f}x"
            )
            with self.balance_lock:
                self.console.print(f"  Saldo atual: R${self.current_balance:.2f}")

            if self.fill_bet_fields_and_submit(
                recommendation.bet_1, recommendation.target_1
            ):
                self.executed_bet_pending = {
                    "strategy": recommendation.strategy_name,
                    "bet_1": recommendation.bet_1,
                    "target_1": recommendation.target_1,
                    "bet_2": 0,
                    "target_2": 0,
                }

                self.last_action = (
                    f"✅ BET 1 executado! "
                    f"R${recommendation.bet_1:.2f}@{recommendation.target_1:.2f}x"
                )

                self.strategy.reset_prepared_bets()
            else:
                self.last_action = "❌ Falha ao executar BET 1"

        except Exception as e:
            self.logger.error(f"Erro ao executar apostas: {e}")
            self.last_action = f"❌ Erro ao executar apostas: {e}"

    def trigger_alert(self, alert_type: str, message: Optional[str] = None):
        """Dispara alerta sonoro e notificação."""
        if self.is_windows:
            try:
                if alert_type == "hit":
                    winsound.Beep(frequency=1500, duration=150)
                elif alert_type == "miss":
                    winsound.Beep(frequency=700, duration=300)
                elif alert_type == "stop_loss":
                    self.last_action = "🚨 ALERTA DE STOP-LOSS ATINGIDO! 🚨"
                    self.console.print(f"[bold red]{self.last_action}[/bold red]")
                    for _ in range(3):
                        winsound.Beep(frequency=500, duration=1000)
                        time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Erro ao tocar som: {e}")

        if message:
            notification_manager.send_telegram_alert(message)

    def fill_bet_fields_and_submit(self, bet_value_1: float, target_1: float) -> bool:
        """Preenche campos e submete aposta."""
        try:
            bet_value_1 = max(1.0, (bet_value_1))
            bet_value_1_str = f"{bet_value_1:.2f}"
            target_1_str = f"{target_1:.2f}"

            area_value = self.screen_areas.get("bet_value_1")
            area_target = self.screen_areas.get("target_1")
            area_button = self.screen_areas.get("bet_button_1")

            if not area_value or not area_target or not area_button:
                self.console.print("❌ Erro: Áreas de aposta incompletas.", style="red")
                return False

            self.console.print("1/3 Preenchendo valor BET 1...", style="yellow")
            if not self.click_and_fill_field(
                area_value, bet_value_1_str, "valor aposta 1"
            ):
                return False
            time.sleep(random.uniform(0.1, 0.2))

            self.console.print("2/3 Preenchendo target BET 1...", style="yellow")
            if not self.click_and_fill_field(
                area_target, target_1_str, "alvo aposta 1"
            ):
                return False
            time.sleep(random.uniform(0.1, 0.2))

            self.console.print("3/3 Clicando botão BET 1...", style="yellow")
            if not self.click_area(area_button, "botão apostar 1"):
                return False

            self.console.print("✅ BET 1 EXECUTADO!", style="green")

            time.sleep(1.0)
            self.return_focus_to_bot()
            return True

        except Exception as e:
            self.logger.error(f"Erro ao executar BET 1: {e}")
            return False

    def click_and_fill_field(self, area: Dict, value: str, description: str) -> bool:
        """Clica em campo e preenche valor."""
        try:
            if not area:
                self.console.print(
                    f"❌ Área {description} não configurada!", style="red"
                )
                return False
            x = area["x"] + area["width"] // 2
            y = area["y"] + area["height"] // 2
            self.move_mouse_humanlike(x, y)
            pyautogui.click()
            time.sleep(random.uniform(0.05, 0.2))
            pyautogui.hotkey("ctrl", "a")
            time.sleep(random.uniform(0.05, 0.1))
            pyautogui.press("delete")
            time.sleep(random.uniform(0.05, 0.1))
            pyperclip.copy(value)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(random.uniform(0.05, 0.2))
            return True
        except Exception as e:
            self.logger.error(f"Erro ao preencher {description}: {e}")
            return False

    def click_area(self, area: Dict, description: str) -> bool:
        """Clica em uma área."""
        try:
            if not area:
                self.console.print(
                    f"❌ Área {description} não configurada!", style="red"
                )
                return False
            center_x = area["x"] + area["width"] // 2
            center_y = area["y"] + area["height"] // 2
            x = center_x + random.randint(-area["width"] // 4, area["width"] // 4)
            y = center_y + random.randint(-area["height"] // 4, area["height"] // 4)
            x = max(area["x"], min(area["x"] + area["width"], x))
            y = max(area["y"], min(area["y"] + area["height"], y))
            self.move_mouse_humanlike(x, y)
            if random.random() < 0.2:
                time.sleep(random.uniform(0.1, 0.3))
            pyautogui.click()
            return True
        except Exception as e:
            self.logger.error(f"Erro ao clicar {description}: {e}")
            return False

    def move_mouse_humanlike(self, target_x: int, target_y: int):
        """Move mouse de forma humana."""
        try:
            current_x, current_y = pyautogui.position()
            distance = (
                (target_x - current_x) ** 2 + (target_y - current_y) ** 2
            ) ** 0.5
            duration = random.uniform(0.1, 0.3) * (distance / 500)
            duration = max(0.05, min(0.5, duration))
            if distance > 50:
                mid_x = (current_x + target_x) // 2 + random.randint(-20, 20)
                mid_y = (current_y + target_y) // 2 + random.randint(-20, 20)
                pyautogui.moveTo(mid_x, mid_y, duration=duration / 2)
                pyautogui.moveTo(target_x, target_y, duration=duration / 2)
            else:
                pyautogui.moveTo(target_x, target_y, duration=duration)
        except Exception as e:
            self.logger.error(f"Erro ao mover mouse: {e}")

    def return_focus_to_bot(self):
        """Retorna foco para o bot."""
        try:
            pyautogui.keyDown("alt")
            time.sleep(0.1)
            pyautogui.press("tab")
            time.sleep(0.1)
            pyautogui.keyUp("alt")
        except Exception as e:
            self.logger.error(f"Erro ao retornar foco: {e}")

    def update_ui_continuously(self):
        """Thread da interface."""
        while self.running:
            try:
                if self.live_display:
                    self.live_display.update(self.build_dashboard_layout())

                current_time = time.time()
                if current_time - self.last_balance_alert_time >= 1800:
                    self.last_balance_alert_time = current_time

                    with self.balance_lock:
                        balance = self.current_balance

                    if not balance:
                        continue

                    stats = self._get_current_history_stats()

                    mode_name = (
                        self.selected_risk_mode.name
                        if self.selected_risk_mode
                        else "N/A"
                    )

                    msg = (
                        f"🔔 *Relatório Periódico (30 min)* 🔔\n\n"
                        f"*Modo: {mode_name}*\n"
                        f"*Banca Atual: R$ {balance:.2f}*\n\n"
                        f"*Análise {stats['total_count']} Rodadas:*\n"
                        f"- Média: {stats['mean_250']:.2f}x\n"
                        f"- Volat.: {stats['std_250']:.2f}\n"
                        f"- CV (Risco): {stats['cv_250']:.2f}\n"
                        f"- Zeros (1.00x): {stats['zeros_count']}\n"
                        f"- Max Streak (<2x): {stats['max_streak']}"
                    )

                    self.trigger_alert("periodic", msg)

                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Erro na UI: {e}")
                time.sleep(1)

    def build_dashboard_layout(self) -> Layout:
        """Cria o layout principal do dashboard."""
        # Verifica se está em suspensão para mostrar tela especial
        if self.strategy.esta_suspenso():
            return self._build_suspension_layout()

        layout = Layout()

        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=6),
        )
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        layout["left"].split(
            Layout(name="balance", size=5),
            Layout(name="db_stats", size=6),
            Layout(name="history", ratio=1),
        )
        layout["right"].split(
            Layout(name="strategy", size=7), Layout(name="stats", ratio=1)
        )
        layout["footer"].split(Layout(name="status"), Layout(name="info"))

        layout["header"].update(self._build_header_panel())
        layout["balance"].update(self._build_balance_panel())
        layout["db_stats"].update(self._build_db_stats_panel())
        layout["history"].update(self._build_history_panel())
        layout["strategy"].update(self._build_strategy_panel())
        layout["stats"].update(self._build_strategy_stats_panel())
        layout["status"].update(
            Panel(Text(self.last_action, justify="center"), style="bold white")
        )
        layout["footer"].update(self._build_footer_panel())

        return layout

    def _build_suspension_layout(self) -> Layout:
        """Cria layout especial para quando o bot está em suspensão (meta batida)."""
        layout = Layout()

        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=4),
        )

        # Header com modo
        layout["header"].update(self._build_header_panel())

        # Painel central grande de META BATIDA
        tempo_restante = self.strategy.get_tempo_restante_suspensao()
        horas = tempo_restante // 3600
        minutos = (tempo_restante % 3600) // 60
        segundos = tempo_restante % 60

        countdown_text = Text()
        countdown_text.append("\n\n")
        countdown_text.append("🏆 ", style="bold yellow")
        countdown_text.append("META BATIDA!", style="bold green")
        countdown_text.append(" 🏆\n\n", style="bold yellow")
        countdown_text.append("Bot em suspensão automática\n\n", style="dim")
        countdown_text.append("⏱️ Tempo restante:\n\n", style="yellow")
        countdown_text.append(
            f"{horas:02d}:{minutos:02d}:{segundos:02d}",
            style="bold cyan",
        )
        countdown_text.append("\n\n")

        with self.balance_lock:
            current_balance = self.current_balance or 0.0

        countdown_text.append(f"Saldo Atual: R$ {current_balance:.2f}\n", style="green")

        if self.strategy.banca_inicial and self.strategy.meta_lucro_percentual:
            meta = self.strategy.banca_inicial * (
                1 + self.strategy.meta_lucro_percentual
            )
            countdown_text.append(f"Meta Atingida: R$ {meta:.2f}\n", style="dim")

        layout["main"].update(
            Panel(
                countdown_text,
                title="[bold yellow]SUSPENSÃO ATIVA[/bold yellow]",
                border_style="green",
            )
        )

        # Footer
        footer_text = Text()
        footer_text.append(
            "O bot retomará automaticamente após o tempo.\n", style="dim"
        )
        footer_text.append("Pressione [Ctrl+C] para sair", style="bold yellow")
        layout["footer"].update(Panel(footer_text))

        return layout

    def _build_header_panel(self) -> Panel:
        """Constrói o painel de cabeçalho com modo de risco."""
        mode_colors = {
            RiskMode.CONSERVADOR: "green",
            RiskMode.MODERADO: "yellow",
            RiskMode.AGRESSIVO: "red",
        }

        title = Text()
        title.append("CRASH BOT - ML", style="bold cyan")

        if self.selected_risk_mode:
            color = mode_colors.get(self.selected_risk_mode, "white")
            title.append(" | Modo: ", style="dim")
            title.append(self.selected_risk_mode.name, style=f"bold {color}")

        return Panel(title, style="cyan")

    def _get_profit_loss_text(
        self, current_balance: Optional[float], initial_balance: Optional[float]
    ) -> Text:
        """Calcula e formata o texto de lucro/prejuízo."""
        if not (
            current_balance is not None
            and initial_balance is not None
            and initial_balance > 0
        ):
            return Text("N/A", style="dim")

        profit = current_balance - initial_balance
        profit_pct = profit / initial_balance * 100
        profit_color = "green" if profit >= 0 else "red"
        return Text(f"R$ {profit:+.2f} ({profit_pct:+.1f}%)", style=profit_color)

    def _build_db_stats_dashboard_text(self, db_stats, pnl_color: str) -> Text:
        """Cria o texto formatado para o painel do DB."""
        text = Text()
        text.append(f"Rodadas Salvas: {db_stats.total_rounds}\n", style="white")
        text.append(f"Apostas Salvas: {db_stats.total_bets}\n", style="white")
        text.append(f"Taxa de Acerto: {db_stats.hit_rate:.1f}%\n", style="white")
        text.append(f"P&L (DB): R$ {db_stats.profit_loss:+.2f}", style=pnl_color)
        return text

    def _build_db_stats_renderable(
        self, is_summary: bool = False
    ) -> Union[Table, Text, Panel]:
        """Busca estatísticas do DB e retorna um objeto 'rich' formatado."""
        try:
            db_stats = self.db_manager.get_session_stats()
            pnl_color = "green" if db_stats.profit_loss >= 0 else "red"

            if is_summary:
                return self._build_db_stats_summary_table(db_stats, pnl_color)
            else:
                return self._build_db_stats_dashboard_text(db_stats, pnl_color)

        except Exception as e:
            if is_summary:
                error_message = f"❌ Erro nas estatísticas do DB: {e}"
                return Panel(error_message, style="red", title="Database")
            else:
                return Text("Erro DB...", style="red")

    def _create_styled_table(
        self,
        title: str,
        border_style: str = "cyan",
        show_header: bool = True,
        title_style: str = "bold cyan",
        header_style: str = "bold white",
        **kwargs,
    ) -> Table:
        """Factory method para criar tabelas Rich."""
        return Table(
            title=title,
            border_style=border_style,
            show_header=show_header,
            title_style=title_style,
            header_style=header_style,
            **kwargs,
        )

    def _create_table_by_type(self, table_type: TableType) -> Table:
        """Cria uma tabela Rich pré-configurada."""
        try:
            config = self._TABLE_CONFIGS[table_type]
        except KeyError:
            self.logger.error(f"Tipo de tabela desconhecido: {table_type}")
            return Table(title=f"Erro: Tabela {table_type} não encontrada")

        title = config.get("title", "")
        columns = config.get("columns", [])

        table_kwargs = {
            k: v for k, v in config.items() if k not in ["title", "columns"]
        }

        table = self._create_styled_table(title=title, **table_kwargs)

        for col_name, col_kwargs in columns:
            table.add_column(col_name, **col_kwargs)
        return table

    def _get_safe_balances(self) -> tuple[Optional[float], Optional[float]]:
        """Retorna o saldo atual e inicial de forma thread-safe."""
        with self.balance_lock:
            current = self.current_balance
            initial = self.initial_balance
        return current, initial

    def _build_db_stats_summary_table(self, db_stats, pnl_color: str) -> Table:
        """Cria a Tabela Rich formatada para o sumário do DB."""
        db_table = self._create_table_by_type(TableType.DATABASE_STATS)

        db_table.add_row("Multiplicadores salvos", str(db_stats.total_rounds))
        db_table.add_row("Apostas executadas", str(db_stats.total_bets))
        db_table.add_row("Taxa de acerto", f"{db_stats.hit_rate:.1f}%")

        db_table.add_row(
            "P&L Total (DB)",
            Text(f"R$ {db_stats.profit_loss:+.2f}", style=pnl_color),
        )
        return db_table

    def _build_balance_panel(self) -> Panel:
        """Constrói o painel de saldo."""
        current_balance, initial_balance = self._get_safe_balances()

        if current_balance is not None:
            balance_text = Text(f"R$ {current_balance:.2f} ", style="bold white")
            profit_text = self._get_profit_loss_text(current_balance, initial_balance)
            balance_text.append(profit_text)
        else:
            balance_text = Text("Detectando...", style="yellow")

        elapsed = (datetime.now() - self.session_start).total_seconds()
        time_text = Text(
            f"Tempo: {self.format_time(elapsed)} | Rodadas: {self.round_count}"
        )

        return Panel(Text.assemble(balance_text, "\n", time_text), title="Banca")

    def _build_db_stats_panel(self) -> Panel:
        """Constrói o painel de estatísticas do DB."""
        db_content = self._build_db_stats_renderable(is_summary=False)
        return Panel(db_content, title="Database (Sessão)")

    def _build_history_panel(self) -> Panel:
        """Constrói o painel de histórico."""
        text = Text()

        if self.explosions:
            last_250_values = [e["value"] for e in self.explosions[-250:]]

            if len(last_250_values) >= 20:
                self._append_history_stats(text, last_250_values)

            self._append_recent_history(text)
        else:
            text.append("Aguardando explosões...", style="dim")

        return Panel(text, title="Histórico e Análise (250)")

    def _append_history_stats(self, text: Text, last_250_values: list):
        """Calcula e anexa estatísticas."""
        stats = self._get_current_history_stats()

        total_count = stats["total_count"]
        mean_250 = stats["mean_250"]
        std_250 = stats["std_250"]
        cv_250 = stats["cv_250"]
        max_streak = stats["max_streak"]
        zeros_count = stats["zeros_count"]

        zeros_pct = (zeros_count / total_count) * 100 if total_count > 0 else 0.0
        p80_value = np.percentile(last_250_values, 80)

        mean_color = "green" if mean_250 >= 2.0 else "red"
        std_color = (
            "red" if std_250 > 15.0 else ("yellow" if std_250 > 10.0 else "green")
        )
        cv_color = "red" if cv_250 > 3.0 else ("yellow" if cv_250 > 2.5 else "green")
        streak_color = (
            "red" if max_streak >= 8 else ("yellow" if max_streak >= 6 else "green")
        )
        zeros_color = (
            "red" if zeros_pct > 4.0 else ("yellow" if zeros_pct > 2.0 else "green")
        )

        text.append(f"--- Análise ({total_count} Rodadas) ---\n", style="cyan")

        text.append("Média  (250): ", style="white")
        text.append(f"{mean_250:.2f}x\n", style=mean_color)

        text.append("Volat. (250): ", style="white")
        text.append(f"{std_250:.2f}\n", style=std_color)

        text.append("CV (Risco):   ", style="white")
        text.append(f"{cv_250:.2f}\n", style=cv_color)

        text.append("Max Streak (<2x): ", style="white")
        text.append(f"{max_streak}\n", style=streak_color)

        text.append("Zeros (1.00x):  ", style="white")
        text.append(f"{zeros_count} ({zeros_pct:.1f}%)\n", style=zeros_color)

        text.append("P80 (Top Win):  ", style="white")
        text.append(f"{p80_value:.2f}x\n", style="dim")

        text.append("-----------------------------\n", style="cyan")

    def _append_recent_history(self, text: Text):
        """Anexa os 15 multiplicadores mais recentes."""
        last_15 = self.explosions[-15:]
        for e in reversed(last_15):
            color = "red" if e["value"] < 2.0 else "green"
            text.append(f"{e['value']:.2f}x\n", style=color)

    def _calculate_max_streak(self, values: list) -> int:
        """Calcula a maior streak de baixos."""
        max_streak = 0
        current_streak = 0
        for value in values:
            if value < 2.0:
                current_streak += 1
            else:
                max_streak = max(max_streak, current_streak)
                current_streak = 0
        return max(max_streak, current_streak)

    def _get_current_history_stats(self) -> Dict[str, Union[float, int]]:
        """Calcula estatísticas das últimas 250 rodadas."""
        stats = {
            "mean_250": 0.0,
            "std_250": 0.0,
            "cv_250": 0.0,
            "zeros_count": 0,
            "max_streak": 0,
            "total_count": 0,
        }

        if not self.explosions:
            return stats

        last_250_values = [e["value"] for e in self.explosions[-250:]]
        stats["total_count"] = len(last_250_values)

        if stats["total_count"] >= 20:
            stats["mean_250"] = np.mean(last_250_values)
            stats["std_250"] = np.std(last_250_values)
            stats["cv_250"] = (
                (stats["std_250"] / stats["mean_250"]) if stats["mean_250"] > 0 else 0.0
            )
            stats["zeros_count"] = last_250_values.count(1.00)
            stats["max_streak"] = self._calculate_max_streak(last_250_values)

        return stats

    def _build_strategy_panel(self) -> Panel:
        """Constrói o painel de status da estratégia."""
        try:
            analysis_data = self.strategy.get_current_analysis()

            table = self._create_styled_table(
                title="",
                border_style="dim",
                show_header=False,
                expand=True,
            )
            table.add_column("Item", style="cyan")
            table.add_column("Status", style="white")

            # Modo de Risco
            mode_colors = {
                "CONSERVADOR": "green",
                "MODERADO": "yellow",
                "AGRESSIVO": "red",
            }
            risk_mode_name = analysis_data.get("risk_mode", "N/A")
            mode_color = mode_colors.get(risk_mode_name, "white")
            table.add_row(
                "Modo:",
                Text(risk_mode_name, style=f"bold {mode_color}"),
            )

            # Status do Martingale
            status_text = (
                "[green]ATIVO[/green]"
                if analysis_data.get("martingale_active")
                else "[yellow]Aguardando[/yellow]"
            )
            table.add_row("Martingale:", status_text)

            # Dobra Atual
            dobra_atual = analysis_data.get("dobra_atual", 1)
            table.add_row("Dobra Atual:", str(dobra_atual))

            # Gatilho de Baixos
            gatilho_baixos = analysis_data.get("baixos_consecutivos", "N/A")
            table.add_row("Gatilho (Baixos):", gatilho_baixos)

            # Confiança do ML
            ml_conf = analysis_data.get("ml_confidence", 0.0)

            if ml_conf == -1.0:
                conf_text = Text("Erro", style="red")
            else:
                conf_color = (
                    "green"
                    if ml_conf > 0.65
                    else ("yellow" if ml_conf > 0.52 else "dim")
                )
                conf_text = Text(f"{ml_conf:.1%}", style=conf_color)

            table.add_row("Confiança ML (Hit):", conf_text)

            return Panel(table, title="Status da Estratégia")

        except Exception as e:
            self.logger.error(f"Erro ao construir _build_strategy_panel: {e}")
            return Panel(
                Text(f"Erro ao carregar status: {e}", style="red"),
                title="Status da Estratégia",
            )

    def _build_strategy_stats_panel(self) -> Panel:
        """Constrói o painel de estatísticas das políticas."""
        try:
            stats_list = self.strategy.get_strategies_stats()
            table = self._create_styled_table(
                title="",
                border_style="dim",
                header_style="bold magenta",
                show_header=True,
            )
            table.add_column("Estratégia", style="cyan")
            table.add_column("T", justify="right")
            table.add_column("H", justify="right", style="green")
            table.add_column("M", justify="right", style="red")
            table.add_column("H%", justify="right")

            for stats in stats_list:
                table.add_row(
                    stats["name"],
                    str(stats["total_recommendations"]),
                    str(stats["total_hits"]),
                    str(stats["total_misses"]),
                    f"{stats['total_hit_rate']:.1f}%",
                )
            return Panel(table, title="Estatísticas das Políticas")
        except Exception:
            return Panel(
                Text("Carregando...", style="dim"), title="Estatísticas das Políticas"
            )

    def _build_footer_panel(self) -> Panel:
        """Constrói o painel de rodapé."""
        text = Text()
        text.append(f"🆔 Sessão: {self.db_manager.session_id[-20:]}\n", style="dim")
        text.append(f"👤 Perfil: {self.selected_profile}\n", style="dim")
        text.append("Pressione [Ctrl+C] para sair", style="bold yellow")
        return Panel(text)

    def _print_summary_footer_info(self):
        """Imprime informações de rodapé do resumo."""
        self.console.print(
            f"🆔 ID da Sessão: {self.db_manager.session_id}", style="dim"
        )
        self.console.print(f"📁 Database: {self.db_manager.db_path}", style="dim")

    def format_time(self, seconds: float) -> str:
        """Formata tempo em HH:MM:SS."""
        return str(timedelta(seconds=int(seconds)))

    def _print_financial_summary(self):
        """Imprime a tabela de resumo financeiro."""
        current_balance, initial_balance = self._get_safe_balances()

        if current_balance is not None and initial_balance is not None:
            profit_text_obj = self._get_profit_loss_text(
                current_balance, initial_balance
            )

            finance_table = self._create_table_by_type(TableType.FINANCIAL_SUMMARY)

            finance_table.add_row("Saldo inicial", f"R$ {initial_balance:.2f}")
            finance_table.add_row("Saldo final", f"R$ {current_balance:.2f}")
            finance_table.add_row(
                "Resultado",
                profit_text_obj,
            )
            self.console.print(finance_table)

    def detect_initial_balance(self) -> Optional[float]:
        """Detecta saldo inicial automaticamente."""
        balance_area = self.screen_areas.get("balance")

        if not balance_area:
            return None

        self.console.print("🔍 Detectando saldo inicial...", style="cyan")

        for attempt in range(8):
            balance = self.vision.get_balance(balance_area)

            if balance and 0.01 <= balance <= 1000000:
                self.console.print(
                    f"✅ Saldo detectado: R$ {balance:.2f}", style="green"
                )
                return balance

            self.console.print(
                f"⚠️ Tentativa {attempt+1}/8... aguardando 2s", style="yellow"
            )
            time.sleep(2)

        return None

    def _set_initial_balance(self, balance_value: float):
        """Define o saldo inicial e atual."""
        with self.balance_lock:
            self.initial_balance = balance_value
            self.current_balance = balance_value
        self.balance_history.append(balance_value)

    def _start_threads(self):
        """Inicializa e inicia todas as threads."""
        self.balance_thread = threading.Thread(
            target=self.detect_balance_continuously, daemon=True
        )
        self.capture_thread = threading.Thread(
            target=self.capture_multipliers_continuously, daemon=True
        )
        self.detect_thread = threading.Thread(
            target=self.detect_bet_and_process, daemon=True
        )
        self.ui_thread = threading.Thread(
            target=self.update_ui_continuously, daemon=True
        )

        self.balance_thread.start()
        self.capture_thread.start()
        self.detect_thread.start()
        self.ui_thread.start()

    def _initialize_balance(self):
        """Detecta o saldo inicial ou define um valor padrão."""
        if not (balance_to_set := self.detect_initial_balance()):
            self.console.print("⚠️ Usando saldo padrão R$ 100,00", style="yellow")
            balance_to_set = 100.0
        self._set_initial_balance(balance_to_set)

    def _get_license_key(self) -> Optional[str]:
        """Lê a chave do arquivo local."""
        filename = "license_key.txt"

        if not os.path.exists(filename):
            try:
                with open(filename, "w") as f:
                    f.write("COLE_SUA_CHAVE_AQUI")

                self.console.print(
                    f"⚠️ Arquivo de licença criado: [bold yellow]{filename}[/bold yellow]",
                    style="yellow",
                )
                self.console.print(
                    "👉 Por favor, cole sua chave nesse arquivo e reinicie o bot.",
                    style="yellow",
                )
            except Exception as e:
                self.logger.error(f"Falha ao criar arquivo de licença: {e}")

            return None

        try:
            with open(filename, "r") as f:
                key = f.read().strip()
                return key if key and "COLE_SUA_CHAVE_AQUI" not in key else None
        except Exception as e:
            self.logger.error(f"Erro ao ler chave de licença: {e}")
            return None

    def _validate_license(self) -> bool:
        """
        Gera o HWID e verifica a licença no servidor na nuvem.
        Retorna True se o acesso for permitido.
        """
        local_hwid = get_hwid()
        license_key = self._get_license_key()

        if not license_key:
            self.console.print(
                "❌ ERRO: Chave de licença ausente ou inválida.", style="bold red"
            )
            return False

        endpoint = f"{API_URL}/validar"
        data = {"chave": license_key, "hwid": local_hwid}

        self.console.print("🔒 Conectando ao servidor de licença...", style="dim")

        try:
            response = requests.post(endpoint, json=data, timeout=10)

            if response.status_code == 200:
                # SUCESSO
                self.console.print(
                    f"✅ LICENÇA VÁLIDA! {response.json().get('mensagem', '')}",
                    style="bold green",
                )
                return True
            else:
                # ERRO (Bloqueado, Expirado, etc)
                try:
                    resp_json = response.json()
                    msg = resp_json.get("mensagem", f"Erro HTTP {response.status_code}")
                except Exception:  # <--- CORREÇÃO AQUI (Era apenas 'except:')
                    msg = f"Erro HTTP {response.status_code}"

                self.console.print(f"❌ ACESSO NEGADO: {msg}", style="bold red")
                return False

        except requests.exceptions.RequestException:
            self.console.print(
                "❌ ERRO DE CONEXÃO: Servidor offline ou sem internet.",
                style="bold red",
            )
            return False

    def _run_main_loop(self):
        """Executa a lógica principal."""
        self.console.print("🚀 Iniciando Bot Controller...", style="cyan")

        if not self._validate_license():
            self.console.print(
                "\n[bold red]SISTEMA DESLIGADO POR FALHA NA LICENÇA.[/bold red]",
                style="bold red",
            )
            time.sleep(4)
            return

        time.sleep(2)

        # Detecta o saldo inicial automaticamente
        self._initialize_balance()

        # Agora que temos o saldo, inicia a sessão no strategy_engine
        with self.balance_lock:
            banca_detectada = self.initial_balance or 100.0

        risk_mode_safe = self._pending_risk_mode or RiskMode.MODERADO

        self.strategy.iniciar_sessao(
            banca_inicial=banca_detectada,
            risk_mode=risk_mode_safe,
        )

        self.running = True
        self._start_threads()

        self.live_display = Live(
            self.build_dashboard_layout(),
            console=self.console,
            refresh_per_second=4,
            screen=True,
        )
        self.live_display.start()

        mode_name = self.selected_risk_mode.name if self.selected_risk_mode else "N/A"
        self.last_action = f"✅ SISTEMA INICIADO! Modo: {mode_name}"

        while self.running:
            time.sleep(1)

    def start(self):
        """Inicia o bot."""
        try:
            self._run_main_loop()
        except KeyboardInterrupt:
            self.last_action = "Encerrando sistema..."
        except Exception as e:
            self.logger.error(f"Erro no start: {e}")
            self.console.print_exception()
        finally:
            self.stop()

    def stop(self):
        """Para o bot."""
        if not self.running:
            return

        self.running = False
        self.console.print(
            "Encerrando... Aguardando threads finalizarem.", style="yellow"
        )

        try:
            if self.ui_thread and self.ui_thread.is_alive():
                self.ui_thread.join(timeout=1.0)
            if self.detect_thread and self.detect_thread.is_alive():
                self.detect_thread.join(timeout=2.0)
            if self.balance_thread and self.balance_thread.is_alive():
                self.balance_thread.join(timeout=2.0)
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=1.0)
        except Exception as e:
            self.logger.error(f"Erro ao aguardar threads: {e}")

        if self.live_display:
            self.live_display.stop()
            self.console.clear()

        time.sleep(0.5)

        try:
            with self.balance_lock:
                final_balance = self.current_balance
            self.db_manager.close_session(final_balance)
            self.console.print("✅ Sessão do database fechada", style="green")
        except Exception as e:
            self.console.print(
                f"❌ Erro ao fechar sessão do database: {e}", style="red"
            )

        self.show_summary()

    def show_summary(self):
        """Mostra resumo da sessão."""
        self.console.clear()
        duration = datetime.now() - self.session_start

        main_panel_content = Text()
        main_panel_content.append(
            f"⏱️  Duração: {self.format_time(duration.total_seconds())}\n"
        )
        main_panel_content.append(f"💥 Total explosões: {len(self.explosions)}\n")

        if self.selected_risk_mode:
            main_panel_content.append(
                f"🎯 Modo utilizado: {self.selected_risk_mode.name}\n"
            )

        if self.explosions:
            values = [e["value"] for e in self.explosions]
            main_panel_content.append(
                f"📈 Menor: {min(values):.2f}x | "
                f"Maior: {max(values):.2f}x | "
                f"Média: {sum(values)/len(values):.2f}x\n"
            )

        self.console.print(
            Panel(main_panel_content, title="Resumo da Sessão", border_style="cyan")
        )

        db_renderable = self._build_db_stats_renderable(is_summary=True)
        self.console.print(db_renderable)

        self._print_financial_summary()
        self._print_summary_footer_info()

    def run_calibration_wizard(self):
        """Guia o usuário para mapear as áreas e salva no config.json."""
        self.console.clear()
        self.console.print(
            Panel(
                "[bold yellow]MODO DE CALIBRAÇÃO (WIZARD)[/bold yellow]\n\n"
                "Vou guiar você para mapear a tela do jogo.\n"
                "Para cada item, colocaremos o mouse no "
                "[cyan]Canto Superior Esquerdo[/cyan]\n"
                "e depois no [cyan]Canto Inferior Direito[/cyan].\n",
                border_style="yellow",
            )
        )

        profile_name = (
            self.console.input(
                "\n[cyan]Nome para este novo perfil (ex: MeuMonitor): [/cyan]"
            )
            or f"User_Profile_{int(time.time())}"
        )

        self.console.print(
            "\n[yellow]Deseja calibrar também a APOSTA 2 (Double Bet)?[/yellow]"
        )
        resp = self.console.input("Digite 's' para Sim ou Enter para pular: ").lower()
        use_bet_2 = resp == "s"
        # -------------------------

        # Chamada limpa (Agora 'use_bet_2' existe!)
        items_to_calibrate = self._get_items_to_calibrate(use_bet_2)

        new_profile = {}

        for area_key, click_key, friendly_name in items_to_calibrate:
            item_data = self._calibrate_single_item(area_key, click_key, friendly_name)
            new_profile |= item_data

        if not use_bet_2:
            self._clear_unused_bet2_fields(new_profile)

        self.console.print("\n💾 Salvando configurações...", style="yellow")
        if self._save_new_profile(profile_name, new_profile):
            return profile_name, new_profile
        return None, None

    def _save_new_profile(self, profile_name: str, new_profile: Dict) -> bool:
        """Salva o novo perfil no arquivo de configuração."""
        self.console.print("\n💾 Salvando configurações...", style="yellow")
        try:
            # Chama o novo método que faz o trabalho pesado
            self._persist_profile_data(profile_name, new_profile)

            self.console.print(
                f"✅ Perfil '{profile_name}' criado com sucesso!", style="bold green"
            )
            self.console.print("O bot usará este perfil agora.", style="cyan")
            return True

        except Exception as e:
            self.console.print(f"❌ Erro ao salvar: {e}", style="bold red")
            return False

    def _persist_profile_data(self, profile_name: str, new_profile: Dict) -> None:
        """
        Carrega, atualiza e salva o arquivo de configuração no disco.
        (Extraído de _save_new_profile)
        """
        current_config = self.load_config()
        if "profiles" not in current_config:
            current_config["profiles"] = {}

        current_config["profiles"][profile_name] = new_profile

        with open(self.config_path, "w") as f:
            json.dump(current_config, f, indent=4)

        # Atualiza a config em memória também
        self.config = current_config

    def _clear_unused_bet2_fields(self, profile: Dict[str, Any]) -> None:
        """Define campos da aposta 2 como None no perfil."""
        fields_to_clear = [
            "bet_value_area_2",
            "bet_value_click_2",
            "target_area_2",
            "target_click_2",
            "bet_button_area_2",
        ]
        for field in fields_to_clear:
            profile[field] = None

    def _calibrate_single_item(
        self, area_key: str, click_key: Optional[str], friendly_name: str
    ) -> Dict[str, Any]:
        """
        Calibra um único item da tela.
        (Extraído de run_calibration_wizard)
        """
        self.console.print(f"\n📍 Mapeando: [bold cyan]{friendly_name}[/bold cyan]")

        # Captura Topo-Esquerdo
        self.console.print(
            "   1. Mouse no [green]CANTO SUPERIOR ESQUERDO[/green] da área."
        )
        self.console.input("      [Enter] para capturar...")
        x1, y1 = pyautogui.position()
        self.console.print(f"      -> Topo: ({x1}, {y1})", style="dim")

        # Captura Base-Direita
        self.console.print(
            "   2. Mouse no [green]CANTO INFERIOR DIREITO[/green] da área."
        )
        self.console.input("      [Enter] para capturar...")
        x2, y2 = pyautogui.position()
        self.console.print(f"      -> Base: ({x2}, {y2})", style="dim")

        # Cálculos
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        # Cria já com o valor (1 passo)
        result = {
            area_key: {
                "x": left,
                "y": top,
                "width": width,
                "height": height,
            }
        }

        # Calcula ponto de clique se necessário
        if click_key:
            cx, cy = left + (width // 2), top + (height // 2)
            result[click_key] = {"x": cx, "y": cy}
            self.console.print(f"      -> Clique calculado: ({cx}, {cy})", style="dim")

        self.console.print("✅ Salvo!", style="green")
        time.sleep(0.3)

        return result

    def _get_items_to_calibrate(
        self, use_bet_2: bool
    ) -> list[tuple[str, Optional[str], str]]:
        """Retorna a lista de itens para calibração."""
        items = [
            (
                "multiplier_area",
                None,
                "MÚLTIPLICADOR (Onde os números voam/explodem no centro)",
            ),
            ("balance_area", None, "SALDO (O valor R$ no topo da tela)"),
            (
                "bet_area",
                None,
                "STATUS DA APOSTA (Onde aparece 'Apostar' ou contagem regressiva)",
            ),
            (
                "bet_value_area_1",
                "bet_value_click_1",
                "CAMPO VALOR (Esquerda - Onde tem botões 1/2 e X2)",
            ),
            (
                "target_area_1",
                "target_click_1",
                "CAMPO AUTO-RETIRAR (Direita - Onde digita o multiplicador ex: 2.00)",
            ),
            ("bet_button_area_1", None, "BOTÃO VERDE GRANDE (Apostar)"),
        ]

        if use_bet_2:
            items.extend(
                [
                    ("bet_value_area_2", "bet_value_click_2", "CAMPO VALOR: Aposta 2"),
                    (
                        "target_area_2",
                        "target_click_2",
                        "CAMPO ALVO (Target): Aposta 2",
                    ),
                    ("bet_button_area_2", None, "BOTÃO VERDE: Apostar 2"),
                ]
            )

        return items


def main():
    """Função principal."""
    console = Console()
    bot = None
    try:
        console.clear()
        console.print(
            Panel(
                Text("CRASH BOT - ML (Versão Comercial)", justify="center"),
                style="cyan bold",
                padding=(1, 10),
            )
        )
        console.print()

        instructions = Text()
        instructions.append("INSTRUÇÕES:\n", style="bold yellow")
        instructions.append("- Certifique-se que o jogo está visível na tela\n")
        instructions.append("- Selecione seu perfil\n")
        instructions.append("- Escolha seu modo de risco\n")
        instructions.append("- O saldo será detectado automaticamente\n")
        instructions.append("- Todos os dados serão salvos automaticamente\n")
        instructions.append("- Pressione [bold]Ctrl+C[/bold] para parar o bot\n")

        console.print(Panel(instructions, title="Setup", border_style="green"))
        console.print()

        console.input("[green]Pressione Enter para continuar...[/green]")

        console.print("⏳ Inicializando BotController...", style="yellow")
        try:
            bot = BotController()
            console.print("✅ BotController inicializado com sucesso.", style="green")
        except Exception:
            console.print(
                "\n\n[bold red]❌ ERRO FATAL DURANTE A INICIALIZAÇÃO:[/bold red]"
            )
            console.print_exception(show_locals=True)
            input("Pressione Enter para sair...")
            return

        console.print("🚀 Tentando iniciar o bot (bot.start())...", style="cyan")
        try:
            bot.start()
        except KeyboardInterrupt:
            console.print(
                "\n\nBot interrompido pelo usuário durante a execução.", style="yellow"
            )
        except Exception:
            console.print("\n\n[bold red]❌ ERRO FATAL DURANTE bot.start():[/bold red]")
            console.print_exception(show_locals=True)
            if bot and bot.running:
                try:
                    bot.stop()
                except Exception:
                    console.print("[red]Erro adicional ao tentar parar o bot:[/red]")
                    console.print_exception()

    except Exception:
        console.print("\n\n[bold red]❌ Erro inesperado GERAL:[/bold red]")
        console.print_exception()

    finally:
        console.print("\nExecutando bloco finally...", style="dim")
        if bot is not None and bot.running:
            console.print("Tentando parar o bot no finally...", style="dim")
            try:
                bot.stop()
            except Exception:
                console.print("[red]Erro no finally ao tentar parar o bot:[/red]")
                console.print_exception()
        else:
            console.print("Objeto 'bot' não foi criado ou já parado.", style="dim")

        console.print("\nBot encerrado.", style="green")
        console.input("\n[cyan]Pressione Enter para sair...[/cyan]")


if __name__ == "__main__":
    main()
