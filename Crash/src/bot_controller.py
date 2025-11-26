#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BOT CONTROLLER - ML (Versão Refatorada)
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
# 2. IMPORTS DE TERCEIROS (PIP) - Ficam ANTES do sys.path
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
# 3. CORREÇÃO DE CAMINHO (Para importar arquivos da pasta raiz)
# ==============================================================================
# Adiciona a pasta pai (../) ao caminho para encontrar config.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ==============================================================================
# 4. IMPORTS DO SEU PROJETO (Dependem do sys.path, por isso precisam de noqa)
# ==============================================================================
import notification_manager  # noqa: E402
from config import BASE_DIR  # noqa: E402
from database_manager import RESULTADO_MISS  # noqa: E402
from database_manager import RESULTADO_HIT, BetData, DatabaseManager, RoundData
from learning_engine import LearningEngine  # noqa: E402
from security import get_hwid  # noqa: E402
from strategy_engine import StrategyEngine  # noqa: E402
from vision.vision_system import VisionSystem  # noqa: E402

# ==============================================================================
# 5. CONSTANTES GLOBAIS
# ==============================================================================
API_URL = "https://crash-api-jose.onrender.com"  # Sua URL do Render


class TableType(Enum):
    """Define os tipos de tabelas pré-configuradas da UI."""

    DATABASE_STATS = "DATABASE_STATS"
    STRATEGY_STATS = "STRATEGY_STATS"
    FINANCIAL_SUMMARY = "FINANCIAL_SUMMARY"


