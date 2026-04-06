"""
Base Parser - Interface que todo parser de plataforma deve implementar.

O parser recebe frames brutos do WebSocket e emite eventos padronizados
que o bot consome independente da plataforma.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ParsedEvent:
    """Evento padronizado emitido pelo parser."""

    __slots__ = ("event_type", "data")

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data

    def __repr__(self):
        return f"ParsedEvent({self.event_type}, {self.data})"


# Tipos de evento padronizados:
#   "round_end"      -> {"crash": float, "round_id": int, "duration": int}
#   "betting_phase"   -> {"bet_left_seconds": int, "round_id": int}
#   "game_start"     -> {"round_id": int}
#   "balance_update" -> {"balance": float}
#   "bet_placed"     -> {"user": str, "amount": float, "round_id": int}
#   "cashout"        -> {"user": str, "multiplier": float, "profit": float}


class BaseParser(ABC):
    """Interface base para parsers de plataforma."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Nome da plataforma (ex: 'brabet', 'blaze')."""
        ...

    @property
    @abstractmethod
    def game_tab_keywords(self) -> List[str]:
        """Keywords para detectar a aba do jogo no Chrome."""
        ...

    @abstractmethod
    def parse_frame(self, payload: str, opcode: int = 1) -> List[ParsedEvent]:
        """Parseia um frame WS bruto e retorna lista de eventos padronizados.

        Args:
            payload: Conteúdo do frame (texto ou base64).
            opcode: 1=texto, 2=binário.

        Returns:
            Lista de ParsedEvent (pode ser vazia se frame não é relevante).
        """
        ...

    def reset(self):
        """Reseta estado interno do parser (novo round, reconexão, etc)."""
        pass
