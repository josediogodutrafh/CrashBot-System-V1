#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - ENGINE TRADING MODULE

Sistema de execução de apostas automatizadas.

Módulos:
- executor: Executa apostas via cliques e digitação

Uso:
    from engine.trading import get_executor, BetSlot

    executor = get_executor()
    executor.load_profile_from_config("Monitor 1")

    # Executa aposta
    result = executor.place_bet(amount=10.0, target=1.85)

    if result.success:
        print(f"Aposta realizada em {result.execution_time:.2f}s")
"""

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

from engine.trading.executor import (  # Classes principais; Enums; Dataclasses; Singleton
    BetExecutor,
    BetResult,
    BetSlot,
    ClickPoint,
    ExecutionStatus,
    ExecutorConfig,
    ExecutorProfile,
    get_executor,
    reset_executor,
)

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Classes
    "BetExecutor",
    # Enums
    "BetSlot",
    "ExecutionStatus",
    # Dataclasses
    "ClickPoint",
    "ExecutorProfile",
    "BetResult",
    "ExecutorConfig",
    # Singleton
    "get_executor",
    "reset_executor",
]
