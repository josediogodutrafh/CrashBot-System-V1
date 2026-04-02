#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SISTEMA DE MARTINGALE

Gerencia progressão de apostas usando estratégia martingale.
Controla dobras, valores e limites.

Uso:
    from engine.strategy.martingale import MartingaleSystem, get_martingale

    mg = get_martingale()
    mg.configure(base_bet=10.0, max_dobra=4)

    # Obtém valor da aposta atual
    bet = mg.get_current_bet()

    # Registra resultado
    mg.record_win()   # Reseta para dobra 1
    mg.record_loss()  # Avança para próxima dobra
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.constants import (
    MARTINGALE_BANCA_DIVISOR,
    MARTINGALE_MAX_DOBRA,
    MARTINGALE_MULTIPLIERS,
)

# Core imports
from core.events import BotEvent, emit, get_event_bus
from core.state import RiskMode, get_state

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class MartingaleState(Enum):
    """Estados do martingale."""

    IDLE = "idle"  # Aguardando primeira aposta
    ACTIVE = "active"  # Ciclo ativo
    MAX_REACHED = "max_reached"  # Atingiu dobra máxima
    RECOVERING = "recovering"  # Em recuperação após loss


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MartingaleConfig:
    """Configuração do martingale."""

    base_bet: float = 10.0  # Aposta base (dobra 1)
    max_dobra: int = 4  # Máximo de dobras
    multipliers: Dict[int, int] = field(
        default_factory=lambda: {1: 1, 2: 2, 3: 4, 4: 8}
    )
    banca_divisor: int = 15  # Banca operacional / divisor = base_bet


@dataclass
class BetInfo:
    """Informações da aposta atual."""

    amount: float  # Valor a apostar
    dobra: int  # Nível da dobra (1-4)
    is_recovery: bool  # Se está em recuperação
    potential_profit: float  # Lucro potencial se ganhar
    risk_total: float  # Total em risco no ciclo


@dataclass
class MartingaleCycle:
    """Registro de um ciclo completo de martingale."""

    start_time: datetime
    end_time: Optional[datetime] = None
    bets: List[Dict[str, Any]] = field(default_factory=list)
    final_result: Optional[str] = None  # "win" ou "loss"
    total_invested: float = 0.0
    total_return: float = 0.0

    @property
    def profit(self) -> float:
        """Lucro/prejuízo do ciclo."""
        return self.total_return - self.total_invested

    @property
    def num_bets(self) -> int:
        """Número de apostas no ciclo."""
        return len(self.bets)


# ═══════════════════════════════════════════════════════════════════════════════
# MARTINGALE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════