class BotController:
    """Controlador principal que integra todos os módulos do bot.

    Esta versão é refatorada para:
    1. Usar a nova arquitetura do StrategyEngine.
    2. Implementar uma UI moderna com 'rich'.
    3. Ser 'thread-safe' no acesso ao saldo.
    4. Carregar parâmetros de configuração do config.json.
    """

    # --- ETAPA 2 (Enum Refactor): Configuração centralizada das tabelas ---
    _TABLE_CONFIGS: Dict[TableType, Dict] = {
        TableType.DATABASE_STATS: {
            "title": "Estatísticas do Database",
            "columns": [
                ("Métrica", {"style": "white"}),
                ("Valor", {"style": "bold white"}),
            ],
        },
        TableType.STRATEGY_STATS: {
            "title": "",  # Título é ""
            "border_style": "dim",  # Estilo específico
            "header_style": "bold magenta",  # Estilo específico
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
        # --- ETAPA 1: Inicialização do 'rich' ---
        self.console = Console()

        self.config_path = os.path.join(BASE_DIR, config_filename)

        self.config = self.load_config()

        # --- ETAPA 2: Carregar Parâmetros do Bot ---
        bot_params = self.config.get("bot_parameters", {})
        self.cooldown_seconds = bot_params.get("cooldown_seconds", 8)
        self.balance_check_interval = bot_params.get("balance_check_interval", 3.0)
        self.balance_change_threshold_pct = bot_params.get(
            "balance_change_threshold_pct", 30
        )
        self.frame_interval = bot_params.get("frame_interval", 0.05)

        self.stop_loss_threshold_pct = bot_params.get("stop_loss_threshold_pct", 0.50)
        self.stop_loss_alerted = False  # Flag para não disparar o alarme várias vezes
        self.is_windows = os.name == "nt"  # Checa se estamos no Windows

        notification_config = self.config.get("notifications", {})
        token = notification_config.get("telegram_bot_token")
        chat_id = notification_config.get("telegram_chat_id")

        if token and chat_id and "COLE_SEU" not in token:
            notification_manager.load_credentials(token, chat_id)
            # Imprime no console (substituindo o print antigo)
            self.console.print("✅ Alertas do Telegram HABILITADOS", style="green")
        else:
            self.console.print(
                "⚠️  Alertas do Telegram DESABILITADOS (Token/ChatID não configurados).",
                style="yellow",
            )

        # Módulos principais
        self.vision = VisionSystem(str(self.config_path))
        self.learning_engine = LearningEngine()
        # Treina o modelo ao iniciar
        # self.learning_engine.train_model() # Descomente se desejar treinar no início

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

        # --- ETAPA 3: Gerenciamento de apostas (movido do strategy) ---
        self.executed_bet_pending: Optional[Dict] = None
        self.last_round_id: Optional[int] = None

        # --- ETAPA 4: Correção de Thread-Safety ---
        self.balance_lock = threading.Lock()
        self.buffer_lock = threading.Lock()

        # Threading
        self.capture_thread = None
        self.detect_thread = None
        self.ui_thread = None
        self.balance_thread = None

        # Buffer para detecção
        self.frame_buffer = deque(maxlen=10)

        # Áreas da tela (carregadas do config)
        self.screen_areas = {}
        self.last_action = ""
        self.selected_profile = ""

        # Logger
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
        )

        self.last_balance_alert_time = time.time()  # Para o alerta periódico

        # O Live é inicializado no 'start' para não poluir o setup
        self.live_display: Optional[Live] = None

        # Configurar áreas da tela
        self.selected_profile = self.setup_screen_areas()

        # Perguntar a banca inicial manualmente logo após o perfil
        # 1. Perguntar as configurações (usando o bot_controller / Rich)
        banca, meta, suspensao, modo = self._perguntar_configuracoes_sessao()

        # 2. Passar as configurações para o "cérebro" (strategy_engine)
        self.strategy.iniciar_sessao(
            banca_inicial=banca,
            meta_pct=meta,
            tempo_suspensao=suspensao,
            modo_ciclo=modo,
        )

        self.console.print("✅ BotController inicializado com sucesso!", style="green")
        self.console.print(
            f"📊 Database Manager ativo: {self.db_manager.session_id}", style="cyan"
        )

    def _obter_escolha_valida(self, prompt: str, opcoes: Dict[str, Any]) -> Any:
        """Helper genérico da UI (com Rich) para obter uma escolha válida."""
        while True:
            try:
                # Usa o console do "Rich" para perguntar
                escolha = self.console.input(f"[green]{prompt}[/green]")
                if escolha in opcoes:
                    return opcoes[escolha]  # Apenas retorna o valor
                else:
                    self.console.print("Opção inválida! Tente novamente.", style="red")
            except Exception as e:
                self.console.print(f"Erro: {e}", style="red")

    def _perguntar_configuracoes_sessao(self) -> tuple:
        """Coleta todas as configurações da sessão usando o console (Rich)."""
        self.console.print("\n--- Configuração da Sessão ---", style="bold cyan")

        # 1. Banca (Lógica única, permanece aqui)
        while True:
            try:
                valor_str = self.console.input("[yellow]Banca hoje? R$ [/yellow]")
                valor = float(valor_str.replace(",", "."))
                if valor > 0:
                    banca_inicial = valor
                    break
                else:
                    self.console.print("Digite um valor maior que zero!", style="red")
            except Exception:
                self.console.print("Valor inválido! Tente novamente.", style="red")

        # 2. Meta (Agora usa o helper)
        meta_pct = self._apresentar_menu_e_obter_escolha(
            titulo="Defina a META DE LUCRO para a sessão:",
            menu_texto="  1. 10%\n  2. 20%\n  3. 40%\n  4. 50%\n  5. 100%",
            opcoes_dict={"1": 10.0, "2": 20.0, "3": 40.0, "4": 50.0, "5": 100.0},
            prompt_input="Escolha (1-5): ",
            log_prefix="Meta de lucro definida",
        )

        # 3. Suspensão (Agora usa o helper)
        tempo_suspensao = self._apresentar_menu_e_obter_escolha(
            titulo="Defina o TEMPO DE SUSPENSÃO (após meta):",
            menu_texto="  1. 04 Horas\n  2. 06 Horas\n  3. 08 Horas\n  4. 12 Horas",
            opcoes_dict={"1": 4, "2": 6, "3": 8, "4": 12},
            prompt_input="Escolha (1-4): ",
            log_prefix="Tempo de suspensão definido",
        )

        # 4. Modo Ciclo (Agora usa o helper)
        modo_ciclo = self._apresentar_menu_e_obter_escolha(
            titulo="Defina o MODO DE CICLO (após suspensão):",
            menu_texto="  1. Reinvestir (usar saldo atual como nova banca)\n  2. Preservar (voltar à banca inicial original)",
            opcoes_dict={"1": "reinvestir", "2": "preservar"},
            prompt_input="Escolha (1-2): ",
            log_prefix="Modo de Ciclo definido",
        )

        return banca_inicial, meta_pct, tempo_suspensao, modo_ciclo

    def _apresentar_menu_e_obter_escolha(
        self,
        titulo: str,
        menu_texto: str,
        opcoes_dict: Dict[str, Any],
        prompt_input: str,
        log_prefix: str,
    ) -> Any:
        """
        Função auxiliar genérica para imprimir um menu e obter uma escolha.
        Chama o helper _obter_escolha_valida para o loop de input.
        """
        self.console.print(f"\n[yellow]{titulo}[/yellow]")
        self.console.print(menu_texto)

        return self._obter_escolha_valida(
            prompt=prompt_input,
            opcoes=opcoes_dict,
        )
        # Nota: O log_message_prefix foi removido de _obter_escolha_valida

    def load_config(self) -> Dict:
        """Carrega configuração"""
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

        # Guard Clause: Não envia se a sessão falhou na validação
        if not self.running and not self.db_manager.session_id:
            return

        # Assumindo que a API_URL está definida em self (ou importada)
        endpoint = f"{API_URL}/telemetria/log"
        payload = {
            # Você precisa definir get_hwid() no seu módulo security.py e importá-lo
            "hwid": get_hwid(),
            "sessao_id": self.db_manager.session_id,
            "tipo": tipo,
            "dados": dados,
            "lucro": lucro,
        }

        # Envia a requisição de forma não-bloqueante (em uma thread separada)
        try:
            threading.Thread(
                target=requests.post,
                args=(endpoint,),
                kwargs={"json": payload, "timeout": 5},
            ).start()
        except Exception as e:
            self.logger.warning(f"Falha ao enviar telemetria: {e}")

    def select_profile(self):
        """Seleção de perfil (Interface com 'rich')"""
        profiles = self.config.get("profiles", {})

        self.console.print("\nPerfis disponíveis:", style="cyan")

        # Opção Especial de Calibração
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

                # SE O USUÁRIO ESCOLHER 0 -> CHAMA O WIZARD
                if choice == 0:
                    name, data = self.run_calibration_wizard()
                    if name and data:
                        # Se calibrou com sucesso, já retorna o novo perfil para uso imediato
                        return name, data
                    else:
                        # Se falhou ou cancelou, pede de novo
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
        """Configura áreas da tela baseado no perfil selecionado"""
        if not self.config:
            self.console.print("❌ Config não carregado!", style="red")
            return ""

        profiles = self.config.get("profiles", {})
        if not profiles:
            self.console.print("❌ Nenhum perfil encontrado no config!", style="red")
            return ""

        profile_name, profile_data = self.select_profile()

        # Carregar configurações do perfil
        self.players = self.config.get("jogadores", [])
        self.max_time = self.config.get("tempo_horas", 8) * 3600
        self.max_rounds = self.config.get("max_rodadas", 1000)
        self.target_profit = self.config.get("meta_lucro_total", 1000)
        self.start_hour = self.config.get("horario_inicio", 9)

        # Mapear áreas
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

        # Verificar áreas críticas
        critical_areas = ["balance", "multiplier", "bet_detection"]
        if missing_areas := [
            area for area in critical_areas if not self.screen_areas.get(area)
        ]:
            self.console.print(
                f"⚠️ Áreas não configuradas: {missing_areas}", style="yellow"
            )

        # (Lógica de verificação de apostas mantida)
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
        # --- ETAPA 4: Usando variável de config ---
        check_interval = self.balance_check_interval

        while self.running:
            try:
                if time.time() - last_check < check_interval:
                    time.sleep(0.2)
                    continue

                balance_area = self.screen_areas.get("balance")

                if not balance_area:
                    continue

                # --- ETAPA 1: Trava de Leitura (para get_balance) ---
                with self.balance_lock:
                    current_balance_snapshot = self.current_balance

                new_balance = self.vision.get_balance(
                    balance_area, current_balance_snapshot
                )

                if new_balance and new_balance != current_balance_snapshot:

                    if validated_balance := self._validate_and_confirm_balance_change(
                        new_balance, current_balance_snapshot
                    ):
                        # --- ETAPA 1: Trava de Escrita ---
                        with self.balance_lock:
                            old_balance = self.current_balance or 0.0
                            self.current_balance = validated_balance
                            # LEIA o saldo inicial aqui, de forma segura
                            initial_balance_snapshot = self.initial_balance
                        # --- Fim da Trava ---

                        self.balance_history.append(validated_balance)
                        change = validated_balance - old_balance
                        self.last_action = f"💰 Saldo: R${validated_balance:.2f} ([green]{change:+.2f}[/green])"

                        # --- INÍCIO DA MODIFICAÇÃO (ALERTA DE STOP-LOSS) ---
                        # Só checa se o saldo inicial já foi definido
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
        """Valida uma mudança drástica de saldo, re-capturando se necessário."""
        if not current_balance or current_balance == 0:
            return new_balance

        change_percent = (abs(new_balance - current_balance) / current_balance) * 100
        # --- ETAPA 4: Usando variável de config ---
        if change_percent <= self.balance_change_threshold_pct:
            return new_balance

        # Se a mudança for drástica, re-capture para confirmar
        self.console.print(
            f"⚠️  Mudança drástica de saldo detectada ({change_percent:.1f}%). Confirmando...",
            style="yellow",
        )
        time.sleep(1)

        # --- CORREÇÃO DE TIPAGEM (PYLANCE) ---
        balance_area = self.screen_areas.get("balance")
        if not balance_area:
            return None  # Impossível confirmar sem área configurada
        # -------------------------------------

        # --- ETAPA 1: Trava de Leitura (para get_balance) ---
        with self.balance_lock:
            current_balance_snapshot = self.current_balance

        # Passamos a variável validada 'balance_area'
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
        """
        Verifica a condição de stop-loss e dispara o alerta se necessário.
        (Extraído de detect_balance_continuously)
        """

        # A condição de guarda (stop_loss_alerted) é a primeira
        if self.stop_loss_alerted:
            return

        # A condição de saldo
        if initial_balance > 0 and current_balance < (  # Garante que o inicial é válido
            initial_balance * (1 - self.stop_loss_threshold_pct)
        ):
            # (MODIFICAÇÃO DE ALERTA (STOP-LOSS))
            loss_pct = (1 - (current_balance / initial_balance)) * 100
            msg = (
                f"🚨 *ALERTA DE STOP-LOSS!* 🚨\n"
                f"Banca caiu abaixo de {self.stop_loss_threshold_pct:.0%} do inicial.\n\n"
                f"Início: R$ {initial_balance:.2f}\n"
                f"Atual: R$ {current_balance:.2f}\n"
                f"Perda: -{loss_pct:.1f}%"
            )
            # (Usando 'trigger_alert' como renomeamos o método)
            self.trigger_alert("stop_loss", msg)
            self.stop_loss_alerted = True  # Trava o alarme

    def capture_multipliers_continuously(self):
        """Thread para capturar multiplicadores continuamente"""
        while self.running:
            try:
                # 1. Capturar a área em uma variável local
                multiplier_area = self.screen_areas.get("multiplier")

                # 2. Verificar se a variável é válida (Não é None)
                if multiplier_area:
                    # 3. Passar a variável validada para a função de visão
                    multiplier = self.vision.get_multiplier(multiplier_area)

                    if multiplier and 1.0 <= multiplier <= 999.99:
                        frame_data = {"timestamp": time.time(), "value": multiplier}

                        with self.buffer_lock:
                            self.frame_buffer.append(frame_data)

                # --- ETAPA 4: Usando variável de config ---
                time.sleep(self.frame_interval)

            except Exception as e:
                self.logger.error(f"Erro na captura: {e}")
                time.sleep(0.1)

    def detect_bet_and_process(self):
        """Thread principal de detecção e processamento"""
        last_explosion_time = 0
        # --- ETAPA 4: Usando variável de config ---
        cooldown = self.cooldown_seconds

        while self.running:
            try:
                current_time = time.time()

                if current_time - last_explosion_time < cooldown:
                    time.sleep(0.1)
                    continue

                # --- CORREÇÃO DE TIPAGEM PYLANCE ---
                bet_area = self.screen_areas.get("bet_detection")

                if not bet_area:
                    # Se a área não estiver configurada, não faz nada
                    time.sleep(1)
                    continue
                # -----------------------------------

                # Agora passamos 'bet_area' validada
                if self.vision.detect_bet_text(bet_area):

                    # (Removido o 'if bet_detected' redundante)
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
                        # Processar explosão
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

    # --- ETAPA 2: LÓGICA CENTRAL REESCRITA ---
    def process_explosion(self, explosion_value: float, timestamp: float):
        """
        Processa uma explosão detectada. (VERSÃO REATORADA)
        Orquestra o processamento da rodada, verificação de estado e preparação da próxima aposta.
        """
        try:
            # 1. Atualizar estado interno e UI
            self.explosions.append(
                {"value": explosion_value, "timestamp": datetime.now()}
            )
            self.round_count += 1
            self.last_action = f"💥 EXPLOSÃO: {explosion_value:.2f}x"

            self._send_telemetry(
                tipo="round", dados=f"Explosao: {explosion_value:.2f}x", lucro=0.0
            )

            # 2. Obter saldo ATUAL (com segurança)
            with self.balance_lock:
                current_balance = self.current_balance or 0.0

            # 3. Processar resultado da aposta ANTERIOR (se houver)
            self._handle_previous_bet_result(explosion_value)

            # 4. Salvar a rodada ATUAL no DB
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

            # 5. Verificar estado (Meta/Suspensão).
            # Se retornar False, o bot para de processar esta rodada.
            if not self._check_game_state_for_next_round(current_balance):
                return  # Bot está suspenso ou atingiu a meta

            # 6. Processar estratégia da rodada atual e preparar próxima aposta
            self._prepare_next_round_bet(current_balance, explosion_value)

        except Exception as e:
            self.logger.error(f"Erro ao processar explosão: {e}")
            self.last_action = f"❌ Erro ao processar explosão: {e}"

    def _check_game_state_for_next_round(self, current_balance: float) -> bool:
        """
        (Helper) Verifica se o bot está suspenso ou atingiu a meta.
        Envia alertas se o estado mudar.
        Retorna True para "Continuar", False para "Parar".
        """
        # 1. VERIFICAR A SUSPENSÃO (A CADA RODADA)
        if self.strategy.esta_suspenso():
            self.last_action += " | [yellow]SUSPENSO (Meta Atingida)[/yellow]"

            # VERIFICAR SE A SUSPENSÃO ACABOU (e enviar alerta de retorno)
            if self.strategy.check_suspension_ended(current_balance):
                msg = (
                    "✅ *OPERAÇÕES RETOMADAS!*\nPeríodo de suspensão (meta) terminado."
                )
                self.trigger_alert("resume", msg)

            return False  # Parar processamento

        # 2. VERIFICAR A META (SÓ SE NÃO ESTIVER SUSPENSO)
        elif self._check_profit_target_reached(current_balance):
            return False  # Parar processamento (o helper já enviou o alerta)

        # 3. OK PARA CONTINUAR
        else:
            return True  # OK para continuar

    def _check_profit_target_reached(self, current_balance: float) -> bool:
        """
        (Helper) Verifica se a meta de lucro foi atingida e suspende o bot.
        Retorna True se o bot DEVE PARAR (meta atingida), False caso contrário.
        """
        # 6. VERIFICAR A META (A CADA RODADA)
        if self.strategy.checar_meta_lucro(current_balance):

            # --- INÍCIO DA CORREÇÃO (Resolve o erro do Pylance) ---
            # Verifica se os valores de estratégia existem antes de usá-los
            if (
                self.strategy.tempo_suspensao_horas is None
                or self.strategy.banca_inicial is None
                or self.strategy.meta_lucro_percentual is None
            ):
                self.logger.error(
                    "Falha ao suspender: Dados da estratégia (banca/meta) são None."
                )
                return True  # Parar processamento

            horas_suspensao = self.strategy.tempo_suspensao_horas
            meta_valor_abs = self.strategy.banca_inicial * (
                1 + self.strategy.meta_lucro_percentual
            )
            # --- FIM DA CORREÇÃO ---

            self.last_action += " | [green]META ATINGIDA! (Suspendendo)[/green]"

            # NOVA NOTIFICAÇÃO (INÍCIO DA SUSPENSÃO)
            msg = (
                f"🏆 *META DE LUCRO ATINGIDA!* 🏆\n"
                f"Meta: R$ {meta_valor_abs:.2f}\n"
                f"Saldo Atual: R$ {current_balance:.2f}\n"
                f"Operações suspensas por {horas_suspensao} horas."
            )
            self.trigger_alert("suspend", msg)
            return True  # Parar processamento (Meta Atingida)

        return False  # OK para continuar (Meta Não Atingida)

    def _prepare_next_round_bet(self, current_balance: float, explosion_value: float):
        """
        (Helper) Processa a estratégia da rodada atual e prepara a próxima aposta.
        """
        # 7. Processar a explosão ATUAL no StrategyEngine
        strategy_activated, _, veto_message = self.strategy.add_explosion_value(
            explosion_value
        )
        if veto_message:
            self.last_action += f" | [yellow]{veto_message}[/yellow]"

        # 8. Preparar a PRÓXIMA aposta
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
        """
        Processa o resultado da aposta pendente da rodada anterior.
        Extraído de process_explosion (sugestão Sourcery).
        """
        if not self.executed_bet_pending:
            return  # Nada a fazer

        try:
            self._process_bet_evaluation(explosion_value, self.executed_bet_pending)

        except Exception as e:
            self.logger.error(f"Erro ao processar resultado da aposta anterior: {e}")
            self.last_action += " | ❌ Erro aposta ant."
        finally:
            # Garante que a aposta pendente seja limpa, mesmo em caso de erro
            self.executed_bet_pending = None

    def _process_bet_evaluation(self, explosion_value: float, executed_bet: dict):
        """(Helper) Avalia, alerta e salva o resultado da aposta."""

        # Pega o saldo atualizado
        with self.balance_lock:
            current_balance = self.current_balance or 0.0

        # Avalia o resultado
        result = self.strategy.evaluate_executed_bet(explosion_value, executed_bet)

        strategy_name = result.get("strategy", "Estratégia")

        # Formata a mensagem base
        base_msg = f"Alvo: {result['target_1']}x | Explodiu: {explosion_value}x\n*Saldo Atual: R$ {current_balance:.2f}*"

        if result["recommendation_hit"]:
            hit_status = "[green]✅ HIT[/green]"
            msg_meta = ""  # Mensagem de meta vazia por padrão
            try:
                # O strategy engine (self.strategy) guarda os valores da meta
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

        # Salvar aposta EXECUTADA no DB
        if self.last_round_id:
            # --- INÍCIO DA CORREÇÃO ---

            # 1. Determinar o resultado como string (usando as constantes)
            resultado_aposta_1 = (
                RESULTADO_HIT if result["recommendation_hit"] else RESULTADO_MISS
            )

            # 2. Criar o objeto BetData com todos os dados
            # (Assumindo que o 'result' do strategy_engine contém 'profit_loss')
            dados_aposta = BetData(
                rodada_id=self.last_round_id,
                estrategia=result.get("strategy", "Estratégia"),
                aposta_1=result.get("bet_1", 0.0),
                target_1=result.get("target_1", 0.0),
                aposta_2=0.0,
                target_2=0.0,
                resultado_1=resultado_aposta_1,
                resultado_2=RESULTADO_MISS,  # Não aplicável, marcamos como miss
                lucro_liquido=result.get(
                    "profit_loss", 0.0
                ),  # Mapeia 'profit_loss' para 'lucro_liquido'
                timestamp=datetime.now().isoformat(),
            )

            # 3. Passar o objeto ÚNICO para a função save_bet
            self.db_manager.save_bet(dados_aposta)

            self._send_telemetry(
                tipo="bet",
                dados=f"Resultado: {resultado_aposta_1}",
                lucro=dados_aposta.lucro_liquido,
            )

    def can_execute_bets(self) -> bool:
        """Verifica apenas áreas do BET 1"""
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

        # self.console.print("✅ Áreas do BET 1 configuradas - Pode apostar!", style="green")
        return True

    # --- ETAPA 2: LÓGICA DE APOSTA ATUALIZADA ---
    def execute_prepared_bets(self):
        """Executa apenas BET 1, lendo do novo StrategyEngine."""
        try:
            # Pega a recomendação (BetRecommendation) do motor
            recommendation = self.strategy.get_prepared_bets()

            if not recommendation or not recommendation.ready:
                return

            self.last_action = f"⚡ EXECUTANDO BET 1: {recommendation.strategy_name}"

            # Log da execução
            self.console.print("DEBUG EXECUÇÃO RÁPIDA (SÓ BET 1):", style="magenta")
            self.console.print(
                f"  Aposta 1: R${recommendation.bet_1:.2f} @ {recommendation.target_1:.2f}x"
            )
            with self.balance_lock:
                self.console.print(f"  Saldo atual: R${self.current_balance:.2f}")

            if self.fill_bet_fields_and_submit(
                recommendation.bet_1, recommendation.target_1
            ):
                # Registrar aposta executada (agora como um dict)
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

                # Reset apostas preparadas no motor
                self.strategy.reset_prepared_bets()
            else:
                self.last_action = "❌ Falha ao executar BET 1"

        except Exception as e:
            self.logger.error(f"Erro ao executar apostas: {e}")
            self.last_action = f"❌ Erro ao executar apostas: {e}"

    # --- MÉTODOS DE AUTOMAÇÃO (PRESERVADOS) ---

    def trigger_alert(self, alert_type: str, message: Optional[str] = None):
        """Dispara um alerta sonoro (local) e uma notificação (Telegram)."""

        # 1. Tocar Som (Local)
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

        # 2. Enviar Notificação (Telegram) - (Não-bloqueante)
        if message:
            notification_manager.send_telegram_alert(message)

    def fill_bet_fields_and_submit(self, bet_value_1: float, target_1: float) -> bool:
        try:
            bet_value_1 = max(1.0, (bet_value_1))
            bet_value_1_str = f"{bet_value_1:.2f}"
            target_1_str = f"{target_1:.2f}"

            # --- CORREÇÃO DE TIPAGEM (PYLANCE) ---
            # 1. Capturamos as áreas em variáveis locais
            area_value = self.screen_areas.get("bet_value_1")
            area_target = self.screen_areas.get("target_1")
            area_button = self.screen_areas.get("bet_button_1")

            # 2. Verificamos se todas existem antes de tentar clicar
            if not area_value or not area_target or not area_button:
                self.console.print("❌ Erro: Áreas de aposta incompletas.", style="red")
                return False
            # -------------------------------------

            self.console.print("1/3 Preenchendo valor BET 1...", style="yellow")
            # Passamos a variável validada 'area_value'
            if not self.click_and_fill_field(
                area_value, bet_value_1_str, "valor aposta 1"
            ):
                return False
            time.sleep(random.uniform(0.1, 0.2))

            self.console.print("2/3 Preenchendo target BET 1...", style="yellow")
            # Passamos a variável validada 'area_target'
            if not self.click_and_fill_field(
                area_target, target_1_str, "alvo aposta 1"
            ):
                return False
            time.sleep(random.uniform(0.1, 0.2))

            self.console.print("3/3 Clicando botão BET 1...", style="yellow")
            # Passamos a variável validada 'area_button'
            if not self.click_area(area_button, "botão apostar 1"):
                return False

            self.console.print("✅ BET 1 EXECUTADO! BET 2 IGNORADO!", style="green")

            time.sleep(1.0)
            self.return_focus_to_bot()
            return True

        except Exception as e:
            self.logger.error(f"Erro ao executar BET 1: {e}")
            return False

    def click_and_fill_field(self, area: Dict, value: str, description: str) -> bool:
        """Clica em campo e preenche valor (lógica preservada)"""
        try:
            if not area:
                self.console.print(
                    f"❌ Área {description} não configurada!", style="red"
                )
                return False
            x, y = area["x"] + area["width"] // 2, area["y"] + area["height"] // 2
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
        """Clica em uma área (lógica preservada)"""
        try:
            if not area:
                self.console.print(
                    f"❌ Área {description} não configurada!", style="red"
                )
                return False
            center_x, center_y = (
                area["x"] + area["width"] // 2,
                area["y"] + area["height"] // 2,
            )
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
        """Move mouse de forma humana (lógica preservada)"""
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
        """Retorna foco para o bot (lógica preservada)"""
        try:
            pyautogui.keyDown("alt")
            time.sleep(0.1)
            pyautogui.press("tab")
            time.sleep(0.1)
            pyautogui.keyUp("alt")
        except Exception as e:
            self.logger.error(f"Erro ao retornar foco: {e}")

    # --- ETAPA 3: LÓGICA DE UI REESCRITA COM 'rich' ---

    def update_ui_continuously(self):
        """Thread da interface que atualiza o 'Live' display."""
        while self.running:
            try:
                if self.live_display:
                    self.live_display.update(self.build_dashboard_layout())

                current_time = time.time()
                # 1800 segundos = 30 minutos
                if current_time - self.last_balance_alert_time >= 1800:
                    self.last_balance_alert_time = current_time

                    # 1. Coletar Saldo (Seguro)
                    with self.balance_lock:
                        balance = self.current_balance

                    if not balance:  # Pula se o saldo não foi detectado
                        continue

                    # 1. Coletar Análise 250 (Usando o novo Helper)
                    stats = self._get_current_history_stats()

                    # 2. Montar a mensagem (em Markdown) - SIMPLIFICADA
                    msg = (
                        f"🔔 *Relatório Periódico (30 min)* 🔔\n\n"
                        f"*Banca Atual: R$ {balance:.2f}*\n\n"
                        # f"*Status do Mercado:*\n{status_mercado}\n\n"
                        f"*Análise {stats['total_count']} Rodadas:*\n"
                        f"- Média: {stats['mean_250']:.2f}x\n"
                        f"- Volat.: {stats['std_250']:.2f}\n"
                        f"- CV (Risco): {stats['cv_250']:.2f}\n"
                        f"- Zeros (1.00x): {stats['zeros_count']}\n"
                        f"- Max Streak (<2x): {stats['max_streak']}"
                    )

                    # 3. Enviar o alerta
                    self.trigger_alert("periodic", msg)

                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Erro na UI: {e}")
                time.sleep(1)

    def build_dashboard_layout(self) -> Layout:
        """Cria o layout principal do dashboard com 'rich'."""
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

        # Preencher o layout
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

    def _build_header_panel(self) -> Panel:
        """Constrói o painel de cabeçalho."""
        title = Text("CRASH BOT - ML (Refatorado)", style="bold cyan", justify="center")
        return Panel(title)

    def _get_profit_loss_text(
        self, current_balance: Optional[float], initial_balance: Optional[float]
    ) -> Text:
        """Calcula e formata o texto de lucro/prejuízo para a UI."""
        # --- Guard Clause: Verifica a condição de FALHA primeiro ---
        if not (
            current_balance is not None
            and initial_balance is not None
            and initial_balance > 0
        ):
            # Retorna imediatamente se a condição de falha for verdadeira
            return Text(
                "N/A", style="dim"
            )  # Código do 'else' original [cf. H:/Meu Drive/Software/Jogos/ML Avancado/src/bot_controller.py (line 722)]

        # --- Caminho Feliz: O 'else' foi removido ---
        # Este código só é executado se a Guard Clause acima NÃO retornar.
        profit = current_balance - initial_balance
        profit_pct = profit / initial_balance * 100
        profit_color = "green" if profit >= 0 else "red"
        # Cria o objeto Text formatado
        return Text(f"R$ {profit:+.2f} ({profit_pct:+.1f}%)", style=profit_color)

    def _build_db_stats_dashboard_text(self, db_stats, pnl_color: str) -> Text:
        """Cria e retorna o objeto Text formatado para o painel do DB no dashboard."""
        # --- Move assignment closer to usage ---
        text = Text()
        text.append(f"Rodadas Salvas: {db_stats.total_rounds}\n", style="white")
        text.append(f"Apostas Salvas: {db_stats.total_bets}\n", style="white")
        text.append(f"Taxa de Acerto: {db_stats.hit_rate:.1f}%\n", style="white")
        # ---> USAR A COR RECEBIDA <---
        text.append(f"P&L (DB): R$ {db_stats.profit_loss:+.2f}", style=pnl_color)
        return text

    def _build_db_stats_renderable(
        self, is_summary: bool = False
    ) -> Union[Table, Text, Panel]:
        """Busca estatísticas do DB e retorna um objeto 'rich' formatado."""
        try:
            db_stats = self.db_manager.get_session_stats()
            pnl_color = "green" if db_stats.profit_loss >= 0 else "red"

            if is_summary:  # Formato de Tabela para o Resumo Final
                return self._build_db_stats_summary_table(db_stats, pnl_color)
            else:  # Formato de Texto para o Painel do Dashboard
                return self._build_db_stats_dashboard_text(db_stats, pnl_color)

        except Exception as e:
            # Retorna um Painel de erro em caso de falha
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
        # Adicionei alguns padrões que usamos
        title_style: str = "bold cyan",
        header_style: str = "bold white",
        **kwargs,  # Permite passar outros args como expand=True
    ) -> Table:
        """
        Factory method para criar tabelas Rich com estilo padrão do bot.
        (Baseado na sugestão do Copilot - Versão 1)
        """
        return Table(
            title=title,
            border_style=border_style,
            show_header=show_header,
            title_style=title_style,
            header_style=header_style,
            **kwargs,  # Passa quaisquer argumentos extras (ex: expand)
        )

    # ... (fim da função _build_db_stats_summary_table)

    def _create_table_by_type(self, table_type: TableType) -> Table:
        """
        Cria uma tabela Rich pré-configurada (com colunas)
        baseada no TableType. (Refatoração Opção 2)
        """
        try:
            config = self._TABLE_CONFIGS[table_type]
        except KeyError:
            self.logger.error(f"Tipo de tabela desconhecido: {table_type}")
            return Table(title=f"Erro: Tabela {table_type} não encontrada")

        # Extrai 'title' e 'columns'
        title = config.get("title", "")
        columns = config.get("columns", [])

        # Pega todos os *outros* kwargs (ex: border_style, header_style)
        table_kwargs = {
            k: v for k, v in config.items() if k not in ["title", "columns"]
        }

        # Cria a tabela base usando a fábrica original
        table = self._create_styled_table(title=title, **table_kwargs)

        # Adiciona as colunas definidas na configuração
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
        """Cria e retorna a Tabela Rich formatada para o sumário do DB."""
        # Cria a tabela E suas colunas em UMA chamada
        db_table = self._create_table_by_type(TableType.DATABASE_STATS)

        # A função agora foca APENAS em adicionar as linhas
        db_table.add_row("Multiplicadores salvos", str(db_stats.total_rounds))
        db_table.add_row("Apostas executadas", str(db_stats.total_bets))
        db_table.add_row("Taxa de acerto", f"{db_stats.hit_rate:.1f}%")

        db_table.add_row(
            "P&L Total (DB)",
            Text(f"R$ {db_stats.profit_loss:+.2f}", style=pnl_color),
        )
        return db_table

    def _build_balance_panel(self) -> Panel:
        """Constrói o painel de saldo (Thread-Safe)."""
        # --- ETAPA 1: Leitura com Trava ---
        current_balance, initial_balance = self._get_safe_balances()

        if current_balance is not None:
            balance_text = Text(f"R$ {current_balance:.2f} ", style="bold white")
            # --- CHAMADA AO NOVO MÉTODO ---
            profit_text = self._get_profit_loss_text(current_balance, initial_balance)
            balance_text.append(profit_text)
            # --- FIM DA CHAMADA ---
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
        """Constrói o painel de histórico de multiplicadores com estatísticas."""
        text = Text()

        # self.explosions é uma lista de dicts
        if self.explosions:
            # Pega os últimos 250 valores
            last_250_values = [e["value"] for e in self.explosions[-250:]]

            if (
                len(last_250_values) >= 20
            ):  # Só mostra stats se tivermos um número razoável
                # --- MUDANÇA: Chama o helper 1 ---
                self._append_history_stats(text, last_250_values)

            # --- MUDANÇA: Chama o helper 2 ---
            self._append_recent_history(text)
        else:
            text.append("Aguardando explosões...", style="dim")

        return Panel(text, title="Histórico e Análise (250)")

    def _append_history_stats(self, text: Text, last_250_values: list):
        """(Helper) Calcula e anexa estatísticas avançadas ao objeto Text."""

        # --- MUDANÇA 1: Chamar o Helper (você já fez isso) ---
        stats = self._get_current_history_stats()
        # --- FIM DA MUDANÇA 1 ---

        # --- MUDANÇA 2: Usar os valores do helper ---
        # (Todos os 'np.mean', 'np.std' etc. foram REMOVIDOS daqui)
        total_count = stats["total_count"]
        mean_250 = stats["mean_250"]
        std_250 = stats["std_250"]
        cv_250 = stats["cv_250"]
        max_streak = stats["max_streak"]
        zeros_count = stats["zeros_count"]
        # --- FIM DA MUDANÇA 2 ---

        # --- MUDANÇA 3: Calcular APENAS o que for específico da UI ---
        # (O P80 e o zeros_pct só são mostrados aqui, não no Telegram)
        zeros_pct = (zeros_count / total_count) * 100 if total_count > 0 else 0.0
        p80_value = np.percentile(last_250_values, 80)
        # --- FIM DA MUDANÇA 3 ---

        # --- Define Cores para a UI (Usa as variáveis que pegamos do 'stats') ---
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

        # --- Constrói o Objeto de Texto (Esta parte já estava correta) ---
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
        text.append(f"{p80_value:.2f}x\n", style="dim")  # Percentil é só informativo

        text.append("-----------------------------\n", style="cyan")

    def _append_recent_history(self, text: Text):
        """(Helper) Anexa os 15 multiplicadores mais recentes ao objeto Text."""
        # self.explosions é uma lista de dicts
        last_15 = self.explosions[-15:]
        for e in reversed(last_15):
            color = "red" if e["value"] < 2.0 else "green"
            text.append(f"{e['value']:.2f}x\n", style=color)

    def _calculate_max_streak(self, values: list) -> int:
        """(Helper) Calcula a maior streak de baixos (< 2.0x) em uma lista."""
        max_streak = 0
        current_streak = 0
        for value in values:
            if value < 2.0:
                current_streak += 1
            else:
                max_streak = max(max_streak, current_streak)
                current_streak = 0
        return max(max_streak, current_streak)  # Checagem final

    def _get_current_history_stats(self) -> Dict[str, Union[float, int]]:
        """
        Calcula e retorna as estatísticas de análise das últimas 250 rodadas.
        Esta função é o "único ponto da verdade" para evitar duplicação.
        """
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
        """Constrói o painel de STATUS ATUAL da estratégia."""
        try:
            # Pedimos ao StrategyEngine um resumo do seu estado atual
            analysis_data = self.strategy.get_current_analysis()

            # Criamos uma tabela simples de Status (Key-Value)
            table = self._create_styled_table(
                title="",  # Sem título
                border_style="dim",
                show_header=False,
                expand=True,
            )
            table.add_column("Item", style="cyan")
            table.add_column("Status", style="white")

            # --- Adicionamos as linhas de status ---

            # 1. Status do Martingale
            status_text = (
                "[green]ATIVO[/green]"
                if analysis_data.get("martingale_active")
                else "[yellow]Aguardando[/yellow]"
            )
            table.add_row("Martingale:", status_text)

            # 2. Dobra Atual
            dobra_atual = analysis_data.get("dobra_atual", 1)
            table.add_row("Dobra Atual:", str(dobra_atual))

            # 3. Gatilho de Baixos (lendo a string "X/8")
            gatilho_baixos = analysis_data.get("baixos_consecutivos", "N/A")
            table.add_row("Gatilho (Baixos):", gatilho_baixos)

            # --- INÍCIO DA MUDANÇA (Isto está faltando no seu) ---
            # 4. Confiança do ML (lendo o float ml_confidence)
            ml_conf = analysis_data.get("ml_confidence", 0.0)

            if ml_conf == -1.0:  # Erro
                conf_text = Text("Erro", style="red")
            else:
                # Define a cor com base na confiança
                conf_color = (
                    "green"
                    if ml_conf > 0.65
                    else ("yellow" if ml_conf > 0.52 else "dim")
                )
                conf_text = Text(f"{ml_conf:.1%}", style=conf_color)

            table.add_row("Confiança ML (Hit):", conf_text)
            # --- FIM DA MUDANÇA ---

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
                title="",  # Sem título no painel
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

    # --- MÉTODOS DE INICIALIZAÇÃO E ENCERRAMENTO (ATUALIZADOS) ---

    def _print_summary_footer_info(self):
        """Imprime as informações de rodapé do resumo da sessão."""
        self.console.print(
            f"🆔 ID da Sessão: {self.db_manager.session_id}", style="dim"
        )
        self.console.print(f"📁 Database: {self.db_manager.db_path}", style="dim")

    def format_time(self, seconds: float) -> str:
        """Formata tempo em HH:MM:SS"""
        return str(timedelta(seconds=int(seconds)))

    def _print_financial_summary(self):
        """Obtém saldos e imprime a tabela de resumo financeiro."""
        current_balance, initial_balance = self._get_safe_balances()

        if current_balance is not None and initial_balance is not None:
            profit_text_obj = self._get_profit_loss_text(
                current_balance, initial_balance
            )

            # Cria a tabela E suas colunas em UMA chamada
            finance_table = self._create_table_by_type(TableType.FINANCIAL_SUMMARY)

            # A função agora foca APENAS em adicionar as linhas
            finance_table.add_row("Saldo inicial", f"R$ {initial_balance:.2f}")
            finance_table.add_row("Saldo final", f"R$ {current_balance:.2f}")
            finance_table.add_row(
                "Resultado",
                profit_text_obj,
            )
            self.console.print(finance_table)

    def detect_initial_balance(self) -> Optional[float]:
        """Detecta saldo inicial automaticamente"""
        # 1. Captura a área em uma variável local
        balance_area = self.screen_areas.get("balance")

        # 2. Valida a variável (Isso satisfaz o Pylance)
        if not balance_area:
            return None

        self.console.print("🔍 Detectando saldo inicial...", style="cyan")

        for attempt in range(8):
            # 3. Passa a variável validada 'balance_area'
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
        """Define o saldo inicial e atual (Thread-Safe)."""
        with self.balance_lock:
            self.initial_balance = balance_value
            self.current_balance = balance_value
        self.balance_history.append(balance_value)

    def _start_threads(self):
        """Inicializa e inicia todas as threads de background do bot."""
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
        """Lê a chave do arquivo local ou cria o arquivo se não existir."""
        filename = "license_key.txt"

        if not os.path.exists(filename):
            try:
                # Cria o arquivo para o usuário
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
                # CORREÇÃO: Em vez de 'pass', logamos o erro. Isso satisfaz o linter.
                self.logger.error(f"Falha ao criar arquivo de licença: {e}")

            return None

        try:
            with open(filename, "r") as f:
                key = f.read().strip()
                # Verifica se é uma chave válida ou o texto padrão
                return key if key and "COLE_SUA_CHAVE_AQUI" not in key else None
        except Exception as e:
            # CORREÇÃO: Tratamento explícito de erro
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
        """Executa a lógica principal de inicialização e o loop de espera do bot."""
        self.console.print("🚀 Iniciando Bot Controller...", style="cyan")

        # --- 1. VERIFICAÇÃO DE LICENÇA (NOVO) ---
        # Se a validação falhar (retornar False), o bot avisa e para.
        if not self._validate_license():
            self.console.print(
                "\n[bold red]SISTEMA DESLIGADO POR FALHA NA LICENÇA.[/bold red]",
                style="bold red",
            )
            time.sleep(4)  # Dá tempo de ler o erro antes de fechar
            return

        # --- 2. PAUSA VISUAL (NOVO) ---
        # Pausa de 2 segundos para você ver a mensagem verde "LICENÇA VÁLIDA"
        # antes do Dashboard cobrir a tela.
        time.sleep(2)
        # ----------------------------------------------------------

        # Detectar saldo inicial
        self._initialize_balance()

        self.running = True
        # Iniciar threads
        self._start_threads()

        # --- ETAPA 3: Iniciar o Live Display ---
        self.live_display = Live(
            self.build_dashboard_layout(),
            console=self.console,
            refresh_per_second=4,
            screen=True,  # Usar tela cheia para evitar flicker
        )
        self.live_display.start()

        self.last_action = "✅ SISTEMA INICIADO! (Conectado à Nuvem)"

        # Loop principal de espera (thread principal)
        while self.running:
            time.sleep(1)

    def start(self):
        """Inicia o bot"""
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
        """Para o bot COM FECHAMENTO DO DATABASE e UI."""
        if not self.running:
            return

        self.running = False  # 1. Sinaliza para as threads pararem
        self.console.print(
            "Encerrando... Aguardando threads finalizarem.", style="yellow"
        )

        # --- 2. Espera as threads de processamento terminarem PRIMEIRO ---
        #    (timeout=2.0) significa "espere no máximo 2 segundos por elas"
        try:
            if self.ui_thread and self.ui_thread.is_alive():
                self.ui_thread.join(timeout=1.0)
            if self.detect_thread and self.detect_thread.is_alive():
                self.detect_thread.join(timeout=2.0)  # A thread que chama save_round
            if self.balance_thread and self.balance_thread.is_alive():
                self.balance_thread.join(timeout=2.0)
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=1.0)
        except Exception as e:
            self.logger.error(f"Erro ao aguardar threads: {e}")

        # 3. Agora que as threads pararam, para a UI
        if self.live_display:
            self.live_display.stop()
            self.console.clear()  # Limpa a tela

        time.sleep(0.5)  # Pequena pausa

        # 4. AGORA é 100% seguro fechar o banco de dados
        try:
            with self.balance_lock:
                final_balance = self.current_balance
            self.db_manager.close_session(final_balance)
            self.console.print("✅ Sessão do database fechada", style="green")
        except Exception as e:
            self.console.print(
                f"❌ Erro ao fechar sessão do database: {e}", style="red"
            )

        # 5. Mostrar resumo
        self.show_summary()

    def show_summary(self):
        """Mostra resumo da sessão (UI com 'rich')"""
        self.console.clear()
        duration = datetime.now() - self.session_start

        main_panel_content = Text()
        main_panel_content.append(
            f"⏱️  Duração: {self.format_time(duration.total_seconds())}\n"
        )
        main_panel_content.append(f"💥 Total explosões: {len(self.explosions)}\n")

        if self.explosions:
            values = [e["value"] for e in self.explosions]
            main_panel_content.append(
                f"📈 Menor: {min(values):.2f}x | Maior: {max(values):.2f}x | Média: {sum(values)/len(values):.2f}x\n"
            )

        self.console.print(
            Panel(main_panel_content, title="Resumo da Sessão", border_style="cyan")
        )

        # ESTATÍSTICAS FINAIS DO DATABASE
        db_renderable = self._build_db_stats_renderable(is_summary=True)
        self.console.print(db_renderable)
        # --- FIM DA CHAMADA ---

        # Resultado financeiro
        self._print_financial_summary()

        self._print_summary_footer_info()

    # MÓDULO DE CALIBRAÇÃO
    # =========================================================================
    def run_calibration_wizard(self):
        """Guia o usuário para mapear TODAS as áreas e salva no config.json."""
        self.console.clear()
        self.console.print(
            Panel(
                "[bold yellow]MODO DE CALIBRAÇÃO (WIZARD)[/bold yellow]\n\n"
                "Vou guiar você para mapear a tela do jogo.\n"
                "Para cada item, colocaremos o mouse no [cyan]Canto Superior Esquerdo[/cyan]\n"
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

        # --- LISTA 1: ITENS ESSENCIAIS (Ajustados para a interface da imagem) ---
        items_to_calibrate = [
            # Áreas Visuais (Para o bot 'ver' o jogo)
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
            # Campos de Ação (Para o bot 'jogar')
            # AQUI ESTÁ A CLAREZA NECESSÁRIA:
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

        # --- PERGUNTA SOBRE APOSTA 2 (Opcional) ---
        self.console.print(
            "\n[yellow]Deseja calibrar também a APOSTA 2 (Double Bet)?[/yellow]"
        )
        resp = self.console.input("Digite 's' para Sim ou Enter para pular: ").lower()

        use_bet_2 = resp == "s"

        if use_bet_2:
            items_to_calibrate.extend(
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

        new_profile = {}

        # --- LOOP DE CALIBRAÇÃO ---
        for area_key, click_key, friendly_name in items_to_calibrate:
            self.console.print(f"\n📍 Mapeando: [bold cyan]{friendly_name}[/bold cyan]")

            # 1. Captura Topo-Esquerda
            self.console.print(
                "   1. Mouse no [green]CANTO SUPERIOR ESQUERDO[/green] da área."
            )
            self.console.input("      [Enter] para capturar...")
            x1, y1 = pyautogui.position()
            self.console.print(f"      -> Topo: ({x1}, {y1})", style="dim")

            # 2. Captura Base-Direita
            self.console.print(
                "   2. Mouse no [green]CANTO INFERIOR DIREITO[/green] da área."
            )
            self.console.input("      [Enter] para capturar...")
            x2, y2 = pyautogui.position()
            self.console.print(f"      -> Base: ({x2}, {y2})", style="dim")

            # 3. Processamento
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            # Salva Área
            new_profile[area_key] = {
                "x": left,
                "y": top,
                "width": width,
                "height": height,
            }

            # Salva Clique (Centro) se necessário
            if click_key:
                cx, cy = left + (width // 2), top + (height // 2)
                new_profile[click_key] = {"x": cx, "y": cy}
                self.console.print(
                    f"      -> Clique calculado: ({cx}, {cy})", style="dim"
                )

            self.console.print("✅ Salvo!", style="green")
            time.sleep(0.3)

        # Se não configurou Bet 2, preenche com None
        if not use_bet_2:
            for field in [
                "bet_value_area_2",
                "bet_value_click_2",
                "target_area_2",
                "target_click_2",
                "bet_button_area_2",
            ]:
                new_profile[field] = None

        # --- SALVAMENTO FINAL ---
        self.console.print("\n💾 Salvando configurações...", style="yellow")
        try:
            current_config = self.load_config()
            if "profiles" not in current_config:
                current_config["profiles"] = {}

            current_config["profiles"][profile_name] = new_profile

            with open(self.config_path, "w") as f:
                json.dump(current_config, f, indent=4)

            self.console.print(
                f"✅ Perfil '{profile_name}' criado com sucesso!", style="bold green"
            )
            self.console.print("O bot usará este perfil agora.", style="cyan")

            self.config = current_config
            return profile_name, new_profile

        except Exception as e:
            self.console.print(f"❌ Erro ao salvar: {e}", style="bold red")
            return None, None


def main():
    """Função principal (UI com 'rich') - COM DEBUG NO START"""
    console = Console()
    bot = None  # Inicializa bot como None
    try:
        console.clear()
        console.print(
            Panel(
                Text("CRASH BOT - ML (Refatorado)", justify="center"),
                style="cyan bold",
                padding=(1, 10),
            )
        )
        console.print()

        instructions = Text()
        instructions.append("INSTRUÇÕES:\n", style="bold yellow")
        instructions.append("- Certifique-se que o jogo está visível na tela\n")
        instructions.append("- Selecione seu perfil\n")
        instructions.append("- O saldo será detectado automaticamente\n")
        instructions.append("- Executa apenas BET 1 para velocidade máxima\n")
        instructions.append("- Todos os dados serão salvos automaticamente\n")
        instructions.append("- Pressione [bold]Ctrl+C[/bold] para parar o bot\n")

        console.print(Panel(instructions, title="Setup", border_style="green"))
        console.print()

        console.input("[green]Pressione Enter para continuar...[/green]")

        # --- Bloco de Inicialização (já testado) ---
        console.print("⏳ Inicializando BotController...", style="yellow")
        try:
            bot = BotController()
            console.print("✅ BotController inicializado com sucesso.", style="green")
        except Exception:
            console.print(
                "\n\n[bold red]❌ ERRO FATAL DURANTE A INICIALIZAÇÃO:[/bold red]"
            )
            console.print_exception(show_locals=True)  # Mostra mais detalhes
            input("Pressione Enter para sair...")
            return  # Sai se a inicialização falhar

        # --- Bloco de Execução (Onde suspeitamos do erro) ---
        console.print("🚀 Tentando iniciar o bot (bot.start())...", style="cyan")
        try:
            bot.start()  # A chamada que pode estar falhando silenciosamente
        except KeyboardInterrupt:
            # Captura Ctrl+C durante o start ou run_main_loop
            console.print(
                "\n\nBot interrompido pelo usuário durante a execução.", style="yellow"
            )
            # O 'finally' cuidará do bot.stop() se bot existir
        except Exception:
            console.print("\n\n[bold red]❌ ERRO FATAL DURANTE bot.start():[/bold red]")
            console.print_exception(
                show_locals=True
            )  # Mostra mais detalhes do erro no start
            # Tenta parar o bot se ele foi parcialmente inicializado
            if bot and bot.running:
                try:
                    bot.stop()
                except Exception:
                    console.print("[red]Erro adicional ao tentar parar o bot:[/red]")
                    console.print_exception()

    # except KeyboardInterrupt: # Movido para dentro do try de start
    #     console.print("\n\nBot interrompido pelo usuário.", style="yellow")

    except Exception:  # Captura erros GERAIS (fora do start)
        console.print("\n\n[bold red]❌ Erro inesperado GERAL:[/bold red]")
        console.print_exception()

    finally:
        console.print("\nExecutando bloco finally...", style="dim")
        # Garante que o bot.stop() seja chamado se o bot foi criado
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


# Bloco if __name__ == "__main__": permanece o mesmo
if __name__ == "__main__":
    main()
