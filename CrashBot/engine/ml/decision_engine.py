#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - DECISION ENGINE

Motor de decisão que combina sinais de múltiplas fontes:
- Regras fixas (gatilho de velas baixas)
- LSTM (previsão de próxima explosão)
- RL Agent (decisão de ação)
- Otimização (parâmetros ajustados)

Usa votação ponderada para decisão final.

Uso:
    from engine.ml.decision_engine import DecisionEngine, get_decision_engine

    engine = get_decision_engine()

    # Configura pesos
    engine.configure_weights(rules=0.3, lstm=0.3, rl=0.4)

    # Obtém decisão
    decision = engine.get_decision(current_state, explosions_history)

    if decision.should_bet:
        print(f"Apostar! Confiança: {decision.confidence:.1%}")
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Core imports
from core.events import BotEvent, emit
from engine.strategy.martingale import BetInfo, MartingaleSystem, get_martingale

# Local imports - Strategy
from engine.strategy.trigger import TriggerResult, TriggerSystem, get_trigger

# Local imports - ML (importação condicional)
try:
    from engine.ml.data_collector import DataCollector, get_collector

    HAS_COLLECTOR = True
except ImportError:
    HAS_COLLECTOR = False

try:
    from engine.ml.predictor_lstm import (
        LSTMPredictor,
        Prediction,
        PredictionMode,
        get_predictor,
    )

    HAS_LSTM = True
except ImportError:
    HAS_LSTM = False

try:
    from engine.ml.rl_agent import PredictionResult as RLPrediction
    from engine.ml.rl_agent import RLAgent, get_agent

    HAS_RL = True
except ImportError:
    HAS_RL = False

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class DecisionSource(Enum):
    """Fontes de decisão."""

    RULES = "rules"  # Regras fixas (gatilho)
    LSTM = "lstm"  # Preditor LSTM
    RL = "rl"  # Agente RL
    COMBINED = "combined"  # Votação combinada


class ActionDecision(Enum):
    """Decisões possíveis."""

    SKIP = "skip"  # Não apostar
    BET = "bet"  # Apostar
    WAIT = "wait"  # Aguardar mais dados


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SignalVote:
    """Voto de uma fonte de sinal."""

    source: DecisionSource
    action: ActionDecision
    confidence: float  # 0.0 - 1.0
    weight: float  # Peso na votação
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """Score ponderado (confiança * peso)."""
        return self.confidence * self.weight


@dataclass
class FinalDecision:
    """Decisão final do engine."""

    action: ActionDecision
    should_bet: bool
    confidence: float
    bet_info: Optional[BetInfo] = None
    suggested_target: float = 1.85
    votes: List[SignalVote] = field(default_factory=list)
    reasoning: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "should_bet": self.should_bet,
            "confidence": self.confidence,
            "suggested_target": self.suggested_target,
            "reasoning": self.reasoning,
            "votes": [
                {
                    "source": v.source.value,
                    "action": v.action.value,
                    "confidence": v.confidence,
                    "weight": v.weight,
                }
                for v in self.votes
            ],
        }


