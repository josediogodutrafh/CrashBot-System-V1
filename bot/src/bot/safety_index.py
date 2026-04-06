"""
SafetyIndex - Indice de seguranca em tempo real por plataforma.

Calcula um score de 0.0 a 1.0 baseado em multiplos fatores:
- Distribuicao de LOWs (rolling %LOW vs referencia)
- Drawdown atual (distancia do pico)
- Win rate recente (ultimas N apostas)
- Lucro da sessao (buffer para absorver perdas)
- Razao bankroll/banca (margem de seguranca)

O SafetyIndex alimenta o StrategyAdvisor, que decide:
- Qual setup usar (agressivo vs conservador)
- Quanto compound aplicar
- Se deve pausar

Niveis:
    0.8 - 1.0  AGRESSIVO   (verde)   Martingale 1/2/4/8, compound 75%
    0.5 - 0.8  NORMAL      (azul)    Martingale 1/2/4, compound 50%
    0.3 - 0.5  CONSERVADOR (amarelo) Half-Kelly ou 1/2, compound 0%
    0.0 - 0.3  DEFENSIVO   (vermelho) Flat ou PAUSA
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Referencia: %LOW esperado (~55% dos rounds < 2.0x)
REFERENCE_PCT_LOW = 0.55

# Pesos dos fatores no indice final
W_DISTRIBUTION = 0.20   # %LOW rolling vs referencia
W_DRAWDOWN = 0.25       # quao longe do pico estamos
W_WIN_RATE = 0.20       # taxa de acerto recente
W_PROFIT = 0.20         # lucro da sessao (buffer)
W_BANKROLL = 0.15       # margem bankroll/banca


@dataclass
class SafetySnapshot:
    """Snapshot imutavel do estado de seguranca."""
    index: float = 0.5        # 0.0 a 1.0
    level: str = "normal"     # defensivo | conservador | normal | agressivo
    color: str = "blue"       # red | yellow | blue | green

    # Componentes individuais (para debug/GUI)
    distribution_score: float = 0.5
    drawdown_score: float = 1.0
    win_rate_score: float = 0.5
    profit_score: float = 0.5
    bankroll_score: float = 0.5

    # Dados brutos
    pct_low: float = 0.55
    drawdown_pct: float = 0.0
    win_rate: float = 0.0
    session_profit_pct: float = 0.0
    bankroll_ratio: float = 1.0
    total_rounds: int = 0


def _level_from_index(index: float) -> tuple:
    """Retorna (level, color) baseado no indice."""
    if index >= 0.8:
        return "agressivo", "green"
    elif index >= 0.5:
        return "normal", "blue"
    elif index >= 0.3:
        return "conservador", "yellow"
    else:
        return "defensivo", "red"


class SafetyIndex:
    """Calculador de indice de seguranca em tempo real.

    Alimentado por cada round (explosion value) e por estado
    do bankroll/session. Recalcula o indice a cada chamada.
    """

    def __init__(
        self,
        rolling_window: int = 200,
        win_rate_window: int = 50,
        min_rounds_for_score: int = 30,
    ):
        self._rolling_window = rolling_window
        self._win_rate_window = win_rate_window
        self._min_rounds = min_rounds_for_score

        # Historicos rolling
        self._low_history: deque = deque(maxlen=rolling_window)
        self._bet_results: deque = deque(maxlen=win_rate_window)

        # Tracking de pico e drawdown
        self._peak_balance: float = 0.0
        self._current_balance: float = 0.0

        # Session
        self._initial_balance: float = 0.0
        self._banca: float = 0.0
        self._total_rounds: int = 0

        # Ultimo snapshot calculado
        self._last_snapshot = SafetySnapshot()

    def initialize(self, balance: float, banca: float):
        """Inicializa com saldo e banca da sessao."""
        self._initial_balance = balance
        self._current_balance = balance
        self._peak_balance = balance
        self._banca = banca
        logger.debug(
            f"SafetyIndex inicializado: saldo={balance:.2f}, banca={banca:.2f}"
        )

    def feed_round(self, explosion: float, threshold: float = 2.0):
        """Alimenta com resultado de um round."""
        self._total_rounds += 1
        is_low = 1 if explosion < threshold else 0
        self._low_history.append(is_low)

    def feed_bet_result(self, is_hit: bool):
        """Alimenta com resultado de uma aposta."""
        self._bet_results.append(1 if is_hit else 0)

    def update_balance(self, balance: float):
        """Atualiza saldo atual (chamado apos cada balance_update)."""
        self._current_balance = balance
        if balance > self._peak_balance:
            self._peak_balance = balance

    # ── Calculo dos componentes ─────────────────────────────────────

    def _calc_distribution_score(self) -> tuple:
        """Score baseado em %LOW vs referencia.

        %LOW proximo de 55% = score alto (distribuicao normal)
        %LOW muito alto ou baixo = score baixo (anomalia)
        """
        if len(self._low_history) < 20:
            return 0.5, REFERENCE_PCT_LOW

        pct_low = sum(self._low_history) / len(self._low_history)
        # Desvio absoluto da referencia (0 = perfeito, 0.1 = 10% de desvio)
        deviation = abs(pct_low - REFERENCE_PCT_LOW)

        # Score: 1.0 quando desvio=0, 0.0 quando desvio>=0.15
        score = max(0.0, 1.0 - (deviation / 0.15))
        return score, pct_low

    def _calc_drawdown_score(self) -> tuple:
        """Score baseado no drawdown atual.

        Sem drawdown = 1.0
        Drawdown de 50%+ = 0.0
        """
        if self._peak_balance <= 0:
            return 1.0, 0.0

        dd = (self._peak_balance - self._current_balance) / self._peak_balance
        dd = max(0.0, dd)

        # Score: 1.0 quando dd=0, 0.0 quando dd>=0.50
        score = max(0.0, 1.0 - (dd / 0.50))
        return score, dd

    def _calc_win_rate_score(self) -> tuple:
        """Score baseado na taxa de acerto recente.

        Win rate >= 60% = score 1.0 (otimo)
        Win rate ~45% (esperado para 2.0x) = score 0.5
        Win rate < 30% = score 0.0 (perigoso)
        """
        if len(self._bet_results) < 5:
            return 0.5, 0.0

        wr = sum(self._bet_results) / len(self._bet_results)

        # Normalizar: 30% → 0.0, 45% → 0.5, 60%+ → 1.0
        score = (wr - 0.30) / 0.30
        score = max(0.0, min(1.0, score))
        return score, wr

    def _calc_profit_score(self) -> tuple:
        """Score baseado no lucro da sessao como % do saldo inicial.

        Lucro >= 20% = score 1.0 (grande buffer)
        Break-even = score 0.5
        Prejuizo >= 30% = score 0.0
        """
        if self._initial_balance <= 0:
            return 0.5, 0.0

        profit_pct = (
            (self._current_balance - self._initial_balance) / self._initial_balance
        )

        # Normalizar: -30% → 0.0, 0% → 0.5, +20% → 1.0
        if profit_pct >= 0:
            score = 0.5 + (profit_pct / 0.20) * 0.5
        else:
            score = 0.5 + (profit_pct / 0.30) * 0.5

        score = max(0.0, min(1.0, score))
        return score, profit_pct

    def _calc_bankroll_score(self) -> tuple:
        """Score baseado na razao saldo/banca.

        Saldo >= 3x banca = score 1.0 (grande margem)
        Saldo = 1x banca = score 0.5 (normal)
        Saldo < 0.5x banca = score 0.0 (perigoso)
        """
        if self._banca <= 0:
            return 0.5, 1.0

        ratio = self._current_balance / self._banca

        # Normalizar: 0.5 → 0.0, 1.0 → 0.5, 3.0 → 1.0
        if ratio >= 1.0:
            score = 0.5 + ((ratio - 1.0) / 2.0) * 0.5
        else:
            score = max(0.0, (ratio - 0.5) / 0.5 * 0.5)

        score = max(0.0, min(1.0, score))
        return score, ratio

    # ── Calculo final ─────────────────────────────────────────────

    def calculate(self) -> SafetySnapshot:
        """Calcula e retorna o snapshot de seguranca atual."""
        # Se nao tem dados suficientes, retorna default conservador
        if self._total_rounds < self._min_rounds:
            self._last_snapshot = SafetySnapshot(
                index=0.5,
                level="normal",
                color="blue",
                total_rounds=self._total_rounds,
            )
            return self._last_snapshot

        # Calcular componentes
        dist_score, pct_low = self._calc_distribution_score()
        dd_score, dd_pct = self._calc_drawdown_score()
        wr_score, wr = self._calc_win_rate_score()
        profit_score, profit_pct = self._calc_profit_score()
        br_score, br_ratio = self._calc_bankroll_score()

        # Indice ponderado
        index = (
            W_DISTRIBUTION * dist_score
            + W_DRAWDOWN * dd_score
            + W_WIN_RATE * wr_score
            + W_PROFIT * profit_score
            + W_BANKROLL * br_score
        )

        # Clamp
        index = max(0.0, min(1.0, round(index, 3)))

        level, color = _level_from_index(index)

        self._last_snapshot = SafetySnapshot(
            index=index,
            level=level,
            color=color,
            distribution_score=round(dist_score, 3),
            drawdown_score=round(dd_score, 3),
            win_rate_score=round(wr_score, 3),
            profit_score=round(profit_score, 3),
            bankroll_score=round(br_score, 3),
            pct_low=round(pct_low, 3),
            drawdown_pct=round(dd_pct, 3),
            win_rate=round(wr, 3),
            session_profit_pct=round(profit_pct, 3),
            bankroll_ratio=round(br_ratio, 2),
            total_rounds=self._total_rounds,
        )

        return self._last_snapshot

    @property
    def snapshot(self) -> SafetySnapshot:
        """Retorna o ultimo snapshot calculado (sem recalcular)."""
        return self._last_snapshot

    @property
    def index(self) -> float:
        """Atalho para o indice atual."""
        return self._last_snapshot.index

    @property
    def level(self) -> str:
        """Atalho para o nivel atual."""
        return self._last_snapshot.level
