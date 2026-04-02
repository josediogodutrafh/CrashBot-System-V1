#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - ENGINE STRATEGY MODULE

Sistema de estratégias de apostas.

Módulos:
- trigger: Sistema de gatilhos (conta velas baixas)
- martingale: Gestão de progressão de apostas

Uso:
    from engine.strategy import get_trigger, get_martingale

    # Gatilhos
    trigger = get_trigger()
    trigger.configure(threshold=2.0, lows_needed=8)

    result = trigger.add_explosion(1.45)
    if result.triggered:
        print("Hora de apostar!")

    # Martingale
    mg = get_martingale()
    mg.configure_from_balance(1000.0)

    bet = mg.get_current_bet()
    print(f"Apostar R$ {bet.amount}")
"""

# Martingale
from engine.strategy.martingale import (
    BetInfo,
    MartingaleConfig,
    MartingaleCycle,
    MartingaleState,
    MartingaleSystem,
    get_martingale,
    reset_martingale,
)

# Trigger
from engine.strategy.trigger import (
    TriggerConfig,
    TriggerResult,
    TriggerState,
    TriggerSystem,
    get_trigger,
    reset_trigger,
)

__all__ = [
    # Trigger
    "TriggerSystem",
    "TriggerState",
    "TriggerConfig",
    "TriggerResult",
    "get_trigger",
    "reset_trigger",
    # Martingale
    "MartingaleSystem",
    "MartingaleState",
    "MartingaleConfig",
    "BetInfo",
    "MartingaleCycle",
    "get_martingale",
    "reset_martingale",
]
