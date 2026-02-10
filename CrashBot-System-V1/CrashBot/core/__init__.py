#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - CORE MODULE

Este módulo contém os componentes fundamentais do sistema:
- EventBus: Sistema de eventos publish/subscribe
- StateManager: Gerenciamento centralizado de estado
- Constants: Constantes globais

Uso:
    from core import get_event_bus, get_state, BotEvent, RiskMode

    # EventBus
    bus = get_event_bus()
    bus.publish(BotEvent.SESSION_STARTED, {"mode": "MODERADO"})

    # State
    state = get_state()
    state.trading.current_balance = 1500.0
"""

# Constants
from core.constants import (
    API_BASE_URL,
    BOT_NAME,
    BOT_VERSION,
    MARTINGALE_MAX_DOBRA,
    ML_CONFIDENCE_THRESHOLD,
    RISK_MODE_CONFIG,
    SUSPENSION_SECONDS,
    THEME_COLORS,
)

# EventBus
from core.events import (
    BotEvent,
    EventBus,
    EventData,
    emit,
    emit_async,
    get_event_bus,
    on_event,
    reset_event_bus,
)

# StateManager
from core.state import (
    ConfigState,
    DecisionType,
    ExplosionData,
    HistoryState,
    RiskMode,
    SessionState,
    SessionStatus,
    StateManager,
    StatsState,
    StrategyState,
    TradingState,
    UIState,
    get_state,
    reset_state,
)

__all__ = [
    # EventBus
    "EventBus",
    "EventData",
    "BotEvent",
    "get_event_bus",
    "reset_event_bus",
    "emit",
    "emit_async",
    "on_event",
    # StateManager
    "StateManager",
    "SessionState",
    "TradingState",
    "StrategyState",
    "HistoryState",
    "StatsState",
    "UIState",
    "ConfigState",
    "RiskMode",
    "SessionStatus",
    "DecisionType",
    "ExplosionData",
    "get_state",
    "reset_state",
    # Constants
    "BOT_VERSION",
    "BOT_NAME",
    "API_BASE_URL",
    "RISK_MODE_CONFIG",
    "MARTINGALE_MAX_DOBRA",
    "ML_CONFIDENCE_THRESHOLD",
    "SUSPENSION_SECONDS",
    "THEME_COLORS",
]

__version__ = BOT_VERSION
