#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BOT CONTROLLER - ML (Versão Comercial com Modos de Risco)
MODIFICADO: Interface atualizada com troca de modo via teclado
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
import tkinter as tk
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
# 3. CORREÇÃO DE CAMINHO
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ==============================================================================
# 4. IMPORTS DO SEU PROJETO
# ==============================================================================
import notification_manager  # noqa: E402
from config import BASE_DIR  # noqa: E402
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
BOT_VERSION = "2.0.0"

# Token padrão do bot Telegram (fallback)
TELEGRAM_BOT_TOKEN_DEFAULT = "8329220374:AAHsK2aMseiAJpxzggsRutkz-S638eQWc8s"


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
                ("Total", {"justify": "right"}),
                ("Acertos", {"justify": "right", "style": "green"}),
                ("Erros", {"justify": "right", "style": "red"}),
                ("%", {"justify": "right"}),
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
        self.console = Console()
        self.config_path = os.path.join(BASE_DIR, config_filename)
        self.config = self.load_config()

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

        # Token do bot Telegram (centralizado - mesmo para todos os clientes)
        # O chat_id será carregado da API durante validação da licença
        notification_config = self.config.get("notifications", {})
        token_from_config = notification_config.get("telegram_bot_token")

        # Usa token do config se válido, senão usa o padrão embutido
        if (
            token_from_config
            and "CHAVE_AQUI" not in token_from_config
            and "COLE_SEU" not in token_from_config
        ):
            self.telegram_bot_token = token_from_config
        else:
            self.telegram_bot_token = TELEGRAM_BOT_TOKEN_DEFAULT

        self.vision = VisionSystem(str(self.config_path))
        self.learning_engine = LearningEngine()
        self.strategy = StrategyEngine(learning_engine=self.learning_engine)
        self.db_manager = DatabaseManager()

        self.running = False
        self.session_start = datetime.now()
        self.explosions = []
        self.round_count = 0
        self.initial_balance = None
        self.current_balance = None
        self.balance_history = []

        self.selected_risk_mode: Optional[RiskMode] = None
        self._pending_risk_mode: Optional[RiskMode] = None
        self.executed_bet_pending: Optional[Dict] = None
        self.last_round_id: Optional[int] = None

        self.balance_lock = threading.Lock()
        self.buffer_lock = threading.Lock()

        self.capture_thread = None
        self.detect_thread = None
        self.ui_thread = None
        self.balance_thread = None
        self.keyboard_thread = None

        self.frame_buffer = deque(maxlen=10)
        self.screen_areas = {}
        self.last_action = ""
        self.selected_profile = ""

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
        )

        self.last_balance_alert_time = time.time()
        self.live_display: Optional[Live] = None

        self.selected_profile = self.setup_screen_areas()
        risk_mode = self._perguntar_configuracoes_sessao()
        self.selected_risk_mode = risk_mode
        self._pending_risk_mode = risk_mode

        self.console.print("✅ BotController inicializado com sucesso!", style="green")
        self.console.print(
            f"📊 Database Manager ativo: {self.db_manager.session_id}", style="cyan"
        )

    def _perguntar_configuracoes_sessao(self) -> RiskMode:
        """Coleta o modo de risco do usuário."""
        self.console.print("\n[bold cyan]━━━ CONFIGURAÇÃO DA SESSÃO ━━━[/bold cyan]")
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

    def _send_telemetry(
        self,
        tipo: str,
        dados: Optional[Union[dict, str]] = None,
        lucro: float = 0.0,
        # Novos campos opcionais
        saldo: Optional[float] = None,
        valor_aposta: Optional[float] = None,
        modo_risco: Optional[str] = None,
        estrategia: Optional[str] = None,
        target: Optional[float] = None,
        explosao: Optional[float] = None,
        resultado: Optional[str] = None,
        sequencia_perdas: Optional[int] = None,
        banca_inicial: Optional[float] = None,
        banca_final: Optional[float] = None,
        stop_loss_atingido: bool = False,
        meta_atingida: bool = False,
        # Campos de sessão
        dobra_atual: Optional[int] = None,
        total_rodadas: Optional[int] = None,
        tempo_sessao_segundos: Optional[int] = None,
    ):
        """Envia dados de telemetria completos para o servidor."""
        if not hasattr(self, "db_manager") or not self.db_manager.session_id:
            return

        endpoint = f"{API_URL}/api/v1/telemetria/log"

        # Converte dados para string se for dict
        dados_str = ""
        if dados is not None:
            dados_str = json.dumps(dados) if isinstance(dados, dict) else str(dados)

        payload = {
            # Campos obrigatórios
            "hwid": get_hwid(),
            "sessao_id": self.db_manager.session_id,
            "tipo": tipo,
            "dados": dados_str,
            "lucro": lucro,
            # Campos financeiros
            "saldo": saldo,
            "valor_aposta": valor_aposta,
            "banca_inicial": banca_inicial,
            "banca_final": banca_final,
            # Campos de jogo
            "modo_risco": modo_risco,
            "estrategia": estrategia,
            "target": target,
            "explosao": explosao,
            "resultado": resultado,
            "sequencia_perdas": sequencia_perdas,
            "dobra_atual": dobra_atual,
            # Sessão
            "total_rodadas": total_rodadas,
            "tempo_sessao_segundos": tempo_sessao_segundos,
            # Alertas (convertido para "S" ou "N")
            "stop_loss_atingido": "S" if stop_loss_atingido else "N",
            "meta_atingida": "S" if meta_atingida else "N",
            # Metadados
            "versao_bot": BOT_VERSION,
            "sistema_operacional": f"{os.name}_{sys.platform}",
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

    def _parse_tempo_horas(self, raw: Any, default: int = 8) -> int:
        """Normaliza valores de tempo."""
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(raw)
        if isinstance(raw, str):
            try:
                return int(float(raw.strip()))
            except (TypeError, ValueError):
                return default
        if isinstance(raw, dict):
            for key in ("value", "hours", "tempo", "tempo_horas"):
                if key in raw:
                    return self._parse_tempo_horas(raw[key], default)
        return default

    def setup_screen_areas(self):
        """Configura áreas da tela baseado no perfil selecionado."""
        if not self.config:
            self.config = {"profiles": {}}
        profiles = self.config.get("profiles", {})
        if not profiles:
            self.console.print(
                "\n[yellow]⚠️ Nenhum perfil encontrado. "
                "Iniciando assistente...[/yellow]"
            )
            time.sleep(2)
            name, data = self.run_calibration_wizard()
            if name and data:
                self.config = self.load_config()
                profile_name = name
                profile_data = data
            else:
                self.console.print("❌ Configuração cancelada.", style="red")
                return ""
        else:
            result = self.select_profile()
            if not result:
                return ""
            profile_name, profile_data = result

        self.players = self.config.get("jogadores", [])
        raw_tempo = self.config.get("tempo_horas", 8)
        tempo_horas = self._parse_tempo_horas(raw_tempo, 8)
        self.max_time = tempo_horas * 3600
        # Correção para garantir que não estamos tentando converter um dicionário/None
        raw_rounds = self.config.get("max_rodadas", 1000)
        self.max_rounds = (
            int(raw_rounds) if isinstance(raw_rounds, (int, float, str)) else 1000
        )

        raw_profit = self.config.get("meta_lucro_total", 1000)
        self.target_profit = (
            float(raw_profit) if isinstance(raw_profit, (int, float, str)) else 1000.0
        )

        raw_hour = self.config.get("horario_inicio", 9)
        self.start_hour = (
            int(raw_hour) if isinstance(raw_hour, (int, float, str)) else 9
        )

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

        self.console.print(f"✅ Perfil '{profile_name}' carregado!", style="green")
        critical_areas = ["balance", "multiplier", "bet_detection"]
        if missing_areas := [
            area for area in critical_areas if not self.screen_areas.get(area)
        ]:
            self.console.print(
                f"⚠️ Áreas críticas não configuradas: {missing_areas}", style="yellow"
            )

        bet_areas = ["bet_value_1", "target_1", "bet_button_1"]
        configured_bet = sum(bool(self.screen_areas.get(area)) for area in bet_areas)
        if configured_bet == len(bet_areas):
            self.console.print("✅ Apostas automáticas: HABILITADAS", style="green")
        else:
            self.console.print("⚠️ Apostas automáticas: DESATIVADAS", style="yellow")
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
                    if validated := self._validate_and_confirm_balance_change(
                        new_balance, current_balance_snapshot
                    ):
                        with self.balance_lock:
                            old_balance = self.current_balance or 0.0
                            self.current_balance = validated
                            initial_balance_snapshot = self.initial_balance
                        self.balance_history.append(validated)
                        change = validated - old_balance
                        self.last_action = (
                            f"💰 Saldo: R${validated:.2f} "
                            f"([green]{change:+.2f}[/green])"
                        )
                        if initial_balance_snapshot:
                            self._check_and_trigger_stop_loss(
                                validated, initial_balance_snapshot
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
        change_pct = abs(new_balance - current_balance) / current_balance * 100
        if change_pct <= self.balance_change_threshold_pct:
            return new_balance
        self.console.print(
            f"⚠️  Mudança drástica de saldo ({change_pct:.1f}%). Confirmando...",
            style="yellow",
        )
        time.sleep(1)
        balance_area = self.screen_areas.get("balance")
        if not balance_area:
            return None
        with self.balance_lock:
            current_balance_snapshot = self.current_balance
        confirmed = self.vision.get_balance(balance_area, current_balance_snapshot)
        if not confirmed or abs(confirmed - new_balance) > 5:
            self.console.print(
                f"❌ Confirmação falhou. Descartando: {new_balance:.2f}", style="red"
            )
            return None
        return confirmed

    def _check_and_trigger_stop_loss(
        self, current_balance: float, initial_balance: float
    ):
        """Verifica stop-loss."""
        if self.stop_loss_alerted:
            return
        threshold = initial_balance * (1 - self.stop_loss_threshold_pct)
        if initial_balance > 0 and current_balance < threshold:
            loss_pct = (1 - (current_balance / initial_balance)) * 100
            msg = (
                f"🚨 *ALERTA DE STOP-LOSS!* 🚨\n"
                f"Banca caiu abaixo de {self.stop_loss_threshold_pct:.0%}.\n"
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
                    if (
                        multiplier := self.vision.get_multiplier(multiplier_area)
                    ) and 1.0 <= multiplier <= 999.99:
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

            with self.balance_lock:
                current_balance = self.current_balance or 0.0

            self._send_telemetry(
                tipo="round",
                dados=f"Explosao: {explosion_value:.2f}x",
                lucro=0.0,
                saldo=current_balance,
                explosao=explosion_value,
                modo_risco=(
                    self.selected_risk_mode.name if self.selected_risk_mode else None
                ),
            )

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
                msg = "✅ *OPERAÇÕES RETOMADAS!*\n" "Período de suspensão terminado."
                self.trigger_alert("resume", msg)
            return False
        elif self._check_profit_target_reached(current_balance):
            return False
        return True

    def _check_profit_target_reached(self, current_balance: float) -> bool:
        """Verifica se a meta de lucro foi atingida."""
        if self.strategy.checar_meta_lucro(current_balance):
            if (
                self.strategy.banca_inicial is None
                or self.strategy.meta_lucro_percentual is None
            ):
                self.logger.error("Falha ao suspender: Dados são None.")
                return True
            meta_valor = self.strategy.banca_inicial * (
                1 + self.strategy.meta_lucro_percentual
            )
            self.last_action = "🏆 META ATINGIDA! Suspendendo por 4 horas..."
            msg = (
                f"🏆 *META DE LUCRO ATINGIDA!* 🏆\n"
                f"Meta: R$ {meta_valor:.2f}\n"
                f"Saldo: R$ {current_balance:.2f}\n"
                f"Suspensão: 4 horas."
            )
            self.trigger_alert("suspend", msg)
            return True
        return False

    def _prepare_next_round_bet(self, current_balance: float, explosion_value: float):
        """Processa a estratégia e prepara a próxima aposta."""
        result = self.strategy.add_explosion_value(explosion_value)
        strategy_activated, _, veto_message = result
        if veto_message:
            self.last_action += f" | [yellow]{veto_message}[/yellow]"
        if recommendation := self.strategy.prepare_bets_for_balance(current_balance):
            self.last_action = (
                f"🎯 ESTRATÉGIA PREPARADA: {recommendation.strategy_name}"
            )
            if self.can_execute_bets():
                self.last_action += " | 🚀 EXECUTANDO"
                self.execute_prepared_bets()
            else:
                self.last_action += " | ⚠️ Áreas não calibradas"

    def _handle_previous_bet_result(self, explosion_value: float):
        """Processa o resultado da aposta pendente."""
        if not self.executed_bet_pending:
            return
        try:
            self._process_bet_evaluation(explosion_value, self.executed_bet_pending)
        except Exception as e:
            self.logger.error(f"Erro ao processar resultado anterior: {e}")
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
            f"*Saldo: R$ {current_balance:.2f}*"
        )
        if result["recommendation_hit"]:
            hit_status = "[green]✅ HIT[/green]"
            msg_meta = ""
            try:
                if self.strategy.banca_inicial and self.strategy.meta_lucro_percentual:
                    meta_abs = self.strategy.banca_inicial * (
                        1 + self.strategy.meta_lucro_percentual
                    )
                    falta = meta_abs - current_balance
                    if falta > 0:
                        msg_meta = f"\n*Falta: R$ {falta:.2f}*"
            except Exception as e:
                self.logger.error(f"Erro meta: {e}")
            msg = f"✅ *HIT!* | {strategy_name}\n{base_msg}{msg_meta}"
            self.trigger_alert("hit", msg)
        else:
            hit_status = "[red]❌ MISS[/red]"
            msg = f"❌ *MISS!* | {strategy_name}\n{base_msg}"
            self.trigger_alert("miss", msg)
        self.last_action += f" | {hit_status}"
        if self.last_round_id:
            resultado = (
                RESULTADO_HIT if result["recommendation_hit"] else RESULTADO_MISS
            )
            dados_aposta = BetData(
                rodada_id=self.last_round_id,
                estrategia=result.get("strategy", "Estratégia"),
                aposta_1=result.get("bet_1", 0.0),
                target_1=result.get("target_1", 0.0),
                aposta_2=0.0,
                target_2=0.0,
                resultado_1=resultado,
                resultado_2=RESULTADO_MISS,
                lucro_liquido=result.get("profit_loss", 0.0),
                timestamp=datetime.now().isoformat(),
            )
            self.db_manager.save_bet(dados_aposta)

            # Obter sequência de perdas do martingale (se disponível)
            sequencia_perdas = None
            try:
                for policy in self.strategy.policies:
                    if hasattr(policy, "perdas_consecutivas"):
                        sequencia_perdas = getattr(policy, "perdas_consecutivas", None)
                        break
            except Exception:
                pass

            # Obter dobra atual do strategy
            analysis = self.strategy.get_current_analysis()
            dobra = analysis.get("dobra_atual", 1)
            self._send_telemetry(
                tipo="bet",
                dados=f"Resultado: {resultado}",
                lucro=dados_aposta.lucro_liquido,
                saldo=current_balance,
                valor_aposta=result.get("bet_1", 0.0),
                modo_risco=(
                    self.selected_risk_mode.name if self.selected_risk_mode else None
                ),
                estrategia=result.get("strategy"),
                target=result.get("target_1"),
                explosao=explosion_value,
                resultado=resultado,
                sequencia_perdas=sequencia_perdas,
                dobra_atual=dobra,
            )

    def can_execute_bets(self) -> bool:
        """Verifica apenas áreas do BET 1."""
        required_areas = ["bet_value_1", "target_1", "bet_button_1"]
        if missing := [a for a in required_areas if not self.screen_areas.get(a)]:
            self.console.print(f"❌ Áreas não configuradas: {missing}", style="red")
            return False
        return True

    def execute_prepared_bets(self):
        """Executa apenas BET 1."""
        try:
            if not (
                (recommendation := self.strategy.get_prepared_bets())
                and recommendation.ready
            ):
                return
            self.last_action = f"⚡ EXECUTANDO BET 1: {recommendation.strategy_name}"
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
            self.last_action = f"❌ Erro: {e}"

    def trigger_alert(self, alert_type: str, message: Optional[str] = None):
        """Dispara alerta sonoro e notificação."""
        if self.is_windows:
            try:
                if alert_type == "hit":
                    winsound.Beep(frequency=1500, duration=150)
                elif alert_type == "miss":
                    winsound.Beep(frequency=700, duration=300)
                elif alert_type == "stop_loss":
                    self.last_action = "🚨 STOP-LOSS! 🚨"
                    for _ in range(3):
                        winsound.Beep(frequency=500, duration=1000)
                        time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Erro som: {e}")
        if message:
            notification_manager.send_telegram_alert(message)

    def fill_bet_fields_and_submit(self, bet_value_1: float, target_1: float) -> bool:
        """Preenche campos e submete aposta."""
        try:
            bet_value_1 = max(1.0, bet_value_1)
            bet_value_1_str = f"{bet_value_1:.2f}"
            target_1_str = f"{target_1:.2f}"
            area_value = self.screen_areas.get("bet_value_1")
            area_target = self.screen_areas.get("target_1")
            area_button = self.screen_areas.get("bet_button_1")
            if not area_value or not area_target or not area_button:
                return False
            if not self.click_and_fill_field(area_value, bet_value_1_str, "valor"):
                return False
            time.sleep(random.uniform(0.1, 0.2))
            if not self.click_and_fill_field(area_target, target_1_str, "target"):
                return False
            time.sleep(random.uniform(0.1, 0.2))
            if not self.click_area(area_button, "botão"):
                return False
            time.sleep(1.0)
            self.return_focus_to_bot()
            return True
        except Exception as e:
            self.logger.error(f"Erro BET 1: {e}")
            return False

    def click_and_fill_field(self, area: Dict, value: str, description: str) -> bool:
        """Clica em campo e preenche valor."""
        try:
            if not area:
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
            self.logger.error(f"Erro preencher {description}: {e}")
            return False

    def click_area(self, area: Dict, description: str) -> bool:
        """Clica em uma área."""
        try:
            if not area:
                return False
            center_x = area["x"] + area["width"] // 2
            center_y = area["y"] + area["height"] // 2
            offset_x = random.randint(-area["width"] // 4, area["width"] // 4)
            offset_y = random.randint(-area["height"] // 4, area["height"] // 4)
            x = center_x + offset_x
            y = center_y + offset_y
            x = max(area["x"], min(area["x"] + area["width"], x))
            y = max(area["y"], min(area["y"] + area["height"], y))
            self.move_mouse_humanlike(x, y)
            if random.random() < 0.2:
                time.sleep(random.uniform(0.1, 0.3))
            pyautogui.click()
            return True
        except Exception as e:
            self.logger.error(f"Erro clicar {description}: {e}")
            return False

    def move_mouse_humanlike(self, target_x: int, target_y: int):
        """Move mouse de forma humana."""
        try:
            current_x, current_y = pyautogui.position()
            dx = target_x - current_x
            dy = target_y - current_y
            distance = (dx**2 + dy**2) ** 0.5
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
            self.logger.error(f"Erro mover mouse: {e}")

    def return_focus_to_bot(self):
        """Retorna foco para o bot."""
        try:
            pyautogui.keyDown("alt")
            time.sleep(0.1)
            pyautogui.press("tab")
            time.sleep(0.1)
            pyautogui.keyUp("alt")
        except Exception as e:
            self.logger.error(f"Erro foco: {e}")

    # ========== TROCA DE MODO VIA TECLADO ==========

    def listen_keyboard_continuously(self):
        """Thread para escutar teclas 1, 2, 3 para troca de modo."""
        try:
            import msvcrt
        except ImportError:
            self.logger.warning("msvcrt não disponível")
            return
        while self.running:
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode("utf-8", errors="ignore")
                    if key == "1":
                        self._trocar_modo_runtime(RiskMode.CONSERVADOR)
                    elif key == "2":
                        self._trocar_modo_runtime(RiskMode.MODERADO)
                    elif key == "3":
                        self._trocar_modo_runtime(RiskMode.AGRESSIVO)
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Erro teclado: {e}")
                time.sleep(1)

    def _trocar_modo_runtime(self, novo_modo: RiskMode):
        """Troca o modo de risco durante a execução."""
        if self.selected_risk_mode == novo_modo:
            self.last_action = f"⚠️ Já está no modo {novo_modo.name}"
            return
        with self.balance_lock:
            saldo_atual = self.current_balance or self.initial_balance or 100.0
        modo_anterior = self.selected_risk_mode
        self.selected_risk_mode = novo_modo
        self.strategy.trocar_modo(novo_modo, saldo_atual)
        self.round_count = 0
        self.explosions = []
        self.session_start = datetime.now()
        with self.balance_lock:
            self.initial_balance = saldo_atual
        mode_colors = {
            RiskMode.CONSERVADOR: "green",
            RiskMode.MODERADO: "yellow",
            RiskMode.AGRESSIVO: "red",
        }
        color = mode_colors.get(novo_modo, "white")
        anterior_name = modo_anterior.name if modo_anterior else "N/A"
        self.last_action = (
            f"🔄 Modo: {anterior_name} → [{color}]{novo_modo.name}[/{color}]"
        )
        msg = (
            f"🔄 *MODO ALTERADO*\n"
            f"De: {anterior_name}\n"
            f"Para: {novo_modo.name}\n"
            f"Saldo: R$ {saldo_atual:.2f}"
        )
        notification_manager.send_telegram_alert(msg)
        self.logger.info(f"Modo alterado para {novo_modo.name}")

    # ========== FIM TROCA DE MODO ==========

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
                    if balance:
                        stats = self._get_current_history_stats()
                        mode_name = (
                            self.selected_risk_mode.name
                            if self.selected_risk_mode
                            else "N/A"
                        )
                        msg = (
                            f"🔔 *Relatório 30 min*\n"
                            f"Modo: {mode_name}\n"
                            f"Banca: R$ {balance:.2f}\n"
                            f"Média: {stats['mean_250']:.2f}x"
                        )
                        self.trigger_alert("periodic", msg)
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Erro UI: {e}")
                time.sleep(1)

    def build_dashboard_layout(self) -> Layout:
        """Cria o layout principal do dashboard."""
        if self.strategy.esta_suspenso():
            return self._build_suspension_layout()
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        layout["left"].split(
            Layout(name="balance", size=5),
            Layout(name="last_decision", size=5),
            Layout(name="history", ratio=1),
        )
        layout["right"].split(
            Layout(name="strategy", size=9),
            Layout(name="stats", ratio=1),
        )
        layout["header"].update(self._build_header_panel())
        layout["balance"].update(self._build_balance_panel())
        layout["last_decision"].update(self._build_last_decision_panel())
        layout["history"].update(self._build_history_panel())
        layout["strategy"].update(self._build_strategy_panel())
        layout["stats"].update(self._build_strategy_stats_panel())
        layout["footer"].update(self._build_footer_panel())
        return layout

    def _build_suspension_layout(self) -> Layout:
        """Layout para quando o bot está em suspensão."""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=4),
        )
        layout["header"].update(self._build_header_panel())
        tempo_restante = self.strategy.get_tempo_restante_suspensao()
        horas = tempo_restante // 3600
        minutos = (tempo_restante % 3600) // 60
        segundos = tempo_restante % 60
        countdown_text = Text()
        countdown_text.append("\n\n🏆 ", style="bold yellow")
        countdown_text.append("META BATIDA!", style="bold green")
        countdown_text.append(" 🏆\n\n", style="bold yellow")
        countdown_text.append("Bot em suspensão\n\n", style="dim")
        countdown_text.append("⏱️ Tempo restante:\n\n", style="yellow")
        countdown_text.append(
            f"{horas:02d}:{minutos:02d}:{segundos:02d}", style="bold cyan"
        )
        countdown_text.append("\n\n")
        with self.balance_lock:
            current_balance = self.current_balance or 0.0
        countdown_text.append(f"Saldo: R$ {current_balance:.2f}\n", style="green")
        if self.strategy.banca_inicial and self.strategy.meta_lucro_percentual:
            meta = self.strategy.banca_inicial * (
                1 + self.strategy.meta_lucro_percentual
            )
            countdown_text.append(f"Meta: R$ {meta:.2f}\n", style="dim")
        layout["main"].update(
            Panel(
                countdown_text,
                title="[bold yellow]SUSPENSÃO ATIVA[/bold yellow]",
                border_style="green",
            )
        )
        layout["footer"].update(self._build_footer_panel())
        return layout

    def _build_header_panel(self) -> Panel:
        """Constrói o painel de cabeçalho."""
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

    def _build_last_decision_panel(self) -> Panel:
        """Constrói o painel de última decisão do bot."""
        try:
            ultima_decisao, tipo = self.strategy.get_ultima_decisao()
            if tipo == "apostando":
                style = "bold green"
                border_style = "green"
            elif tipo == "pulou":
                style = "yellow"
                border_style = "yellow"
            else:
                style = "dim"
                border_style = "dim"
            text = Text(ultima_decisao, style=style)
            return Panel(
                text,
                title="[bold white]Última Decisão[/bold white]",
                border_style=border_style,
            )
        except Exception as e:
            self.logger.error(f"Erro painel decisão: {e}")
            return Panel(Text("Erro", style="red"), title="Última Decisão")

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
            if stats["mean_250"] > 0:
                stats["cv_250"] = stats["std_250"] / stats["mean_250"]
            stats["zeros_count"] = last_250_values.count(1.00)
            stats["max_streak"] = self._calculate_max_streak(last_250_values)
        return stats

    def _build_strategy_panel(self) -> Panel:
        """Constrói o painel de status da estratégia."""
        try:
            analysis_data = self.strategy.get_current_analysis()
            table = self._create_styled_table(
                title="", border_style="dim", show_header=False, expand=True
            )
            table.add_column("Item", style="cyan")
            table.add_column("Status", style="white")
            mode_colors = {
                "CONSERVADOR": "green",
                "MODERADO": "yellow",
                "AGRESSIVO": "red",
            }
            risk_mode_name = analysis_data.get("risk_mode", "N/A")
            mode_color = mode_colors.get(risk_mode_name, "white")
            table.add_row("Modo:", Text(risk_mode_name, style=f"bold {mode_color}"))
            martingale_active = analysis_data.get("martingale_active")
            status_text = (
                "[green]ATIVO[/green]"
                if martingale_active
                else "[yellow]Aguardando[/yellow]"
            )
            table.add_row("Martingale:", status_text)
            dobra_atual = analysis_data.get("dobra_atual", 1)
            table.add_row("Dobra Atual:", str(dobra_atual))
            gatilho_baixos = analysis_data.get("baixos_consecutivos", "N/A")
            table.add_row("Gatilho (Baixos):", gatilho_baixos)
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
            table.add_row("Confiança ML:", conf_text)
            return Panel(table, title="Status da Estratégia")
        except Exception as e:
            self.logger.error(f"Erro strategy panel: {e}")
            return Panel(Text(f"Erro: {e}", style="red"), title="Status")

    def _build_strategy_stats_panel(self) -> Panel:
        """Constrói o painel de estatísticas."""
        try:
            stats_list = self.strategy.get_strategies_stats()
            table = self._create_styled_table(
                title="",
                border_style="dim",
                header_style="bold magenta",
                show_header=True,
            )
            table.add_column("Estratégia", style="cyan")
            table.add_column("Total", justify="right")
            table.add_column("Acertos", justify="right", style="green")
            table.add_column("Erros", justify="right", style="red")
            table.add_column("%", justify="right")
            for stats in stats_list:
                if "MLHighConfidence" in stats["name"]:
                    continue
                nome = (
                    "Martingale"
                    if "CommercialMartingale" in stats["name"]
                    else stats["name"]
                )
                table.add_row(
                    nome,
                    str(stats["total_recommendations"]),
                    str(stats["total_hits"]),
                    str(stats["total_misses"]),
                    f"{stats['total_hit_rate']:.1f}%",
                )
            return Panel(table, title="Estatísticas")
        except Exception:
            return Panel(Text("Carregando...", style="dim"), title="Estatísticas")

    def _build_footer_panel(self) -> Panel:
        """Constrói o painel de rodapé com atalhos."""
        mode_colors = {
            RiskMode.CONSERVADOR: "green",
            RiskMode.MODERADO: "yellow",
            RiskMode.AGRESSIVO: "red",
        }
        text = Text()
        if self.selected_risk_mode:
            color = mode_colors.get(self.selected_risk_mode, "white")
            text.append("🎯 ", style="white")
            text.append(self.selected_risk_mode.name, style=f"bold {color}")
        else:
            text.append("🎯 N/A", style="dim")
        text.append(" | ", style="dim")
        text.append("[1]", style="bold green")
        text.append(" Cons ", style="green")
        text.append("[2]", style="bold yellow")
        text.append(" Mod ", style="yellow")
        text.append("[3]", style="bold red")
        text.append(" Agres", style="red")
        text.append(" | ", style="dim")
        text.append("Ctrl+C sair", style="dim")
        return Panel(text, style="dim")

    def _print_summary_footer_info(self):
        """Imprime informações de rodapé do resumo."""
        self.console.print(f"🆔 Sessão: {self.db_manager.session_id}", style="dim")
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
            finance_table.add_row("Resultado", profit_text_obj)
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
            self.console.print(f"⚠️ Tentativa {attempt+1}/8...", style="yellow")
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
        self.keyboard_thread = threading.Thread(
            target=self.listen_keyboard_continuously, daemon=True
        )
        self.balance_thread.start()
        self.capture_thread.start()
        self.detect_thread.start()
        self.ui_thread.start()
        self.keyboard_thread.start()

    def _initialize_balance(self):
        """Detecta o saldo inicial ou define um valor padrão."""
        balance_to_set = self.detect_initial_balance()
        if not balance_to_set:
            self.console.print("⚠️ Usando saldo padrão R$ 100,00", style="yellow")
            balance_to_set = 100.0
        self._set_initial_balance(balance_to_set)

    def _get_license_key(self) -> Optional[str]:
        """Gerencia o login do usuário."""
        filename = os.path.join(BASE_DIR, "license_key.txt")
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    content = f.read().strip()
                    if content and len(content) > 10:
                        return content
            except Exception as e:
                self.logger.error(f"Erro ler licença: {e}")
        self.console.clear()
        login_panel = Panel(
            Text.assemble(
                ("🔐 SISTEMA DE AUTENTICAÇÃO\n\n", "bold white"),
                ("Este software requer uma licença ativa.\n", "dim white"),
                ("Digite ou cole sua chave abaixo.", "yellow"),
            ),
            title="🔒 CrashBot Security",
            border_style="cyan",
            padding=(1, 5),
        )
        self.console.print(login_panel)
        self.console.print()
        if key_input := self.console.input(
            "[bold green]🔑 CHAVE DE LICENÇA: [/bold green]"
        ).strip():
            try:
                with open(filename, "w") as f:
                    f.write(key_input)
                self.console.print()
                self.console.print("✅ Licença salva!", style="green")
                time.sleep(1.5)
                return key_input
            except Exception as e:
                self.console.print(f"❌ Erro salvar: {e}", style="red")
                return None
        return None

    def _prompt_update(self, download_url: str, obrigatoria: bool) -> bool:
        """Exibe mensagem de atualização."""
        should_open_browser = False
        if obrigatoria:
            self.console.print("[bold red]⚠️ ATUALIZAÇÃO OBRIGATÓRIA![/bold red]")
            self.console.input("\n[yellow]Enter para abrir download...[/yellow]")
            should_open_browser = True
        else:
            resposta = self.console.input(
                "[yellow]Continuar mesmo assim? (S/N): [/yellow]"
            )
            if resposta.lower() != "s":
                should_open_browser = True
        if should_open_browser:
            import webbrowser

            webbrowser.open(download_url)
            return False
        return True

    def _check_for_updates(self) -> bool:
        """Verifica se há atualizações disponíveis."""
        try:
            self.console.print("🔍 Verificando atualizações...", style="cyan")
            response = requests.get(f"{API_URL}/api/v1/bot/versao", timeout=10)
            if response.status_code == 200:
                data = response.json()
                versao_servidor = data.get("versao", "0.0.0")
                if self._comparar_versoes(versao_servidor, BOT_VERSION):
                    return self._handle_update_found(
                        versao_servidor,
                        data.get("download_url", ""),
                        data.get("changelog", ""),
                        data.get("obrigatoria", False),
                    )
                else:
                    self.console.print(
                        f"[green]✅ Bot atualizado! v{BOT_VERSION}[/green]"
                    )
            elif response.status_code == 404:
                self.console.print("[yellow]⚠️ Nenhuma versão no servidor[/yellow]")
            return True
        except requests.exceptions.RequestException as e:
            self.console.print(f"[yellow]⚠️ Não verificou atualizações: {e}[/yellow]")
            return True
        except Exception as e:
            self.logger.error(f"Erro atualizações: {e}")
            return True

    def _handle_update_found(
        self, versao_servidor: str, download_url: str, changelog: str, obrigatoria: bool
    ) -> bool:
        """Exibe o banner de atualização."""
        self.console.print(f"\n[bold yellow]{'='*50}[/bold yellow]")
        self.console.print(
            f"[bold green]🎉 NOVA VERSÃO: v{versao_servidor}[/bold green]"
        )
        self.console.print(f"[white]Sua versão: v{BOT_VERSION}[/white]")
        if changelog:
            self.console.print(f"\n[cyan]Novidades:[/cyan]\n[white]{changelog}[/white]")
        self.console.print(f"\n[bold blue]Download: {download_url}[/bold blue]")
        self.console.print(f"[bold yellow]{'='*50}[/bold yellow]\n")
        return self._prompt_update(download_url, obrigatoria)

    def _parse_version(self, version: str) -> list:
        """Converte string de versão para lista de inteiros."""
        return [int(x) for x in version.split(".")]

    def _comparar_versoes(self, versao_nova: str, versao_atual: str) -> bool:
        """Compara duas versões."""
        try:
            return self._parse_version(versao_nova) > self._parse_version(versao_atual)
        except ValueError:
            return False

    def _validate_license(self) -> bool:
        """Verifica a licença no servidor."""
        local_hwid = get_hwid()
        license_key = self._get_license_key()
        if not license_key:
            self.console.print("❌ Chave de licença ausente.", style="bold red")
            return False
        endpoint = f"{API_URL}/validar"
        data = {"chave": license_key, "hwid": local_hwid}
        self.console.print("🔒 Conectando ao servidor...", style="dim")
        try:
            response = requests.post(endpoint, json=data, timeout=10)
            if response.status_code == 200:
                resp_data = response.json()
                self.console.print(
                    f"✅ LICENÇA VÁLIDA! {resp_data.get('mensagem', '')}",
                    style="bold green",
                )

                # Carregar telegram_chat_id do servidor (se disponível)
                telegram_chat_id = resp_data.get("telegram_chat_id")
                if telegram_chat_id and self.telegram_bot_token:
                    notification_manager.load_credentials(
                        self.telegram_bot_token, telegram_chat_id
                    )
                    self.console.print(
                        "✅ Notificações Telegram ATIVADAS", style="green"
                    )
                elif not telegram_chat_id:
                    self.console.print(
                        "ℹ️ Configure seu Telegram no painel web", style="dim"
                    )

                return True
            else:
                try:
                    resp_json = response.json()
                    msg = resp_json.get("mensagem", f"Erro HTTP {response.status_code}")
                except Exception:
                    msg = f"Erro HTTP {response.status_code}"
                self.console.print(f"❌ ACESSO NEGADO: {msg}", style="bold red")
                return False
        except requests.exceptions.RequestException:
            self.console.print("❌ ERRO CONEXÃO: Servidor offline.", style="bold red")
            return False

    def _run_main_loop(self):
        """Executa a lógica principal."""
        self.console.print("🚀 Iniciando Bot Controller...", style="cyan")
        if not self._check_for_updates():
            self.console.print(
                "\n[bold yellow]Bot encerrado para atualização.[/bold yellow]"
            )
            time.sleep(2)
            return
        if not self._validate_license():
            self.console.print(
                "\n[bold red]SISTEMA DESLIGADO POR FALHA NA LICENÇA.[/bold red]"
            )
            time.sleep(4)
            return
        time.sleep(2)
        self._initialize_balance()
        with self.balance_lock:
            banca_detectada = self.initial_balance or 100.0
        risk_mode_safe = self._pending_risk_mode or RiskMode.MODERADO
        self.strategy.iniciar_sessao(
            banca_inicial=banca_detectada, risk_mode=risk_mode_safe
        )
        self.running = True
        self._send_telemetry(
            tipo="sessao_inicio",
            dados="Sessao iniciada",
            lucro=0.0,
            saldo=banca_detectada,
            modo_risco=(
                self.selected_risk_mode.name if self.selected_risk_mode else None
            ),
            banca_inicial=banca_detectada,
        )
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
            self.last_action = "Encerrando..."
        except Exception as e:
            self.logger.error(f"Erro start: {e}")
            self.console.print_exception()
        finally:
            self.stop()

    def stop(self):
        """Para o bot."""
        if not self.running:
            return
        self.running = False
        self.console.print("Encerrando... Aguardando threads.", style="yellow")
        try:
            threads = [
                self.ui_thread,
                self.detect_thread,
                self.balance_thread,
                self.capture_thread,
                self.keyboard_thread,
            ]
            for thread in threads:
                if thread and thread.is_alive():
                    thread.join(timeout=1.0)
        except Exception as e:
            self.logger.error(f"Erro threads: {e}")
        if self.live_display:
            self.live_display.stop()
            self.console.clear()
        time.sleep(0.5)
        try:
            with self.balance_lock:
                final_balance = self.current_balance
                saldo_final = final_balance or 0.0
                saldo_inicial = self.initial_balance or 0.0
                lucro_sessao = saldo_final - saldo_inicial
            # Verificar se stop_loss ou meta foram atingidos
            stop_loss = getattr(self, "stop_loss_alerted", False)
            meta = (
                self.strategy.esta_suspenso()
                if hasattr(self.strategy, "esta_suspenso")
                else False
            )
            # Calcular tempo de sessão
            tempo_sessao = int((datetime.now() - self.session_start).total_seconds())
            self._send_telemetry(
                tipo="sessao_fim",
                dados=f"Sessao finalizada - {self.round_count} rodadas",
                lucro=lucro_sessao,
                saldo=saldo_final,
                modo_risco=(
                    self.selected_risk_mode.name if self.selected_risk_mode else None
                ),
                banca_inicial=saldo_inicial,
                banca_final=saldo_final,
                stop_loss_atingido=stop_loss,
                meta_atingida=meta,
                total_rodadas=self.round_count,
                tempo_sessao_segundos=tempo_sessao,
            )
            self.db_manager.close_session(final_balance)
            self.console.print("✅ Sessão fechada", style="green")
        except Exception as e:
            self.console.print(f"❌ Erro fechar sessão: {e}", style="red")
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
            main_panel_content.append(f"🎯 Modo: {self.selected_risk_mode.name}\n")
        if self.explosions:
            values = [e["value"] for e in self.explosions]
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            main_panel_content.append(
                f"📈 Min: {min_val:.2f}x | Max: {max_val:.2f}x | "
                f"Média: {avg_val:.2f}x\n"
            )
        self.console.print(
            Panel(main_panel_content, title="Resumo da Sessão", border_style="cyan")
        )
        self._print_financial_summary()
        self._print_summary_footer_info()

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
            self.logger.error(f"Tabela desconhecida: {table_type}")
            return Table(title=f"Erro: {table_type}")
        title = config.get("title", "")
        columns = config.get("columns", [])
        table_kwargs = {
            k: v for k, v in config.items() if k not in ["title", "columns"]
        }
        table = self._create_styled_table(title=title, **table_kwargs)
        for col_name, col_kwargs in columns:
            table.add_column(col_name, **col_kwargs)
        return table

    def _get_safe_balances(self) -> tuple:
        """Retorna o saldo atual e inicial de forma thread-safe."""
        with self.balance_lock:
            current = self.current_balance
            initial = self.initial_balance
        return current, initial

    def run_calibration_wizard(self):
        """Guia o usuário para mapear as áreas."""
        self.console.clear()
        self.console.print(
            Panel(
                "[bold yellow]MODO DE CALIBRAÇÃO[/bold yellow]\n\n"
                "Vou guiar você para mapear a tela.\n"
                "Para cada item, posicione no [cyan]Canto Superior Esquerdo[/cyan]\n"
                "e depois no [cyan]Canto Inferior Direito[/cyan].",
                border_style="yellow",
            )
        )
        profile_name = (
            self.console.input("\n[cyan]Nome do perfil: [/cyan]")
            or f"User_Profile_{int(time.time())}"
        )
        self.console.print("\n[yellow]Deseja calibrar APOSTA 2 (Double Bet)?[/yellow]")
        resp = self.console.input("Digite 's' para Sim ou Enter para pular: ").lower()
        use_bet_2 = resp == "s"
        items_to_calibrate = self._get_items_to_calibrate(use_bet_2)
        new_profile = {}
        for area_key, click_key, friendly_name in items_to_calibrate:
            item_data = self._calibrate_single_item(area_key, click_key, friendly_name)
            new_profile |= item_data
        if not use_bet_2:
            self._clear_unused_bet2_fields(new_profile)
        self.console.print("\n💾 Salvando...", style="yellow")
        if self._save_new_profile(profile_name, new_profile):
            return profile_name, new_profile
        return None, None

    def _save_new_profile(self, profile_name: str, new_profile: Dict) -> bool:
        """Salva o novo perfil."""
        try:
            self._persist_profile_data(profile_name, new_profile)
            self.console.print(
                f"✅ Perfil '{profile_name}' criado!", style="bold green"
            )
            return True
        except Exception as e:
            self.console.print(f"❌ Erro salvar: {e}", style="bold red")
            return False

    def _persist_profile_data(self, profile_name: str, new_profile: Dict) -> None:
        """Salva dados do perfil no arquivo."""
        current_config = self.load_config()
        if "profiles" not in current_config:
            current_config["profiles"] = {}
        current_config["profiles"][profile_name] = new_profile
        with open(self.config_path, "w") as f:
            json.dump(current_config, f, indent=4)
        self.config = current_config

    def _clear_unused_bet2_fields(self, profile: Dict[str, Any]) -> None:
        """Define campos da aposta 2 como None."""
        fields = [
            "bet_value_area_2",
            "bet_value_click_2",
            "target_area_2",
            "target_click_2",
            "bet_button_area_2",
        ]
        for field in fields:
            profile[field] = None

    def _select_area_visual(self, title: str) -> Optional[Dict]:
        """Abre tela para seleção visual de área (arrastar retângulo)."""
        result = {"x": 0, "y": 0, "width": 0, "height": 0}

        def on_press(event):
            nonlocal start_x, start_y
            start_x = event.x
            start_y = event.y
            if rect[0]:
                canvas.delete(rect[0])
            rect[0] = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='#00FF00', width=3)

        def on_drag(event):
            if rect[0]:
                canvas.coords(rect[0], start_x, start_y, event.x, event.y)

        def on_release(event):
            x1, y1 = min(start_x, event.x), min(start_y, event.y)
            x2, y2 = max(start_x, event.x), max(start_y, event.y)
            if (x2 - x1) > 5 and (y2 - y1) > 5:
                result["x"], result["y"] = x1, y1
                result["width"], result["height"] = x2 - x1, y2 - y1
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
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        canvas = tk.Canvas(root, width=screen_w, height=screen_h, bg='black', highlightthickness=0, cursor='cross')
        canvas.pack()
        canvas.create_text(screen_w // 2, 40, text=f"🎯 {title}", font=('Arial', 28, 'bold'), fill='white')
        canvas.create_text(screen_w // 2, 80, text="CLIQUE e ARRASTE para selecionar | ESC = cancelar", font=('Arial', 16), fill='yellow')
        canvas.bind('<ButtonPress-1>', on_press)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        root.bind('<Escape>', on_cancel)
        root.mainloop()
        return result if result["width"] > 0 else None

    def _calibrate_single_item(self, area_key: str, click_key: Optional[str], friendly_name: str) -> Optional[Dict[str, Any]]:
        """Calibra um único item da tela usando seleção visual."""
        area_result = self._select_area_visual(friendly_name)
        if not area_result:
            return None
        self.console.print(f"[green]✅ {friendly_name}: {area_result['width']}x{area_result['height']}[/green]")
        result = {area_key: area_result}
        if click_key:
            cx, cy = area_result["x"] + area_result["width"] // 2, area_result["y"] + area_result["height"] // 2
            result[click_key] = {"x": cx, "y": cy}
        return result

    def _get_items_to_calibrate(self, use_bet_2: bool) -> list:
        """Retorna a lista de itens para calibração."""
        items = [
            ("multiplier_area", None, "MULTIPLICADOR (centro da tela)"),
            ("balance_area", None, "SALDO (R$ no topo)"),
            ("bet_area", None, "BET 8s (Bet 8 segundos)"),
            ("bet_value_area_1", "bet_value_click_1", "CAMPO VALOR (esquerda)"),
            ("target_area_1", "target_click_1", "CAMPO AUTO-RETIRAR (direita)"),
            ("bet_button_area_1", None, "BOTÃO VERDE (Apostar)"),
        ]
        if use_bet_2:
            items.extend(
                [
                    ("bet_value_area_2", "bet_value_click_2", "CAMPO VALOR: Aposta 2"),
                    ("target_area_2", "target_click_2", "CAMPO ALVO: Aposta 2"),
                    ("bet_button_area_2", None, "BOTÃO: Apostar 2"),
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
        instructions.append("- Certifique-se que o jogo está visível\n")
        instructions.append("- Selecione seu perfil\n")
        instructions.append("- Escolha seu modo de risco\n")
        instructions.append("- O saldo será detectado automaticamente\n")
        instructions.append("- Pressione [bold]Ctrl+C[/bold] para parar\n")
        instructions.append(
            "- Pressione [bold]1, 2 ou 3[/bold] para trocar modo\n", style="cyan"
        )
        console.print(Panel(instructions, title="Setup", border_style="green"))
        console.print()
        console.input("[green]Pressione Enter para continuar...[/green]")
        console.print("⏳ Inicializando...", style="yellow")
        try:
            bot = BotController()
            console.print("✅ BotController inicializado.", style="green")
        except Exception:
            console.print("\n\n[bold red]❌ ERRO FATAL NA INICIALIZAÇÃO:[/bold red]")
            console.print_exception(show_locals=True)
            input("Pressione Enter para sair...")
            return
        console.print("🚀 Iniciando bot...", style="cyan")
        try:
            bot.start()
        except KeyboardInterrupt:
            console.print("\n\nBot interrompido pelo usuário.", style="yellow")
        except Exception:
            console.print("\n\n[bold red]❌ ERRO FATAL:[/bold red]")
            console.print_exception(show_locals=True)
            if bot and bot.running:
                try:
                    bot.stop()
                except Exception:
                    console.print_exception()
    except Exception:
        console.print("\n\n[bold red]❌ Erro inesperado:[/bold red]")
        console.print_exception()
    finally:
        console.print("\nExecutando finally...", style="dim")
        if bot is not None and bot.running:
            try:
                bot.stop()
            except Exception:
                console.print_exception()
        console.print("\nBot encerrado.", style="green")
        console.input("\n[cyan]Pressione Enter para sair...[/cyan]")


if __name__ == "__main__":
    main()
