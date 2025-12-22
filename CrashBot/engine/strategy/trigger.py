#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SISTEMA DE GATILHOS

Gerencia gatilhos de entrada baseados em padrões de explosões.
Detecta sequências de velas baixas para sinalizar entrada.

Uso:
    from engine.strategy.trigger import TriggerSystem, get_trigger

    trigger = get_trigger()
    trigger.configure(threshold=2.0, lows_needed=8)

    # Alimenta com explosões
    trigger.add_explosion(1.45)
    trigger.add_explosion(1.89)

    # Verifica se gatilho ativou
    if trigger.is_triggered():
        print("Hora de apostar!")
"""

from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Core imports
from core.events import BotEvent, emit, get_event_bus
from core.state import RiskMode, get_state

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class TriggerState(Enum):
    """Estados do gatilho."""

    WAITING = "waiting"  # Aguardando velas baixas
    COUNTING = "counting"  # Contando velas baixas
    TRIGGERED = "triggered"  # Gatilho ativado
    COOLDOWN = "cooldown"  # Em período de espera


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TriggerConfig:
    """Configuração do gatilho."""

    threshold: float = 2.0  # Valor abaixo do qual é "vela baixa"
    lows_needed: int = 8  # Quantas velas baixas para ativar
    reset_on_high: bool = True  # Reseta contagem se vier vela alta

    @classmethod
    def for_mode(cls, mode: RiskMode) -> "TriggerConfig":
        """Cria configuração baseada no modo de risco."""
        configs = {
            RiskMode.CONSERVADOR: cls(threshold=2.0, lows_needed=8),
            RiskMode.MODERADO: cls(threshold=2.0, lows_needed=random.choice([7, 8])),
            RiskMode.AGRESSIVO: cls(threshold=2.0, lows_needed=random.choice([6, 7])),
        }
        return configs.get(mode, cls())


@dataclass
class TriggerResult:
    """Resultado da análise do gatilho."""

    triggered: bool  # Se o gatilho ativou
    current_count: int  # Contagem atual de velas baixas
    needed: int  # Quantas velas precisam
    remaining: int  # Quantas faltam
    progress_percent: float  # Progresso em percentual
    last_value: Optional[float] = None
    state: TriggerState = TriggerState.WAITING

    @property
    def progress_str(self) -> str:
        """Progresso formatado (ex: '5/8')."""
        return f"{self.current_count}/{self.needed}"


# ═══════════════════════════════════════════════════════════════════════════════
# TRIGGER SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════


class TriggerSystem:
    """
    Sistema de gatilhos para entrada.

    Monitora explosões e conta sequências de velas baixas.
    Quando atinge o número configurado, sinaliza entrada.

    Features:
        - Configurável por modo de risco
        - Histórico de explosões
        - Integração com EventBus
        - Análise de padrões

    Exemplo:
        trigger = TriggerSystem()
        trigger.configure(threshold=2.0, lows_needed=8)

        # A cada explosão do jogo
        result = trigger.add_explosion(1.45)

        if result.triggered:
            print("Gatilho ativou! Apostar agora.")
        else:
            print(f"Progresso: {result.progress_str}")
    """

    def __init__(self, emit_events: bool = True):
        """
        Inicializa o sistema de gatilhos.

        Args:
            emit_events: Se True, emite eventos no EventBus
        """
        self._lock = threading.Lock()
        self._emit_events = emit_events

        # Configuração
        self._config = TriggerConfig()

        # Estado
        self._state = TriggerState.WAITING
        self._low_count = 0
        self._total_count = 0

        # Histórico
        self._history: List[float] = []
        self._max_history = 260

        # Última análise
        self._last_result: Optional[TriggerResult] = None

        logger.debug("TriggerSystem inicializado")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def configure(
        self,
        threshold: Optional[float] = None,
        lows_needed: Optional[int] = None,
        reset_on_high: Optional[bool] = None,
    ) -> None:
        """
        Configura os parâmetros do gatilho.

        Args:
            threshold: Valor limite para vela baixa
            lows_needed: Quantidade de velas baixas necessárias
            reset_on_high: Se reseta ao vir vela alta
        """
        with self._lock:
            if threshold is not None:
                self._config.threshold = threshold
            if lows_needed is not None:
                self._config.lows_needed = lows_needed
            if reset_on_high is not None:
                self._config.reset_on_high = reset_on_high

        logger.info(
            f"Gatilho configurado: threshold={self._config.threshold}, "
            f"lows_needed={self._config.lows_needed}"
        )

    def configure_for_mode(self, mode: RiskMode) -> None:
        """
        Configura baseado no modo de risco.

        Args:
            mode: Modo de risco (CONSERVADOR, MODERADO, AGRESSIVO)
        """
        config = TriggerConfig.for_mode(mode)
        self.configure(
            threshold=config.threshold,
            lows_needed=config.lows_needed,
            reset_on_high=config.reset_on_high,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PROCESSAMENTO DE EXPLOSÕES
    # ═══════════════════════════════════════════════════════════════════════════

    def add_explosion(self, value: float) -> TriggerResult:
        """
        Processa uma nova explosão.

        Args:
            value: Valor da explosão

        Returns:
            TriggerResult com o estado atual
        """
        with self._lock:
            # Adiciona ao histórico
            self._history.append(value)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

            self._total_count += 1

            # Analisa a vela
            is_low = value < self._config.threshold

            if is_low:
                self._low_count += 1
                self._state = TriggerState.COUNTING

                # Emite progresso
                if self._emit_events:
                    emit(
                        BotEvent.TRIGGER_PROGRESS,
                        {
                            "count": self._low_count,
                            "needed": self._config.lows_needed,
                            "value": value,
                        },
                    )
            else:
                # Vela alta
                if self._config.reset_on_high:
                    old_count = self._low_count
                    self._low_count = 0
                    self._state = TriggerState.WAITING

                    if self._emit_events and old_count > 0:
                        emit(
                            BotEvent.TRIGGER_RESET,
                            {
                                "reason": "high_value",
                                "value": value,
                                "lost_count": old_count,
                            },
                        )

            # Verifica se ativou
            triggered = self._low_count >= self._config.lows_needed

            if triggered:
                self._state = TriggerState.TRIGGERED

                if self._emit_events:
                    emit(
                        BotEvent.TRIGGER_ACTIVATED,
                        {
                            "count": self._low_count,
                            "history": self._history[-10:],
                        },
                    )

            # Monta resultado
            result = TriggerResult(
                triggered=triggered,
                current_count=self._low_count,
                needed=self._config.lows_needed,
                remaining=max(0, self._config.lows_needed - self._low_count),
                progress_percent=min(
                    100, (self._low_count / self._config.lows_needed) * 100
                ),
                last_value=value,
                state=self._state,
            )

            self._last_result = result
            return result

    def is_triggered(self) -> bool:
        """Verifica se o gatilho está ativado."""
        with self._lock:
            return self._low_count >= self._config.lows_needed

    def reset(self) -> None:
        """Reseta o gatilho para estado inicial."""
        with self._lock:
            self._low_count = 0
            self._state = TriggerState.WAITING
            self._last_result = None

        if self._emit_events:
            emit(BotEvent.TRIGGER_RESET, {"reason": "manual"})

        logger.debug("Gatilho resetado")

    def reset_after_bet(self) -> None:
        """Reseta o gatilho após uma aposta (mantém histórico)."""
        with self._lock:
            self._low_count = 0
            self._state = TriggerState.WAITING

        logger.debug("Gatilho resetado após aposta")

    # ═══════════════════════════════════════════════════════════════════════════
    # ANÁLISE
    # ═══════════════════════════════════════════════════════════════════════════

    def get_status(self) -> TriggerResult:
        """Retorna o status atual do gatilho."""
        with self._lock:
            if self._last_result:
                return self._last_result

            return TriggerResult(
                triggered=False,
                current_count=self._low_count,
                needed=self._config.lows_needed,
                remaining=self._config.lows_needed - self._low_count,
                progress_percent=0,
                state=self._state,
            )

    def get_history(self, limit: int = 50) -> List[float]:
        """Retorna histórico de explosões."""
        with self._lock:
            return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do gatilho."""
        with self._lock:
            history = self._history

            if not history:
                return {
                    "total_explosions": 0,
                    "low_count": 0,
                    "current_streak": self._low_count,
                }

            lows = [v for v in history if v < self._config.threshold]
            highs = [v for v in history if v >= self._config.threshold]

            return {
                "total_explosions": len(history),
                "low_count": len(lows),
                "high_count": len(highs),
                "low_percent": len(lows) / len(history) * 100 if history else 0,
                "average": sum(history) / len(history) if history else 0,
                "min": min(history) if history else 0,
                "max": max(history) if history else 0,
                "current_streak": self._low_count,
                "threshold": self._config.threshold,
                "lows_needed": self._config.lows_needed,
            }

    def analyze_pattern(self) -> Dict[str, Any]:
        """
        Analisa padrões no histórico de explosões.

        Returns:
            Dicionário com análise de padrões
        """
        with self._lock:
            history = self._history

        if len(history) < 10:
            return {"sufficient_data": False}

        # Últimas N explosões
        recent = history[-20:]

        # Conta sequências de lows
        max_streak = 0
        current_streak = 0
        streaks = []

        for value in history:
            if value < self._config.threshold:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0

        if current_streak > 0:
            streaks.append(current_streak)

        # Média e desvio padrão
        import statistics

        avg = statistics.mean(recent) if recent else 0
        std = statistics.stdev(recent) if len(recent) > 1 else 0

        return {
            "sufficient_data": True,
            "recent_average": avg,
            "recent_std": std,
            "max_low_streak": max_streak,
            "avg_low_streak": statistics.mean(streaks) if streaks else 0,
            "is_volatile": std > 2.0,
            "trend": "baixa" if avg < 2.0 else "alta",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_trigger_system: Optional[TriggerSystem] = None
_trigger_lock = threading.Lock()


def get_trigger() -> TriggerSystem:
    """
    Retorna a instância singleton do TriggerSystem.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _trigger_system

    if _trigger_system is None:
        with _trigger_lock:
            if _trigger_system is None:
                _trigger_system = TriggerSystem()

    return _trigger_system


def reset_trigger() -> None:
    """Reseta o sistema de gatilhos (útil para testes)."""
    global _trigger_system
    with _trigger_lock:
        if _trigger_system:
            _trigger_system.reset()
        _trigger_system = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO TRIGGER SYSTEM - CrashBot v3.0")
    print("=" * 60)

    # Cria sistema
    trigger = TriggerSystem(emit_events=False)
    trigger.configure(threshold=2.0, lows_needed=8)

    print(f"\n✅ TriggerSystem criado")
    print(f"   Threshold: {trigger._config.threshold}")
    print(f"   Lows needed: {trigger._config.lows_needed}")

    # Simula explosões
    print(f"\n--- Simulando Explosões ---")

    test_values = [1.23, 1.45, 1.89, 3.21, 1.12, 1.67, 1.34, 1.98, 1.56, 1.23, 1.45]

    for value in test_values:
        result = trigger.add_explosion(value)
        emoji = "🔴" if value < 2.0 else "🟢"
        status = (
            "🎯 TRIGGERED!" if result.triggered else f"Progress: {result.progress_str}"
        )
        print(f"   {emoji} {value:.2f}x → {status}")

        if result.triggered:
            print(f"\n   ✅ Gatilho ativou! Resetando...")
            trigger.reset_after_bet()

    # Stats
    print(f"\n--- Estatísticas ---")
    stats = trigger.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    # Análise de padrão
    print(f"\n--- Análise de Padrão ---")
    pattern = trigger.analyze_pattern()
    for key, value in pattern.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