@dataclass
class EngineConfig:
    """Configuração do Decision Engine."""

    # Pesos das fontes
    weight_rules: float = 0.4
    weight_lstm: float = 0.3
    weight_rl: float = 0.3

    # Thresholds
    min_confidence_to_bet: float = 0.6
    min_votes_to_bet: int = 2

    # Parâmetros de estratégia (podem vir do optimizer)
    trigger_threshold: float = 2.0
    trigger_lows_needed: int = 8
    default_target: float = 1.85


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class DecisionEngine:
    """
    Motor de decisão central.

    Combina sinais de múltiplas fontes usando votação ponderada:
    1. Regras fixas (TriggerSystem)
    2. LSTM (previsão de próxima explosão)
    3. RL Agent (decisão aprendida)

    A decisão final considera:
    - Votos de cada fonte
    - Confiança de cada voto
    - Peso configurado para cada fonte
    - Threshold mínimo de confiança

    Exemplo:
        engine = DecisionEngine()

        # Configura pesos (opcional)
        engine.configure_weights(rules=0.4, lstm=0.3, rl=0.3)

        # A cada rodada
        decision = engine.get_decision(
            state=current_state,
            explosions=last_20_explosions,
        )

        if decision.should_bet:
            bet_amount = decision.bet_info.amount
            target = decision.suggested_target
            execute_bet(bet_amount, target)
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        use_lstm: bool = True,
        use_rl: bool = True,
    ):
        """
        Inicializa o Decision Engine.

        Args:
            config: Configuração do engine
            use_lstm: Se True, usa preditor LSTM
            use_rl: Se True, usa agente RL
        """
        self._lock = threading.Lock()
        self._config = config or EngineConfig()

        # Flags de componentes
        self._use_lstm = use_lstm and HAS_LSTM
        self._use_rl = use_rl and HAS_RL

        # Componentes (lazy loading)
        self._trigger: Optional[TriggerSystem] = None
        self._martingale: Optional[MartingaleSystem] = None
        self._collector: Optional[DataCollector] = None
        self._lstm: Optional[LSTMPredictor] = None
        self._rl_agent: Optional[RLAgent] = None

        # Estado
        self._last_decision: Optional[FinalDecision] = None
        self._decision_history: List[FinalDecision] = []
        self._max_history = 100

        # Estatísticas
        self._stats = {
            "total_decisions": 0,
            "bet_decisions": 0,
            "skip_decisions": 0,
            "correct_bets": 0,
            "incorrect_bets": 0,
        }

        logger.info(
            f"DecisionEngine inicializado: lstm={self._use_lstm}, rl={self._use_rl}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def configure_weights(
        self,
        rules: Optional[float] = None,
        lstm: Optional[float] = None,
        rl: Optional[float] = None,
    ) -> None:
        """
        Configura pesos das fontes de decisão.

        Args:
            rules: Peso para regras fixas
            lstm: Peso para LSTM
            rl: Peso para RL Agent
        """
        with self._lock:
            if rules is not None:
                self._config.weight_rules = rules
            if lstm is not None:
                self._config.weight_lstm = lstm
            if rl is not None:
                self._config.weight_rl = rl

            # Normaliza pesos
            total = (
                self._config.weight_rules
                + self._config.weight_lstm
                + self._config.weight_rl
            )

            if total > 0:
                self._config.weight_rules /= total
                self._config.weight_lstm /= total
                self._config.weight_rl /= total

        logger.info(
            f"Pesos configurados: rules={self._config.weight_rules:.2f}, "
            f"lstm={self._config.weight_lstm:.2f}, rl={self._config.weight_rl:.2f}"
        )

    def configure_thresholds(
        self,
        min_confidence: Optional[float] = None,
        min_votes: Optional[int] = None,
    ) -> None:
        """
        Configura thresholds de decisão.

        Args:
            min_confidence: Confiança mínima para apostar
            min_votes: Mínimo de votos positivos
        """
        with self._lock:
            if min_confidence is not None:
                self._config.min_confidence_to_bet = min_confidence
            if min_votes is not None:
                self._config.min_votes_to_bet = min_votes

    def configure_strategy(
        self,
        threshold: Optional[float] = None,
        lows_needed: Optional[int] = None,
        default_target: Optional[float] = None,
    ) -> None:
        """
        Configura parâmetros de estratégia.

        Args:
            threshold: Limite para vela baixa
            lows_needed: Velas baixas necessárias
            default_target: Alvo padrão
        """
        with self._lock:
            if threshold is not None:
                self._config.trigger_threshold = threshold
            if lows_needed is not None:
                self._config.trigger_lows_needed = lows_needed
            if default_target is not None:
                self._config.default_target = default_target

        # Atualiza trigger se já inicializado
        if self._trigger:
            self._trigger.configure(
                threshold=self._config.trigger_threshold,
                lows_needed=self._config.trigger_lows_needed,
            )

    def load_optimized_params(self, params: Dict[str, Any]) -> None:
        """
        Carrega parâmetros otimizados pelo Optuna.

        Args:
            params: Dicionário de parâmetros otimizados
        """
        # Parâmetros de estratégia
        if "trigger" in params:
            trigger_params = params["trigger"]
            self.configure_strategy(
                threshold=trigger_params.get("threshold"),
                lows_needed=trigger_params.get("lows_needed"),
            )

        if "betting" in params:
            betting_params = params["betting"]
            self.configure_strategy(
                default_target=betting_params.get("target"),
            )

        logger.info(f"Parâmetros otimizados carregados: {params}")

    # ═══════════════════════════════════════════════════════════════════════════
    # INICIALIZAÇÃO DE COMPONENTES
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_trigger(self) -> TriggerSystem:
        """Obtém ou cria TriggerSystem."""
        if self._trigger is None:
            self._trigger = get_trigger()
            self._trigger.configure(
                threshold=self._config.trigger_threshold,
                lows_needed=self._config.trigger_lows_needed,
            )
        return self._trigger

    def _get_martingale(self) -> MartingaleSystem:
        """Obtém ou cria MartingaleSystem."""
        if self._martingale is None:
            self._martingale = get_martingale()
        return self._martingale

    def _get_collector(self) -> Optional[DataCollector]:
        """Obtém ou cria DataCollector."""
        if not HAS_COLLECTOR:
            return None
        if self._collector is None:
            self._collector = get_collector()
        return self._collector

    def _get_lstm(self) -> Optional[LSTMPredictor]:
        """Obtém ou cria LSTMPredictor."""
        if not self._use_lstm or not HAS_LSTM:
            return None
        if self._lstm is None:
            self._lstm = get_predictor()
        return self._lstm

    def _get_rl_agent(self) -> Optional[RLAgent]:
        """Obtém ou cria RLAgent."""
        if not self._use_rl or not HAS_RL:
            return None
        if self._rl_agent is None:
            self._rl_agent = get_agent()
        return self._rl_agent

    # ═══════════════════════════════════════════════════════════════════════════
    # COLETA DE VOTOS
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_rules_vote(self, explosions: List[float]) -> SignalVote:
        """
        Obtém voto das regras fixas (trigger).

        Args:
            explosions: Histórico de explosões

        Returns:
            SignalVote com decisão baseada em regras
        """
        trigger = self._get_trigger()

        # Alimenta trigger com última explosão se não estiver atualizado
        if explosions:
            # Simula processamento das últimas explosões
            trigger.reset()
            for value in explosions[-20:]:  # Últimas 20
                result = trigger.add_explosion(value)

        status = trigger.get_status()

        # Decide baseado no status
        if status.triggered:
            action = ActionDecision.BET
            confidence = min(1.0, 0.7 + (status.current_count - status.needed) * 0.1)
        elif status.current_count >= status.needed - 2:
            action = ActionDecision.WAIT
            confidence = status.progress_percent / 100.0
        else:
            action = ActionDecision.SKIP
            confidence = 1.0 - (status.progress_percent / 100.0)

        return SignalVote(
            source=DecisionSource.RULES,
            action=action,
            confidence=confidence,
            weight=self._config.weight_rules,
            details={
                "trigger_progress": status.progress_str,
                "streak": status.current_count,
                "needed": status.needed,
            },
        )

    def _get_lstm_vote(self, explosions: List[float]) -> Optional[SignalVote]:
        """
        Obtém voto do preditor LSTM.

        Args:
            explosions: Histórico de explosões

        Returns:
            SignalVote ou None se LSTM não disponível
        """
        lstm = self._get_lstm()

        if lstm is None or not lstm.is_trained:
            return None

        if len(explosions) < 20:
            return None

        # Faz predição
        prediction = lstm.predict(explosions[-20:])

        # Converte predição em decisão
        if prediction.classification.value == "low":
            # LSTM prevê explosão baixa -> pode apostar
            action = ActionDecision.BET
            confidence = prediction.confidence
        elif prediction.classification.value == "uncertain":
            action = ActionDecision.WAIT
            confidence = 0.5
        else:
            # LSTM prevê explosão alta -> não apostar
            action = ActionDecision.SKIP
            confidence = prediction.confidence

        return SignalVote(
            source=DecisionSource.LSTM,
            action=action,
            confidence=confidence,
            weight=self._config.weight_lstm,
            details={
                "prediction": prediction.classification.value,
                "raw_confidence": prediction.confidence,
                "value": prediction.value,
            },
        )

    def _get_rl_vote(self, state: np.ndarray) -> Optional[SignalVote]:
        """
        Obtém voto do agente RL.

        Args:
            state: Estado atual (observação)

        Returns:
            SignalVote ou None se RL não disponível
        """
        rl_agent = self._get_rl_agent()

        if rl_agent is None or not rl_agent.is_trained:
            return None

        # Faz predição
        prediction = rl_agent.predict(state)

        # Converte ação em decisão
        if prediction.action == 0:  # SKIP
            action = ActionDecision.SKIP
        else:
            action = ActionDecision.BET

        return SignalVote(
            source=DecisionSource.RL,
            action=action,
            confidence=prediction.confidence,
            weight=self._config.weight_rl,
            details={
                "action": prediction.action,
                "action_name": prediction.action_name,
            },
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # DECISÃO FINAL
    # ═══════════════════════════════════════════════════════════════════════════

    def get_decision(
        self,
        state: Optional[np.ndarray] = None,
        explosions: Optional[List[float]] = None,
    ) -> FinalDecision:
        """
        Obtém decisão final combinando todas as fontes.

        Args:
            state: Estado para RL (opcional)
            explosions: Histórico de explosões

        Returns:
            FinalDecision com ação recomendada
        """
        with self._lock:
            explosions = explosions or []
            votes: List[SignalVote] = []

            # Coleta votos
            # 1. Regras fixas (sempre disponível)
            rules_vote = self._get_rules_vote(explosions)
            votes.append(rules_vote)

            # 2. LSTM (se disponível e treinado)
            if self._use_lstm:
                lstm_vote = self._get_lstm_vote(explosions)
                if lstm_vote:
                    votes.append(lstm_vote)

            # 3. RL Agent (se disponível e treinado)
            if self._use_rl and state is not None:
                rl_vote = self._get_rl_vote(state)
                if rl_vote:
                    votes.append(rl_vote)

            # Calcula decisão final por votação ponderada
            bet_score = 0.0
            skip_score = 0.0
            total_weight = 0.0

            bet_votes = 0

            for vote in votes:
                total_weight += vote.weight

                if vote.action == ActionDecision.BET:
                    bet_score += vote.weighted_score
                    bet_votes += 1
                elif vote.action == ActionDecision.SKIP:
                    skip_score += vote.weighted_score
                elif vote.action == ActionDecision.WAIT:
                    # WAIT conta parcialmente para ambos
                    bet_score += vote.weighted_score * 0.3
                    skip_score += vote.weighted_score * 0.3

            # Normaliza scores
            if total_weight > 0:
                bet_score /= total_weight
                skip_score /= total_weight

            # Decide
            if (
                bet_score > skip_score
                and bet_score >= self._config.min_confidence_to_bet
            ):
                if (
                    bet_votes >= self._config.min_votes_to_bet
                    or len(votes) < self._config.min_votes_to_bet
                ):
                    action = ActionDecision.BET
                    confidence = bet_score
                    should_bet = True
                else:
                    action = ActionDecision.WAIT
                    confidence = bet_score
                    should_bet = False
            else:
                action = ActionDecision.SKIP
                confidence = skip_score
                should_bet = False

            # Obtém info de aposta
            martingale = self._get_martingale()
            bet_info = martingale.get_current_bet()

            # Determina alvo sugerido
            suggested_target = self._config.default_target

            # Se RL votou BET, usa o alvo sugerido pelo RL
            for vote in votes:
                if (
                    vote.source == DecisionSource.RL
                    and vote.action == ActionDecision.BET
                ):
                    action_name = vote.details.get("action_name", "")
                    if "1.5x" in action_name:
                        suggested_target = 1.50
                    elif "2.0x" in action_name:
                        suggested_target = 2.00
                    elif "3.0x" in action_name:
                        suggested_target = 3.00

            # Gera reasoning
            reasoning_parts = []
            for vote in votes:
                reasoning_parts.append(
                    f"{vote.source.value}: {vote.action.value} ({vote.confidence:.1%})"
                )
            reasoning = " | ".join(reasoning_parts)

            # Cria decisão final
            decision = FinalDecision(
                action=action,
                should_bet=should_bet,
                confidence=confidence,
                bet_info=bet_info,
                suggested_target=suggested_target,
                votes=votes,
                reasoning=reasoning,
            )

            # Atualiza estado
            self._last_decision = decision
            self._decision_history.append(decision)
            if len(self._decision_history) > self._max_history:
                self._decision_history = self._decision_history[-self._max_history :]

            # Estatísticas
            self._stats["total_decisions"] += 1
            if should_bet:
                self._stats["bet_decisions"] += 1
            else:
                self._stats["skip_decisions"] += 1

            # Emite evento
            emit(BotEvent.DECISION_MADE, decision.to_dict())

            return decision

    def record_result(self, won: bool) -> None:
        """
        Registra resultado da última decisão (para estatísticas).

        Args:
            won: Se a aposta foi vencedora
        """
        with self._lock:
            if self._last_decision and self._last_decision.should_bet:
                if won:
                    self._stats["correct_bets"] += 1
                else:
                    self._stats["incorrect_bets"] += 1

    # ═══════════════════════════════════════════════════════════════════════════
    # MODOS SIMPLIFICADOS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_rules_only_decision(self, explosions: List[float]) -> FinalDecision:
        """
        Decisão usando apenas regras fixas (sem ML).

        Útil quando modelos não estão treinados.
        """
        old_lstm = self._use_lstm
        old_rl = self._use_rl

        self._use_lstm = False
        self._use_rl = False

        try:
            return self.get_decision(explosions=explosions)
        finally:
            self._use_lstm = old_lstm
            self._use_rl = old_rl

    def get_ml_only_decision(
        self,
        state: np.ndarray,
        explosions: List[float],
    ) -> FinalDecision:
        """
        Decisão usando apenas ML (LSTM + RL).

        Útil para comparar performance.
        """
        old_rules_weight = self._config.weight_rules
        self._config.weight_rules = 0.0

        try:
            # Rebalanceia pesos
            total = self._config.weight_lstm + self._config.weight_rl
            if total > 0:
                self._config.weight_lstm /= total
                self._config.weight_rl /= total

            return self.get_decision(state=state, explosions=explosions)
        finally:
            self._config.weight_rules = old_rules_weight
            self.configure_weights()  # Renormaliza

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do engine."""
        return {
            "config": {
                "weight_rules": self._config.weight_rules,
                "weight_lstm": self._config.weight_lstm,
                "weight_rl": self._config.weight_rl,
                "min_confidence": self._config.min_confidence_to_bet,
            },
            "components": {
                "lstm_available": self._use_lstm and HAS_LSTM,
                "lstm_trained": self._lstm.is_trained if self._lstm else False,
                "rl_available": self._use_rl and HAS_RL,
                "rl_trained": self._rl_agent.is_trained if self._rl_agent else False,
            },
            "stats": self._stats,
            "last_decision": (
                self._last_decision.to_dict() if self._last_decision else None
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas."""
        stats = self._stats.copy()

        total_bets = stats["correct_bets"] + stats["incorrect_bets"]
        if total_bets > 0:
            stats["accuracy"] = stats["correct_bets"] / total_bets
        else:
            stats["accuracy"] = 0.0

        return stats

    def reset_stats(self) -> None:
        """Reseta estatísticas."""
        with self._lock:
            self._stats = {
                "total_decisions": 0,
                "bet_decisions": 0,
                "skip_decisions": 0,
                "correct_bets": 0,
                "incorrect_bets": 0,
            }

    def get_decision_history(self, limit: int = 20) -> List[Dict]:
        """Retorna histórico de decisões."""
        return [d.to_dict() for d in self._decision_history[-limit:]]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_decision_engine: Optional[DecisionEngine] = None
_engine_lock = threading.Lock()


def get_decision_engine(**kwargs) -> DecisionEngine:
    """
    Retorna a instância singleton do DecisionEngine.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _decision_engine

    if _decision_engine is None:
        with _engine_lock:
            if _decision_engine is None:
                _decision_engine = DecisionEngine(**kwargs)

    return _decision_engine


def reset_decision_engine() -> None:
    """Reseta o decision engine (útil para testes)."""
    global _decision_engine
    with _engine_lock:
        _decision_engine = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO DECISION ENGINE - CrashBot v3.0")
    print("=" * 60)

    # Cria engine (sem ML para teste simples)
    engine = DecisionEngine(use_lstm=False, use_rl=False)

    print(f"\n✅ DecisionEngine criado")

    # Status
    print(f"\n--- Status ---")
    status = engine.get_status()
    print(f"   Pesos: rules={status['config']['weight_rules']:.2f}")
    print(f"   LSTM disponível: {status['components']['lstm_available']}")
    print(f"   RL disponível: {status['components']['rl_available']}")

    # Simula explosões
    print(f"\n--- Simulação ---")
    import random

    explosions = []

    for i in range(30):
        # Gera explosão
        if random.random() < 0.6:
            value = round(random.uniform(1.0, 1.99), 2)
        else:
            value = round(random.uniform(2.0, 5.0), 2)

        explosions.append(value)

        # Obtém decisão
        decision = engine.get_decision(explosions=explosions)

        emoji = "🔴" if value < 2.0 else "🟢"
        bet_emoji = "💰" if decision.should_bet else "⏸️"

        print(
            f"   {i+1:2d}. {emoji} {value:.2f}x → {bet_emoji} {decision.action.value} ({decision.confidence:.1%})"
        )
        print(f"       Reasoning: {decision.reasoning}")

        # Simula resultado se apostou
        if decision.should_bet:
            # Próxima explosão determina resultado
            next_value = (
                random.uniform(1.0, 1.99)
                if random.random() < 0.6
                else random.uniform(2.0, 5.0)
            )
            won = next_value >= decision.suggested_target
            engine.record_result(won)
            result_emoji = "✅" if won else "❌"
            print(f"       Resultado: {result_emoji} (next={next_value:.2f}x)")

    # Estatísticas finais
    print(f"\n--- Estatísticas ---")
    stats = engine.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2%}")
        else:
            print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