class MartingaleSystem:
    """
    Sistema de gestão de apostas com martingale.

    Controla a progressão de apostas:
    - Dobra 1: Aposta base (ex: R$ 10)
    - Dobra 2: 2x base (ex: R$ 20)
    - Dobra 3: 4x base (ex: R$ 40)
    - Dobra 4: 8x base (ex: R$ 80)

    Após WIN: Reseta para dobra 1
    Após LOSS: Avança para próxima dobra

    Features:
        - Configurável por banca operacional
        - Limite de dobras
        - Histórico de ciclos
        - Integração com EventBus

    Exemplo:
        mg = MartingaleSystem()
        mg.configure_from_balance(1000.0)  # Calcula base_bet automaticamente

        # Loop de apostas
        bet = mg.get_current_bet()
        print(f"Apostar R$ {bet.amount:.2f} (Dobra {bet.dobra})")

        # Após resultado
        if ganhou:
            mg.record_win(profit=8.50)
        else:
            mg.record_loss()
    """

    def __init__(self, emit_events: bool = True):
        """
        Inicializa o sistema de martingale.

        Args:
            emit_events: Se True, emite eventos no EventBus
        """
        self._lock = threading.Lock()
        self._emit_events = emit_events

        # Configuração
        self._config = MartingaleConfig()

        # Estado atual
        self._state = MartingaleState.IDLE
        self._current_dobra = 1
        self._cycle_invested = 0.0  # Total investido no ciclo atual

        # Histórico
        self._current_cycle: Optional[MartingaleCycle] = None
        self._completed_cycles: List[MartingaleCycle] = []
        self._max_cycles_history = 100

        # Estatísticas
        self._total_wins = 0
        self._total_losses = 0
        self._consecutive_losses = 0
        self._max_consecutive_losses = 0

        logger.debug("MartingaleSystem inicializado")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def configure(
        self,
        base_bet: Optional[float] = None,
        max_dobra: Optional[int] = None,
    ) -> None:
        """
        Configura os parâmetros do martingale.

        Args:
            base_bet: Valor da aposta base
            max_dobra: Máximo de dobras permitidas
        """
        with self._lock:
            if base_bet is not None:
                self._config.base_bet = max(0.01, base_bet)
            if max_dobra is not None:
                self._config.max_dobra = max(1, min(10, max_dobra))

        logger.info(
            f"Martingale configurado: base_bet={self._config.base_bet:.2f}, "
            f"max_dobra={self._config.max_dobra}"
        )

    def configure_from_balance(
        self,
        operational_balance: float,
        divisor: Optional[int] = None,
    ) -> float:
        """
        Configura aposta base a partir da banca operacional.

        Args:
            operational_balance: Banca operacional
            divisor: Divisor para calcular base (default: 15)

        Returns:
            Valor da aposta base calculada
        """
        div = divisor or self._config.banca_divisor
        base_bet = operational_balance / div

        # Arredonda para 2 casas decimais
        base_bet = round(base_bet, 2)

        # Mínimo de R$ 1.00
        base_bet = max(1.0, base_bet)

        self.configure(base_bet=base_bet)

        logger.info(
            f"Base bet calculada: R$ {base_bet:.2f} (banca: R$ {operational_balance:.2f})"
        )
        return base_bet

    # ═══════════════════════════════════════════════════════════════════════════
    # APOSTAS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_current_bet(self) -> BetInfo:
        """
        Retorna informações da aposta atual.

        Returns:
            BetInfo com valor, dobra e informações adicionais
        """
        with self._lock:
            multiplier = self._config.multipliers.get(self._current_dobra, 1)
            amount = self._config.base_bet * multiplier

            # Calcula lucro potencial (considerando target ~1.85x)
            target = 1.85
            potential_profit = amount * (target - 1)

            # Total em risco no ciclo
            risk_total = self._cycle_invested + amount

            return BetInfo(
                amount=round(amount, 2),
                dobra=self._current_dobra,
                is_recovery=self._current_dobra > 1,
                potential_profit=round(potential_profit, 2),
                risk_total=round(risk_total, 2),
            )

    def get_bet_amount(self) -> float:
        """Atalho: retorna apenas o valor da aposta."""
        return self.get_current_bet().amount

    def record_win(self, profit: float = 0.0) -> None:
        """
        Registra uma aposta vencedora.

        Args:
            profit: Lucro obtido
        """
        with self._lock:
            old_dobra = self._current_dobra

            # Registra no ciclo
            if self._current_cycle:
                self._current_cycle.bets.append(
                    {
                        "dobra": old_dobra,
                        "result": "win",
                        "profit": profit,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                self._current_cycle.total_return += profit + self.get_bet_amount()
                self._current_cycle.end_time = datetime.now()
                self._current_cycle.final_result = "win"

                # Arquiva ciclo
                self._completed_cycles.append(self._current_cycle)
                if len(self._completed_cycles) > self._max_cycles_history:
                    self._completed_cycles = self._completed_cycles[
                        -self._max_cycles_history :
                    ]

            # Reseta
            self._current_dobra = 1
            self._cycle_invested = 0.0
            self._state = MartingaleState.IDLE
            self._current_cycle = None

            # Estatísticas
            self._total_wins += 1
            self._consecutive_losses = 0

        if self._emit_events:
            emit(
                BotEvent.MARTINGALE_RESET,
                {
                    "reason": "win",
                    "old_dobra": old_dobra,
                    "profit": profit,
                },
            )

        logger.info(f"WIN registrado! Dobra resetada: {old_dobra} → 1")

    def record_loss(self, loss: float = 0.0) -> bool:
        """
        Registra uma aposta perdedora.

        Args:
            loss: Valor perdido

        Returns:
            True se ainda há dobras disponíveis, False se atingiu máximo
        """
        with self._lock:
            old_dobra = self._current_dobra
            bet_amount = self.get_bet_amount()

            # Inicia ciclo se necessário
            if self._current_cycle is None:
                self._current_cycle = MartingaleCycle(start_time=datetime.now())

            # Registra no ciclo
            self._current_cycle.bets.append(
                {
                    "dobra": old_dobra,
                    "result": "loss",
                    "loss": loss or bet_amount,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self._current_cycle.total_invested += bet_amount
            self._cycle_invested += bet_amount

            # Estatísticas
            self._total_losses += 1
            self._consecutive_losses += 1
            self._max_consecutive_losses = max(
                self._max_consecutive_losses, self._consecutive_losses
            )

            # Avança dobra
            if self._current_dobra < self._config.max_dobra:
                self._current_dobra += 1
                self._state = MartingaleState.ACTIVE

                if self._emit_events:
                    emit(
                        BotEvent.MARTINGALE_DOBRA_UP,
                        {
                            "old_dobra": old_dobra,
                            "new_dobra": self._current_dobra,
                            "cycle_invested": self._cycle_invested,
                        },
                    )

                logger.info(
                    f"LOSS registrado. Dobra: {old_dobra} → {self._current_dobra}"
                )
                return True

            else:
                # Atingiu máximo
                self._state = MartingaleState.MAX_REACHED

                # Finaliza ciclo como loss
                self._current_cycle.end_time = datetime.now()
                self._current_cycle.final_result = "loss"
                self._completed_cycles.append(self._current_cycle)

                if self._emit_events:
                    emit(
                        BotEvent.MARTINGALE_MAX_REACHED,
                        {
                            "dobra": self._current_dobra,
                            "total_loss": self._cycle_invested,
                        },
                    )

                logger.warning(
                    f"LOSS registrado. DOBRA MÁXIMA ATINGIDA! ({self._current_dobra})"
                )

                # Reseta para próximo ciclo
                self._current_dobra = 1
                self._cycle_invested = 0.0
                self._current_cycle = None

                return False

    def force_reset(self) -> None:
        """Força reset do martingale (sem registrar resultado)."""
        with self._lock:
            old_dobra = self._current_dobra
            self._current_dobra = 1
            self._cycle_invested = 0.0
            self._state = MartingaleState.IDLE
            self._current_cycle = None

        if self._emit_events:
            emit(
                BotEvent.MARTINGALE_RESET,
                {
                    "reason": "forced",
                    "old_dobra": old_dobra,
                },
            )

        logger.info(f"Martingale resetado forçadamente: {old_dobra} → 1")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONSULTAS
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def current_dobra(self) -> int:
        """Retorna a dobra atual."""
        return self._current_dobra

    @property
    def is_active(self) -> bool:
        """Verifica se está em ciclo ativo (dobra > 1)."""
        return self._current_dobra > 1

    @property
    def is_max_reached(self) -> bool:
        """Verifica se atingiu dobra máxima."""
        return self._state == MartingaleState.MAX_REACHED

    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do martingale."""
        with self._lock:
            bet = self.get_current_bet()

            return {
                "state": self._state.value,
                "current_dobra": self._current_dobra,
                "max_dobra": self._config.max_dobra,
                "base_bet": self._config.base_bet,
                "current_bet": bet.amount,
                "cycle_invested": self._cycle_invested,
                "is_recovery": bet.is_recovery,
                "potential_profit": bet.potential_profit,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas históricas."""
        with self._lock:
            total_cycles = len(self._completed_cycles)
            wins = sum(1 for c in self._completed_cycles if c.final_result == "win")
            losses = total_cycles - wins

            total_profit = sum(c.profit for c in self._completed_cycles)

            return {
                "total_wins": self._total_wins,
                "total_losses": self._total_losses,
                "win_rate": (
                    self._total_wins / (self._total_wins + self._total_losses) * 100
                    if (self._total_wins + self._total_losses) > 0
                    else 0
                ),
                "consecutive_losses": self._consecutive_losses,
                "max_consecutive_losses": self._max_consecutive_losses,
                "completed_cycles": total_cycles,
                "cycle_wins": wins,
                "cycle_losses": losses,
                "total_profit": total_profit,
            }

    def get_progression_table(self) -> List[Dict[str, Any]]:
        """Retorna tabela de progressão de apostas."""
        table = []

        for dobra in range(1, self._config.max_dobra + 1):
            multiplier = self._config.multipliers.get(dobra, 2 ** (dobra - 1))
            amount = self._config.base_bet * multiplier

            table.append(
                {
                    "dobra": dobra,
                    "multiplier": multiplier,
                    "amount": round(amount, 2),
                    "is_current": dobra == self._current_dobra,
                }
            )

        return table


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_martingale_system: Optional[MartingaleSystem] = None
_martingale_lock = threading.Lock()


def get_martingale() -> MartingaleSystem:
    """
    Retorna a instância singleton do MartingaleSystem.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _martingale_system

    if _martingale_system is None:
        with _martingale_lock:
            if _martingale_system is None:
                _martingale_system = MartingaleSystem()

    return _martingale_system


def reset_martingale() -> None:
    """Reseta o sistema de martingale (útil para testes)."""
    global _martingale_system
    with _martingale_lock:
        if _martingale_system:
            _martingale_system.force_reset()
        _martingale_system = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO MARTINGALE SYSTEM - CrashBot v3.0")
    print("=" * 60)

    # Cria sistema
    mg = MartingaleSystem(emit_events=False)
    mg.configure_from_balance(1000.0)  # Banca operacional de R$ 1000

    print(f"\n✅ MartingaleSystem criado")
    print(f"   Base bet: R$ {mg._config.base_bet:.2f}")
    print(f"   Max dobra: {mg._config.max_dobra}")

    # Tabela de progressão
    print(f"\n--- Tabela de Progressão ---")
    for row in mg.get_progression_table():
        marker = " ◄" if row["is_current"] else ""
        print(
            f"   Dobra {row['dobra']}: {row['multiplier']}x = R$ {row['amount']:.2f}{marker}"
        )

    # Simula sequência
    print(f"\n--- Simulação ---")

    # Cenário: LOSS, LOSS, WIN
    print("\nCenário 1: LOSS → LOSS → WIN")

    bet = mg.get_current_bet()
    print(f"   Aposta: R$ {bet.amount:.2f} (Dobra {bet.dobra})")
    mg.record_loss()

    bet = mg.get_current_bet()
    print(f"   Aposta: R$ {bet.amount:.2f} (Dobra {bet.dobra})")
    mg.record_loss()

    bet = mg.get_current_bet()
    print(f"   Aposta: R$ {bet.amount:.2f} (Dobra {bet.dobra})")
    mg.record_win(profit=bet.amount * 0.85)

    bet = mg.get_current_bet()
    print(f"   Após WIN: R$ {bet.amount:.2f} (Dobra {bet.dobra})")

    # Cenário: 4 LOSSES (atinge máximo)
    print("\nCenário 2: 4x LOSS (atinge máximo)")

    for i in range(4):
        bet = mg.get_current_bet()
        print(f"   Aposta: R$ {bet.amount:.2f} (Dobra {bet.dobra})")
        has_more = mg.record_loss()
        if not has_more:
            print(f"   ⚠️ Dobra máxima atingida!")

    bet = mg.get_current_bet()
    print(f"   Após reset: R$ {bet.amount:.2f} (Dobra {bet.dobra})")

    # Stats
    print(f"\n--- Estatísticas ---")
    stats = mg.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
