"""
PlatformSession - Sessão independente por plataforma.

Encapsula captura WS + parser + strategy + bankroll + betting para
UMA plataforma. O MultiPlatformController gerencia múltiplas sessões.

Uso:
    config = PlatformConfig(
        platform_name="brabet", port=9222,
        game_url="https://brabet.com/crash",
        banca=500, setup=SetupModerado(),
        meta_pct=20, stop_loss_pct=100,
    )
    session = PlatformSession(config)
    session.start()  # Blocking - roda em thread separada
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from src.bot.bankroll import BankrollManager
from src.bot.betting import BettingExecutor
from src.bot.setups import BaseSetup, SetupModerado
from src.bot.strategy import StrategyEngine
from src.bot.strategy_advisor import StrategyAdvisor, get_strategy_map
from src.analysis.trend_analyzer import TrendAnalyzer
from src.notifications.telegram import (
    notify_advisor_change,
    notify_bet_placed,
    set_platform_context,
)
from src.ws.capture import CrashWSCapture
from src.ws.parsers import get_parser

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════

@dataclass
class PlatformConfig:
    """Configuração de uma plataforma."""
    platform_name: str
    port: int = 9222
    game_url: str = ""
    banca: float = 500.0
    setup: BaseSetup = field(
        default_factory=SetupModerado
    )
    meta_pct: float = 20.0
    stop_loss_pct: float = 100.0
    compound_pct: float = 0.0
    # Compat: caixa aponta pra banca
    caixa: float = 0.0
    session_hours: float = 0.0  # 0 = sem limite
    gain_action: str = "encerrar"
    gain_suspend_hours: float = 0.0
    loss_action: str = "encerrar"
    loss_suspend_hours: float = 0.0
    profile_name: str = ""      # Perfil de calibração de tela
    recording: bool = False     # Modo gravação de frames WS
    enabled: bool = True
    advisor_enabled: bool = True  # StrategyAdvisor adaptativo
    advisor_interval: int = 25    # Rounds entre cada reavaliação


# ══════════════════════════════════════════════════════════════════════
# SESSION
# ══════════════════════════════════════════════════════════════════════

class PlatformSession:
    """Sessão completa de uma plataforma (captura + strategy + betting).

    Cada PlatformSession roda em sua própria thread e é independente
    das demais. O estado pode ser lido a qualquer momento via get_state().
    """

    def __init__(self, config: PlatformConfig):
        self.config = config
        self.name = config.platform_name
        self.logger = logging.getLogger(f"session.{self.name}")

        # Parser
        self._parser = get_parser(config.platform_name)

        # Se modo gravação, ativa recording no parser
        if config.recording and hasattr(self._parser, "start_recording"):
            self._parser.start_recording(config.platform_name)

        # Captura WS (com parser injetado)
        self.capture = CrashWSCapture(
            port=config.port,
            auto_reconnect=True,
            parser=self._parser,
        )

        # Strategy
        self.strategy = StrategyEngine()

        # Bankroll
        self.bankroll = BankrollManager(
            banca=config.banca,
            meta_percent=config.meta_pct,
            stop_loss_percent=config.stop_loss_pct,
        )

        # Betting (pyautogui com mutex)
        self.betting = BettingExecutor(
            platform_name=config.platform_name,
            profile_name=config.profile_name,
        )

        # Database desativado
        self.db_manager = None

        # Strategy Advisor (adaptive brain, per-platform map)
        self.advisor = StrategyAdvisor(
            platform_name=config.platform_name,
            strategy_map=get_strategy_map(config.platform_name),
            eval_interval=config.advisor_interval,
            enabled=config.advisor_enabled,
        )

        # Trend Analyzer (intraday pattern matching)
        self.trend_analyzer = TrendAnalyzer(platform_name=config.platform_name)

        # Estado
        self.status = "idle"  # idle | connecting | running | paused | stopped | error
        self.running = False
        self._stop_requested = False
        self.paused = False
        self.last_action = ""

        # Sessão
        self.session_start: Optional[datetime] = None
        self.round_count = 0
        self.session_hits = 0
        self.session_misses = 0
        self.session_profit = 0.0

        # Saldo
        self.initial_balance: Optional[float] = None
        self.current_balance: Optional[float] = None
        self._ws_balance_initialized = False
        self._balance_lock = threading.Lock()

        # Chrome HWND para foco de janela durante betting
        self._chrome_hwnd: int = 0

        # Apostas pendentes
        self._executed_bet_pending: Optional[Dict] = None
        self._last_round_id: Optional[int] = None

        # Setup ativo
        self.active_setup = config.setup

        # Suspensão
        self._suspended_until: Optional[datetime] = None

        # Thread
        self._thread: Optional[threading.Thread] = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start_async(self):
        """Inicia a sessão em thread separada (non-blocking)."""
        # Telemetria: sessao_inicio
        try:
            from src.telemetry import get_telemetry
            get_telemetry().send_event(
                tipo="sessao_inicio",
                plataforma=self.name,
                banca_inicial=float(self.config.banca or 0),
                modo_risco=str(self.config.setup or ""),
            )
        except Exception:
            pass

        self._thread = threading.Thread(
            target=self._run, daemon=True,
            name=f"session-{self.name}",
        )
        self._thread.start()

    def start(self):
        """Inicia a sessão (blocking)."""
        self._run()

    def stop(self):
        """Para a sessão."""
        self._stop_requested = True
        self.running = False

        # Parar recording se ativo
        if hasattr(self._parser, "stop_recording"):
            self._parser.stop_recording()

        try:
            self.capture.stop()
        except Exception:
            pass

        pass  # DB desativado

        # Telemetria: sessao_fim
        try:
            from src.telemetry import get_telemetry
            with self._balance_lock:
                final_balance = self.current_balance or 0.0
            get_telemetry().send_event(
                tipo="sessao_fim",
                plataforma=self.name,
                banca_final=float(final_balance),
                lucro=float(self.session_profit),
                total_rodadas=int(self.round_count),
            )
        except Exception:
            pass

        self.status = "stopped"
        self.last_action = f"[{self.name}] Encerrado"
        self.logger.info("Sessão encerrada")

    def pause(self):
        self.paused = not self.paused
        state = "PAUSADO" if self.paused else "RETOMADO"
        self.last_action = f"[{self.name}] {state}"

    def calibrate(self) -> bool:
        """Roda wizard de calibracao para esta plataforma."""
        ok = self.betting.calibrate()
        if ok:
            self.last_action = (
                f"[{self.name}] Calibrado!"
            )
        else:
            self.last_action = (
                f"[{self.name}] "
                f"Calibracao cancelada"
            )
        return ok

    # ── Main Loop ─────────────────────────────────────────────────────

    def _run(self):
        """Loop principal: Chrome → Tab → WS → Strategy."""
        try:
            # Contexto de plataforma para notificações Telegram
            set_platform_context(self.name)

            self.status = "connecting"
            self.session_start = datetime.now()

            # FASE 1: Chrome
            if not self._phase_chrome():
                return

            # Capturar HWND imediatamente após Chrome abrir
            # (necessário para posicionamento de janelas antes da fase 2)
            self._capture_hwnd()

            # FASE 2: Game tab
            if not self._phase_game_tab():
                return
            # FASE 3: WebSocket
            if not self._phase_connect():
                return

            # Inicializar strategy com banca do config
            # Caixa será auto-detectado no primeiro balance_update WS
            banca = self.config.banca
            with self._balance_lock:
                self.initial_balance = banca
                self.current_balance = banca

            # Aplicar setup inicial do strategy map (per-platform)
            # Sem isso, todas iniciam com config.setup
            if self.advisor.enabled:
                initial_level = self.advisor._current_level  # "normal"
                initial_config = self.advisor.strategy_map.get(initial_level)
                if initial_config:
                    initial_setup = self.advisor._get_setup(initial_config.setup_name)
                    if initial_setup:
                        initial_setup.trigger_base = initial_config.trigger
                        self.active_setup = initial_setup
                        self.logger.info(
                            f"Setup inicial: {initial_config.setup_name} "
                            f"(trigger={initial_config.trigger}, "
                            f"bet_mult={initial_config.bet_multiplier:.2f})"
                        )

            self.strategy.iniciar_sessao(banca, self.active_setup)
            # Aplicar multiplicador de aposta inicial
            if self.advisor.enabled and initial_config:
                self.strategy.bet_multiplier = initial_config.bet_multiplier
                self.advisor._current_bet_multiplier = initial_config.bet_multiplier
            self.advisor.initialize(banca, banca)
            self.running = True
            self.status = "running"
            self.last_action = f"[{self.name}] Aguardando saldo WS..."

            # Registrar callbacks e iniciar captura
            self._register_callbacks()
            self.capture.start()

            self.logger.info(f"Sessão {self.name} ativa (porta {self.config.port})")

            # Loop principal
            while self.running and not self._stop_requested:
                time.sleep(1)
                self._check_session_limits()

        except Exception as e:
            self.logger.error(f"Erro na sessão {self.name}: {e}")
            self.status = "error"
            self.last_action = f"[{self.name}] ERRO: {e}"
        finally:
            if self.running:
                self.stop()

    def _capture_hwnd(self):
        """Captura HWND do Chrome para foco de janela e posicionamento.

        Estratégia (em ordem de preferência):
        1. Se temos PID (Chrome lançado por nós) → find_hwnd_by_pid
        2. Senão (Chrome já estava aberto) → encontrar pelo user-data-dir
           na command line do processo chrome.exe
        """
        import os
        if os.name != "nt":
            return

        # Tentativa 1: PID direto (Chrome lançado por nós nesta sessão)
        chrome_pid = self.capture._chrome_pid
        if chrome_pid:
            for _ in range(10):
                hwnd = BettingExecutor.find_hwnd_by_pid(chrome_pid)
                if hwnd:
                    self._chrome_hwnd = hwnd
                    self.logger.info(
                        f"Chrome HWND (via PID {chrome_pid}): {hwnd:#x}"
                    )
                    return
                time.sleep(1)

        # Tentativa 2: Encontrar pela command line do processo
        # Cada instância usa user-data-dir com o número da porta
        port = self.config.port
        hwnd = self._find_hwnd_by_chrome_port(port)
        if hwnd:
            self._chrome_hwnd = hwnd
            self.logger.info(f"Chrome HWND (via porta {port}): {hwnd:#x}")
            return

        self.logger.warning(
            f"HWND não encontrado (PID={chrome_pid}, porta={port})"
        )

    @staticmethod
    def _find_hwnd_by_chrome_port(port: int) -> int:
        """Encontra HWND do Chrome procurando pela porta na command line.

        Usa WMI (via PowerShell) para encontrar o PID do chrome.exe que
        foi lançado com --remote-debugging-port=PORT, depois busca o HWND.
        """
        import subprocess

        try:
            # PowerShell: buscar PIDs de chrome.exe com nossa porta
            ps_cmd = (
                f"Get-CimInstance Win32_Process -Filter "
                f"\"Name='chrome.exe' AND CommandLine LIKE "
                f"'%--remote-debugging-port={port}%'\" "
                f"| Select-Object -ExpandProperty ProcessId"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=15,
            )

            pids = []
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))

            if not pids:
                return 0

            # Tentar cada PID — o principal é o que tem janela visível
            for pid in pids:
                hwnd = BettingExecutor.find_hwnd_by_pid(pid)
                if hwnd:
                    return hwnd

        except Exception as e:
            logging.getLogger(__name__).debug(
                f"_find_hwnd_by_chrome_port({port}) erro: {e}"
            )

        return 0

    def _phase_chrome(self) -> bool:
        """FASE 1: Garantir Chrome com debug port."""
        self.last_action = f"[{self.name}] Verificando Chrome (porta {self.config.port})..."
        self.logger.info(f"FASE 1: Chrome na porta {self.config.port}")

        if not self.capture._is_chrome_debug_running():
            self.last_action = f"[{self.name}] Lançando Chrome..."
            self.capture.ensure_chrome_running(self.config.game_url)

        start = time.time()
        while not self.capture._is_chrome_debug_running():
            if self._stop_requested:
                return False
            elapsed = int(time.time() - start)
            if elapsed >= 90:
                self.status = "error"
                self.last_action = f"[{self.name}] Chrome não respondeu"
                return False
            self.last_action = (
                f"[{self.name}] Aguardando Chrome... ({90 - elapsed}s)"
            )
            time.sleep(2)

        self.logger.info(f"FASE 1 OK: Chrome porta {self.config.port}")
        return True

    def _phase_game_tab(self) -> bool:
        """FASE 2: Aguardar aba do jogo."""
        self.last_action = f"[{self.name}] Buscando aba do jogo..."
        self.logger.info("FASE 2: Buscando aba do jogo")

        elapsed = 0
        while not self.capture.has_game_tab():
            if self._stop_requested:
                return False
            remaining = 180 - elapsed
            self.last_action = (
                f"[{self.name}] Abra o jogo no Chrome! ({remaining}s)"
            )
            time.sleep(3)
            elapsed += 3
            if elapsed >= 180:
                self.status = "error"
                self.last_action = f"[{self.name}] Jogo não encontrado"
                return False

        self.logger.info("FASE 2 OK: Aba do jogo encontrada")
        return True

    def _phase_connect(self) -> bool:
        """FASE 3: Conectar DevTools."""
        self.last_action = f"[{self.name}] Conectando WebSocket..."
        self.logger.info("FASE 3: Conectando DevTools")

        for attempt in range(1, 6):
            if self._stop_requested:
                return False
            self.last_action = (
                f"[{self.name}] Conectando WS... ({attempt}/5)"
            )
            if self.capture.connect():
                self.logger.info("FASE 3 OK: WebSocket conectado")
                return True
            time.sleep(3)

        self.status = "error"
        self.last_action = (
            f"[{self.name}] Falha ao conectar: {self.capture.last_error}"
        )
        return False

    # ── WS Callbacks ──────────────────────────────────────────────────

    def _register_callbacks(self):
        """Registra callbacks de eventos WS."""
        self.capture.on("round_end", self._on_round_end)
        self.capture.on("balance_update", self._on_balance_update)
        self.capture.on("betting_phase", self._on_betting_phase)
        self.capture.on("phase_change", self._on_phase_change)

    def _on_round_end(self, data: Dict):
        """Round acabou — processar crash value."""
        try:
            crash_value = data["crash"]

            self.round_count += 1
            self.last_action = f"[{self.name}] Crash: {crash_value:.2f}x"

            # Processar resultado de aposta pendente
            if self._executed_bet_pending:
                self._process_bet_result(crash_value)

            with self._balance_lock:
                balance = self.current_balance or 0.0

            # Feed advisor com round (SEMPRE, mesmo em pausa — permite reavaliar)
            self.advisor.feed_round(crash_value)

            # Trend Analyzer: feed round + periodic analysis
            self.trend_analyzer.feed_round(crash_value)
            if self.trend_analyzer.should_analyze():
                self.trend_analyzer.analyze()

            # Advisor: reavaliar a cada N rounds (SEMPRE, para poder sair de pausa)
            if self.advisor.should_evaluate():
                advisor_msg = self.advisor.evaluate(self)
                if advisor_msg:
                    self.last_action = advisor_msg
                    notify_advisor_change(advisor_msg)

            # Se pausado, nao alimentar strategy nem preparar apostas
            if self.paused:
                return

            # Strategy: alimentar + verificar trigger
            triggered, _, msg = self.strategy.add_explosion_value(crash_value)
            if msg:
                self.last_action += f" | {msg}"

            # Preparar próxima aposta
            rec = self.strategy.prepare_bets_for_balance(balance)
            if rec:
                self.last_action = (
                    f"[{self.name}] {rec.strategy_name} (aguardando apostas)"
                )

        except Exception as e:
            self.logger.error(f"Erro _on_round_end: {e}")

    def _on_balance_update(self, data: Dict):
        """Saldo atualizado via WS.

        No primeiro update, sincroniza a banca com o
        saldo real da plataforma.
        """
        try:
            new_balance = data["balance"]

            if not self._ws_balance_initialized:
                self._ws_balance_initialized = True

                self.logger.info(
                    f"Saldo detectado: "
                    f"R${new_balance:.2f}"
                )

                with self._balance_lock:
                    self.initial_balance = new_balance
                    self.current_balance = new_balance

                # Recriar bankroll com saldo real
                self.bankroll = BankrollManager(
                    banca=new_balance,
                    meta_percent=self.config.meta_pct,
                    stop_loss_percent=(
                        self.config.stop_loss_pct
                    ),
                )

                # Reinicializar advisor
                self.advisor.initialize(
                    new_balance, new_balance
                )

                self.last_action = (
                    f"[{self.name}] "
                    f"Banca: R${new_balance:.2f}"
                )
                return

            with self._balance_lock:
                old_balance = self.current_balance or 0.0
                self.current_balance = new_balance
            change = new_balance - old_balance
            self.last_action = (
                f"[{self.name}] Saldo: R${new_balance:.2f} ({change:+.2f})"
            )

            self.bankroll.sync_balance(new_balance)
            self.advisor.update_balance(new_balance)

            # Banca fixa — nao atualiza strategy

        except Exception as e:
            self.logger.error(f"Erro _on_balance_update: {e}")

    def _on_betting_phase(self, data: Dict):
        """Fase de apostas — executar aposta preparada."""
        try:
            rec = self.strategy.get_prepared_bets()
            if rec and rec.ready and not self.paused:
                if self.betting.can_execute():
                    time.sleep(0.5)
                    self._execute_prepared_bets()
                else:
                    self.last_action = (
                        f"[{self.name}] Sem calibração - não apostou"
                    )
        except Exception as e:
            self.logger.error(f"Erro _on_betting_phase: {e}")

    def _on_phase_change(self, data: Dict):
        """Fase do jogo mudou."""
        pass  # Simplificado — last_action já atualizado pelos outros callbacks

    # ── Betting ───────────────────────────────────────────────────────

    def _execute_prepared_bets(self):
        """Executa a aposta preparada via BettingExecutor."""
        try:
            rec = self.strategy.get_prepared_bets()
            if not rec or not rec.ready:
                return

            if self.betting.execute_bet(rec.bet_1, rec.target_1, self._chrome_hwnd):
                self._executed_bet_pending = {
                    "strategy": rec.strategy_name,
                    "bet_1": rec.bet_1,
                    "target_1": rec.target_1,
                }
                self.last_action = (
                    f"[{self.name}] Apostado R${rec.bet_1:.2f}@{rec.target_1:.2f}x"
                )
                # Notificar Telegram
                safety_level = self.advisor.get_state().get("safety_level", "")
                notify_bet_placed(rec.bet_1, rec.target_1, rec.strategy_name, safety_level)
                self.strategy.reset_prepared_bets()
        except Exception as e:
            self.logger.error(f"Erro executar aposta: {e}")

    def _process_bet_result(self, explosion_value: float):
        """Processa resultado de aposta executada."""
        try:
            result = self.strategy.evaluate_executed_bet(
                explosion_value, self._executed_bet_pending
            )
            bet_amount = result.get("bet_1", 0.0)
            target = result.get("target_1", 0.0)
            is_hit = result["recommendation_hit"]

            if is_hit:
                bet_profit = bet_amount * (target - 1)
                self.session_hits += 1
            else:
                bet_profit = -bet_amount
                self.session_misses += 1

            self.session_profit += bet_profit

            # Feed advisor com resultado da aposta
            self.advisor.feed_bet_result(is_hit)

            # Telemetria: aposta
            try:
                from src.telemetry import get_telemetry
                with self._balance_lock:
                    saldo = self.current_balance or 0.0
                get_telemetry().send_event(
                    tipo="aposta",
                    plataforma=self.name,
                    valor_aposta=float(bet_amount),
                    target=float(target),
                    explosao=float(explosion_value),
                    resultado="hit" if is_hit else "miss",
                    lucro=float(bet_profit),
                    saldo=float(saldo),
                    modo_risco=str(self.config.setup or ""),
                    total_rodadas=int(self.round_count),
                )
            except Exception:
                pass

        except Exception as e:
            self.logger.error(f"Erro processar resultado: {e}")
        finally:
            self._executed_bet_pending = None

    # ── Session Limits ────────────────────────────────────────────────

    def _check_session_limits(self):
        """Verifica limites: apenas tempo."""
        if self._suspended_until:
            if datetime.now() >= self._suspended_until:
                self._suspended_until = None
                self.paused = False
            return

        if (self.config.session_hours > 0
                and self.session_start):
            elapsed = (
                datetime.now() - self.session_start
            ).total_seconds()
            limit = self.config.session_hours * 3600
            if elapsed >= limit:
                self.last_action = (
                    f"[{self.name}] Tempo limite"
                )
                self.running = False

    # ── State Snapshot ────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """Retorna snapshot do estado da sessão (thread-safe)."""
        with self._balance_lock:
            balance = self.current_balance or 0.0

        analysis = {}
        try:
            analysis = self.strategy.get_current_analysis()
        except Exception:
            pass

        ws_stats = {}
        try:
            ws_stats = self.capture.get_stats()
        except Exception:
            pass

        advisor_state = {}
        try:
            advisor_state = self.advisor.get_state()
        except Exception:
            pass

        return {
            "platform": self.name,
            "status": self.status,
            "running": self.running,
            "paused": self.paused,
            "last_action": self.last_action,
            # Financial
            "caixa": self.config.banca,
            "banca": self.config.banca,
            "saldo": balance,
            "session_profit": self.session_profit,
            "session_hits": self.session_hits,
            "session_misses": self.session_misses,
            "round_count": self.round_count,
            # Strategy
            "setup_name": self.active_setup.name if self.active_setup else "N/A",
            "martingale_active": analysis.get("martingale_active", False),
            "dobra_atual": analysis.get("dobra_atual", 0),
            "max_dobras": analysis.get("max_dobras", 0),
            "baixos_consecutivos": analysis.get("baixos_consecutivos", 0),
            "next_bet_value": analysis.get("next_bet_value", 0),
            "total_sequences": analysis.get("total_sequences", 0),
            "total_wins": analysis.get("total_wins", 0),
            "total_breaks": analysis.get("total_breaks", 0),
            # WS
            "ws_connected": ws_stats.get("connected", False),
            "ws_frames": ws_stats.get("frames_received", 0),
            "ws_rounds": ws_stats.get("rounds_captured", 0),
            # History
            "explosion_history": self.capture.get_crash_history(20),
            # Config
            "port": self.config.port,
            "recording": self.config.recording,
            # Advisor
            "advisor": advisor_state,
            "trend": self.trend_analyzer.get_state(),
        }
