#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - GERENCIADOR DE ESTADO (StateManager)

Este módulo centraliza todo o estado do bot em um único lugar,
eliminando variáveis espalhadas e garantindo thread-safety.

Uso:
    from core.state import get_state, RiskMode

    state = get_state()
    state.session.running = True
    state.trading.current_balance = 1500.0
    state.trading.risk_mode = RiskMode.MODERADO
"""

from __future__ import annotations

import logging
import random
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional

# Importa apenas BotEvent (emit será importado localmente quando necessário)
from core.events import BotEvent

# Configuração do logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class RiskMode(Enum):
    """Modos de risco disponíveis."""

    CONSERVADOR = 1
    MODERADO = 2
    AGRESSIVO = 3

    @property
    def color(self) -> str:
        """Retorna a cor associada ao modo."""
        colors = {
            RiskMode.CONSERVADOR: "green",
            RiskMode.MODERADO: "yellow",
            RiskMode.AGRESSIVO: "red",
        }
        return colors.get(self, "white")

    @property
    def emoji(self) -> str:
        """Retorna o emoji associado ao modo."""
        emojis = {
            RiskMode.CONSERVADOR: "🛡️",
            RiskMode.MODERADO: "⚖️",
            RiskMode.AGRESSIVO: "⚔️",
        }
        return emojis.get(self, "🎯")


class SessionStatus(Enum):
    """Estados possíveis da sessão."""

    IDLE = "idle"  # Não iniciada
    STARTING = "starting"  # Iniciando
    VALIDATING = "validating"  # Validando licença
    CALIBRATING = "calibrating"  # Calibrando tela
    DETECTING_BALANCE = "detecting"  # Detectando saldo
    RUNNING = "running"  # Rodando
    SUSPENDED = "suspended"  # Suspensa (meta atingida)
    STOPPING = "stopping"  # Parando
    STOPPED = "stopped"  # Parada
    ERROR = "error"  # Erro


class DecisionType(Enum):
    """Tipos de decisão do bot."""

    WAITING = "waiting"  # Aguardando gatilho
    ANALYZING = "analyzing"  # Analisando
    BETTING = "betting"  # Apostando
    SKIPPED = "skipped"  # Pulou (fase arrecadatória, etc)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES DE ESTADO
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SessionState:
    """
    Estado da sessão atual.

    Controla o ciclo de vida da sessão e informações gerais.
    """

    status: SessionStatus = SessionStatus.IDLE
    session_id: str = ""
    start_time: Optional[datetime] = None
    round_count: int = 0
    last_round_id: Optional[int] = None

    # Plataforma ativa
    platform: str = "Brabet"

    # Configurações da sessão
    max_time_seconds: int = 8 * 3600  # 8 horas padrão
    max_rounds: int = 1000

    # Suspensão
    suspended_until: Optional[float] = None

    @property
    def running(self) -> bool:
        """Verifica se a sessão está rodando."""
        return self.status == SessionStatus.RUNNING

    @property
    def elapsed_seconds(self) -> float:
        """Tempo decorrido desde o início da sessão."""
        if self.start_time is None:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def elapsed_formatted(self) -> str:
        """Tempo decorrido formatado (HH:MM:SS)."""
        elapsed = int(self.elapsed_seconds)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def is_suspended(self) -> bool:
        """Verifica se está em período de suspensão."""
        if self.suspended_until is None:
            return False
        return time.time() < self.suspended_until

    @property
    def suspension_remaining_seconds(self) -> int:
        """Tempo restante de suspensão em segundos."""
        if self.suspended_until is None:
            return 0
        remaining = self.suspended_until - time.time()
        return max(0, int(remaining))


@dataclass
class TradingState:
    """
    Estado relacionado a trading/apostas.

    Controla saldos, modo de risco e apostas pendentes.
    """

    # Saldos
    initial_balance: Optional[float] = None
    current_balance: Optional[float] = None
    balance_history: List[float] = field(default_factory=list)

    # Modo de risco
    risk_mode: Optional[RiskMode] = None

    # Banca operacional (calculada com base no modo)
    operational_balance: Optional[float] = None

    # Meta e Stop Loss
    profit_target_percent: Optional[float] = None  # Ex: 0.35 = 35%
    stop_loss_percent: float = 0.50  # 50% padrão
    stop_loss_alerted: bool = False

    # Aposta pendente
    pending_bet: Optional[Dict[str, Any]] = None
    last_executed_bet: Optional[Dict[str, Any]] = None

    @property
    def profit(self) -> float:
        """Lucro/prejuízo atual."""
        if self.initial_balance is None or self.current_balance is None:
            return 0.0
        return self.current_balance - self.initial_balance

    @property
    def profit_percent(self) -> float:
        """Lucro/prejuízo em percentual."""
        if self.initial_balance is None or self.initial_balance == 0:
            return 0.0
        return (self.profit / self.initial_balance) * 100

    @property
    def profit_target_value(self) -> Optional[float]:
        """Valor absoluto da meta."""
        if self.initial_balance is None or self.profit_target_percent is None:
            return None
        return self.initial_balance * (1 + self.profit_target_percent)

    @property
    def goal_progress_percent(self) -> float:
        """Progresso em direção à meta (0-100%)."""
        if self.profit_target_value is None or self.initial_balance is None:
            return 0.0
        if self.current_balance is None:
            return 0.0

        target_profit = self.profit_target_value - self.initial_balance
        if target_profit <= 0:
            return 0.0

        return min(100.0, (self.profit / target_profit) * 100)

    @property
    def is_goal_reached(self) -> bool:
        """Verifica se a meta foi atingida."""
        if self.profit_target_value is None or self.current_balance is None:
            return False
        return self.current_balance >= self.profit_target_value

    @property
    def is_stop_loss_triggered(self) -> bool:
        """Verifica se o stop loss foi atingido."""
        if self.initial_balance is None or self.current_balance is None:
            return False
        threshold = self.initial_balance * (1 - self.stop_loss_percent)
        return self.current_balance < threshold


@dataclass
class StrategyState:
    """
    Estado da estratégia de apostas.

    Controla o martingale, gatilhos e análises.
    """

    # Martingale
    martingale_active: bool = False
    current_dobra: int = 1
    max_dobras: int = 4
    base_bet: float = 0.0
    current_bet: float = 0.0

    # Gatilho (velas baixas consecutivas)
    lows_needed: int = 8  # Quantidade de velas necessárias
    current_lows_count: int = 0
    trigger_threshold: float = 2.0  # Abaixo disso é "low"

    # ML/IA
    ml_enabled: bool = True
    ml_confidence: float = 0.0
    ml_prediction: Optional[str] = None

    # Última decisão
    last_decision_text: str = ""
    last_decision_type: DecisionType = DecisionType.WAITING
    last_decision_time: Optional[datetime] = None

    @property
    def trigger_progress(self) -> str:
        """Progresso do gatilho (ex: '5/8')."""
        return f"{self.current_lows_count}/{self.lows_needed}"

    @property
    def is_trigger_ready(self) -> bool:
        """Verifica se o gatilho está pronto para apostar."""
        return self.current_lows_count >= self.lows_needed

    def reset_trigger(self) -> None:
        """Reseta contagem do gatilho."""
        self.current_lows_count = 0

    def reset_martingale(self) -> None:
        """Reseta o martingale para dobra 1."""
        self.martingale_active = False
        self.current_dobra = 1
        self.current_bet = self.base_bet


@dataclass
class ExplosionData:
    """Dados de uma explosão individual."""

    value: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_high(self) -> bool:
        """Verifica se é uma explosão alta (>= 2.0x)."""
        return self.value >= 2.0

    @property
    def color_code(self) -> str:
        """Retorna código de cor baseado no valor."""
        if self.value >= 10.0:
            return "gold"
        elif self.value >= 2.0:
            return "green"
        else:
            return "red"


@dataclass
class HistoryState:
    """
    Estado do histórico de explosões.

    Mantém as últimas N explosões para análise.
    """

    explosions: List[ExplosionData] = field(default_factory=list)
    max_size: int = 260

    def add(self, value: float) -> None:
        """Adiciona uma explosão ao histórico."""
        self.explosions.append(ExplosionData(value=value))
        # Limita tamanho
        if len(self.explosions) > self.max_size:
            self.explosions = self.explosions[-self.max_size :]

    @property
    def values(self) -> List[float]:
        """Retorna apenas os valores das explosões."""
        return [e.value for e in self.explosions]

    @property
    def last_n(self) -> List[float]:
        """Retorna os últimos 15 valores (para exibição)."""
        return self.values[-15:]

    @property
    def count(self) -> int:
        """Quantidade de explosões no histórico."""
        return len(self.explosions)

    def clear(self) -> None:
        """Limpa o histórico."""
        self.explosions.clear()


@dataclass
class StatsState:
    """
    Estatísticas da sessão.

    Contadores e métricas de performance.
    """

    total_hits: int = 0
    total_misses: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0

    @property
    def total_bets(self) -> int:
        """Total de apostas."""
        return self.total_hits + self.total_misses

    @property
    def hit_rate(self) -> float:
        """Taxa de acerto (0-100%)."""
        if self.total_bets == 0:
            return 0.0
        return (self.total_hits / self.total_bets) * 100

    @property
    def net_profit(self) -> float:
        """Lucro líquido."""
        return self.total_profit - self.total_loss

    def record_hit(self, profit: float) -> None:
        """Registra um HIT."""
        self.total_hits += 1
        self.total_profit += profit

    def record_miss(self, loss: float) -> None:
        """Registra um MISS."""
        self.total_misses += 1
        self.total_loss += loss

    def reset(self) -> None:
        """Reseta todas as estatísticas."""
        self.total_hits = 0
        self.total_misses = 0
        self.total_profit = 0.0
        self.total_loss = 0.0


@dataclass
class UIState:
    """Estado da interface."""
    visible: bool = True
    current_tab: str = "dashboard"
    log_lines: List[str] = field(default_factory=list)


@dataclass
class ConfigState:
    """Estado de configuração."""
    tesseract_path: str = ""
    api_url: str = ""
    telemetry_enabled: bool = True
    sound_enabled: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════


class StateManager:
    """
    Gerenciador central de estado do CrashBot.

    Centraliza todo o estado em um único lugar, garantindo:
    - Thread-safety (todas operações usam locks)
    - Imutabilidade quando necessário
    - Eventos automáticos quando estado muda
    - Snapshot completo para debug/telemetria

    Exemplo:
        state = get_state()

        # Leitura
        balance = state.trading.current_balance

        # Escrita (com lock automático)
        state.set_balance(1500.0)

        # Snapshot
        data = state.get_snapshot()
    """

    def __init__(self, emit_events: bool = True):
        """
        Inicializa o gerenciador de estado.

        Args:
            emit_events: Se True, emite eventos quando estado muda
        """
        self._lock = threading.RLock()
        self._emit_events = emit_events

        # Sub-estados
        self.session = SessionState()
        self.trading = TradingState()
        self.strategy = StrategyState()
        self.history = HistoryState()
        self.stats = StatsState()

        logger.debug("StateManager inicializado")

    @contextmanager
    def lock(self) -> Generator[None, None, None]:
        """Context manager para operações atômicas."""
        with self._lock:
            yield

    def reset(self) -> None:
        """Reseta todo o estado para valores iniciais."""
        with self._lock:
            self.session = SessionState()
            self.trading = TradingState()
            self.strategy = StrategyState()
            self.history = HistoryState()
            self.stats = StatsState()

        logger.info("Estado resetado")

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS PRIVADOS
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_strategy_for_mode(self) -> None:
        """Atualiza parâmetros da estratégia baseado no modo de risco."""
        mode_config = {
            RiskMode.CONSERVADOR: {
                "banca_percent": 0.60,
                "gatilho_opcoes": [8, 9, 10],
                "meta_min": 0.20,
                "meta_max": 0.35,
            },
            RiskMode.MODERADO: {
                "banca_percent": 0.80,
                "gatilho_opcoes": [7, 8],
                "meta_min": 0.25,
                "meta_max": 0.45,
            },
            RiskMode.AGRESSIVO: {
                "banca_percent": 1.00,
                "gatilho_opcoes": [6, 7],
                "meta_min": 0.35,
                "meta_max": 0.55,
            },
        }

        # Verifica se risk_mode não é None
        current_mode = self.trading.risk_mode
        if current_mode is None:
            current_mode = RiskMode.MODERADO

        config = mode_config.get(current_mode, mode_config[RiskMode.MODERADO])

        # Sorteia gatilho
        self.strategy.lows_needed = random.choice(config["gatilho_opcoes"])

        # Sorteia meta
        self.trading.profit_target_percent = random.uniform(
            config["meta_min"], config["meta_max"]
        )

        # Calcula banca operacional
        if self.trading.current_balance:
            self.trading.operational_balance = (
                self.trading.current_balance * config["banca_percent"]
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE CONVENIÊNCIA
    # ═══════════════════════════════════════════════════════════════════════════

    def set_balance(
        self,
        new_balance: float,
        should_emit: bool = True,
    ) -> None:
        """
        Atualiza o saldo atual.

        Args:
            new_balance: Novo valor do saldo
            should_emit: Se True, emite evento BALANCE_CHANGED
        """
        with self._lock:
            old_balance = self.trading.current_balance
            self.trading.current_balance = new_balance
            self.trading.balance_history.append(new_balance)

            # Limita histórico
            if len(self.trading.balance_history) > 1000:
                self.trading.balance_history = self.trading.balance_history[-1000:]

        if should_emit and self._emit_events and old_balance != new_balance:
            from core.events import emit as emit_func

            emit_func(
                BotEvent.BALANCE_CHANGED,
                old=old_balance,
                new=new_balance,
            )

    def set_initial_balance(self, balance: float) -> None:
        """Define o saldo inicial (e atual se não definido)."""
        with self._lock:
            self.trading.initial_balance = balance
            if self.trading.current_balance is None:
                self.trading.current_balance = balance
            self.trading.balance_history.append(balance)

    def add_explosion(
        self,
        value: float,
        should_emit: bool = True,
    ) -> None:
        """
        Adiciona uma explosão ao histórico.

        Args:
            value: Valor da explosão
            should_emit: Se True, emite evento EXPLOSION_DETECTED
        """
        with self._lock:
            self.history.add(value)
            self.session.round_count += 1

            # Atualiza contagem de lows consecutivos
            if value < self.strategy.trigger_threshold:
                self.strategy.current_lows_count += 1
            else:
                self.strategy.current_lows_count = 0

        if should_emit and self._emit_events:
            from core.events import emit as emit_func

            emit_func(BotEvent.EXPLOSION_DETECTED, value=value)

    def set_decision(self, text: str, decision_type: DecisionType) -> None:
        """Atualiza a última decisão."""
        with self._lock:
            self.strategy.last_decision_text = text
            self.strategy.last_decision_type = decision_type
            self.strategy.last_decision_time = datetime.now()

    def set_risk_mode(
        self,
        mode: RiskMode,
        reinitialize: bool = True,
    ) -> None:
        """
        Define o modo de risco.

        Args:
            mode: Novo modo de risco
            reinitialize: Se True, recalcula parâmetros da estratégia
        """
        with self._lock:
            old_mode = self.trading.risk_mode
            self.trading.risk_mode = mode

            if reinitialize:
                self._update_strategy_for_mode()

        if self._emit_events:
            from core.events import emit as emit_func

            emit_func(BotEvent.MODE_CHANGED, old=old_mode, new=mode)

    # ═══════════════════════════════════════════════════════════════════════════
    # SNAPSHOT / SERIALIZAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Retorna um snapshot completo do estado atual.

        Útil para debug, logging, telemetria.

        Returns:
            Dicionário com todo o estado (serializável para JSON)
        """
        with self._lock:
            risk_mode = self.trading.risk_mode
            risk_mode_name = risk_mode.name if risk_mode else None

            return {
                "timestamp": datetime.now().isoformat(),
                "session": {
                    "status": self.session.status.value,
                    "session_id": self.session.session_id,
                    "round_count": self.session.round_count,
                    "elapsed": self.session.elapsed_formatted,
                    "is_suspended": self.session.is_suspended,
                },
                "trading": {
                    "initial_balance": self.trading.initial_balance,
                    "current_balance": self.trading.current_balance,
                    "profit": self.trading.profit,
                    "profit_percent": self.trading.profit_percent,
                    "risk_mode": risk_mode_name,
                    "goal_progress": self.trading.goal_progress_percent,
                    "is_goal_reached": self.trading.is_goal_reached,
                },
                "strategy": {
                    "martingale_active": self.strategy.martingale_active,
                    "current_dobra": self.strategy.current_dobra,
                    "trigger_progress": self.strategy.trigger_progress,
                    "ml_confidence": self.strategy.ml_confidence,
                    "last_decision": self.strategy.last_decision_text,
                    "decision_type": self.strategy.last_decision_type.value,
                },
                "stats": {
                    "hits": self.stats.total_hits,
                    "misses": self.stats.total_misses,
                    "hit_rate": self.stats.hit_rate,
                    "net_profit": self.stats.net_profit,
                },
                "history": {
                    "count": self.history.count,
                    "last_15": self.history.last_n,
                },
            }

    def __repr__(self) -> str:
        """Representação string do estado."""
        return (
            f"StateManager("
            f"status={self.session.status.value}, "
            f"balance={self.trading.current_balance}, "
            f"mode={self.trading.risk_mode}, "
            f"rounds={self.session.round_count})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_state_manager: Optional[StateManager] = None
_state_lock = threading.Lock()


def get_state() -> StateManager:
    """
    Retorna a instância singleton do StateManager.

    Thread-safe. Cria a instância na primeira chamada.

    Example:
        state = get_state()
        state.trading.current_balance = 1500.0
    """
    global _state_manager

    if _state_manager is None:
        with _state_lock:
            if _state_manager is None:
                _state_manager = StateManager()

    return _state_manager


def reset_state() -> None:
    """Reseta o StateManager global (útil para testes)."""
    global _state_manager
    with _state_lock:
        if _state_manager:
            _state_manager.reset()
        _state_manager = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO STATE MANAGER - CrashBot v3.0")
    print("=" * 60)

    # Obtém o estado global
    state = get_state()

    # Simula início de sessão
    print("\n--- Iniciando Sessão ---")
    state.session.status = SessionStatus.RUNNING
    state.session.session_id = "sess_20241220_143000"
    state.session.start_time = datetime.now()

    # Define modo e saldo
    state.set_risk_mode(RiskMode.MODERADO)
    state.set_initial_balance(1000.0)

    risk_mode = state.trading.risk_mode
    if risk_mode:
        print(f"Modo: {risk_mode.name} {risk_mode.emoji}")
    print(f"Saldo inicial: R$ {state.trading.initial_balance:.2f}")

    target = state.trading.profit_target_percent
    if target:
        print(f"Meta: {target:.1%}")
    print(f"Gatilho: {state.strategy.lows_needed} velas")

    # Simula algumas explosões
    print("\n--- Simulando Explosões ---")
    explosions = [1.23, 1.45, 3.21, 1.89, 1.12, 4.56, 1.67, 2.34]
    for exp in explosions:
        # should_emit=False para não precisar do EventBus
        state.add_explosion(exp, should_emit=False)
        emoji = "🟢" if exp >= 2.0 else "🔴"
        print(f"  {emoji} {exp:.2f}x | " f"Lows: {state.strategy.trigger_progress}")

    # Simula mudança de saldo
    print("\n--- Atualizando Saldo ---")
    state.set_balance(1150.0, should_emit=False)
    print(f"Novo saldo: R$ {state.trading.current_balance:.2f}")
    print(
        f"Lucro: R$ {state.trading.profit:.2f} "
        f"({state.trading.profit_percent:.1f}%)"
    )
    print(f"Progresso da meta: {state.trading.goal_progress_percent:.1f}%")

    # Simula apostas
    print("\n--- Simulando Stats ---")
    state.stats.record_hit(50.0)
    state.stats.record_hit(75.0)
    state.stats.record_miss(25.0)
    print(f"Hits: {state.stats.total_hits} | " f"Misses: {state.stats.total_misses}")
    print(f"Taxa de acerto: {state.stats.hit_rate:.1f}%")
    print(f"Lucro líquido: R$ {state.stats.net_profit:.2f}")

    # Snapshot
    print("\n--- Snapshot ---")
    snapshot = state.get_snapshot()
    import json

    print(json.dumps(snapshot, indent=2, default=str))

    print("\n✅ StateManager funcionando corretamente!")
