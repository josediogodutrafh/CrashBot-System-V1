"""
BotState - Thread-safe shared state between bot logic and GUI.

The bot (background thread) writes via update().
The GUI (main thread) reads via snapshot().
"""

import threading
import time
from typing import Any, Dict, List, Optional


class BotState:
    """Thread-safe state container for bot↔UI communication."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            # Control
            "running": False,
            "paused": False,
            "phase": "config",  # config | connecting | running | stopped

            # Financial
            "caixa": 0.0,
            "banca": 0.0,
            "n_bancas": 0.0,
            "saldo": 0.0,
            "session_profit": 0.0,
            "session_hits": 0,
            "session_misses": 0,
            "round_count": 0,
            "session_start": 0.0,
            "session_hours": 0.0,

            # Stop gain / stop loss
            "stop_gain_pct": 20.0,
            "stop_loss_pct": 100.0,
            "stop_gain_value": 0.0,
            "stop_loss_value": 0.0,
            "meta_progress": 0.0,
            "loss_progress": 0.0,

            # Strategy
            "setup_name": "N/A",
            "setup_display": "N/A",
            "baixos_consecutivos": 0,
            "martingale_active": False,
            "dobra_atual": 0,
            "max_dobras": 0,
            "n_cycles": 1,
            "cycle_info": None,
            "bets_by_cycle": [],
            "pending_swap": None,

            # Stats
            "total_sequences": 0,
            "total_wins": 0,
            "total_breaks": 0,
            "total_profit": 0.0,
            "wins_by_dobra": {},
            "meta_reached": False,

            # WS
            "ws_connected": False,
            "ws_phase": "unknown",
            "ws_frames": 0,
            "ws_rounds": 0,
            "ws_errors": 0,
            "ws_uptime": 0.0,
            "ws_last_frame": 0.0,

            # History
            "explosion_history": [],

            # UI
            "last_action": "",
            "premium_status": "REGULAR",
            "premium_hours_today": [],
        }

    def update(self, key: str, value: Any) -> None:
        """Update a single state value (thread-safe)."""
        with self._lock:
            self._data[key] = value

    def update_many(self, updates: Dict[str, Any]) -> None:
        """Update multiple state values atomically (thread-safe)."""
        with self._lock:
            self._data.update(updates)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a single value (thread-safe)."""
        with self._lock:
            return self._data.get(key, default)

    def snapshot(self) -> Dict[str, Any]:
        """Return a full copy of the state (thread-safe)."""
        with self._lock:
            return dict(self._data)


# Global singleton
_state: Optional[BotState] = None


def get_state() -> BotState:
    """Get or create the global BotState singleton."""
    global _state
    if _state is None:
        _state = BotState()
    return _state


def reset_state() -> BotState:
    """Reset the global state (for new sessions)."""
    global _state
    _state = BotState()
    return _state
