"""
WS Parsers - Adaptadores de protocolo por plataforma.
"""

from src.ws.parsers.base import BaseParser, ParsedEvent  # noqa: F401
from src.ws.parsers.brabet import BrabetParser
from src.ws.parsers.onebra import OnebraParser
from src.ws.parsers.pgwin import PGWinParser
from src.ws.parsers.winbra import WinbraParser

PARSERS = {
    "brabet": BrabetParser,
    "onebra": OnebraParser,
    "pgwin": PGWinParser,
    "winbra": WinbraParser,
}


def get_parser(platform: str) -> BaseParser:
    """Retorna instancia do parser."""
    cls = PARSERS.get(platform.lower())
    if not cls:
        available = ", ".join(PARSERS.keys())
        raise ValueError(
            f"Parser '{platform}' nao encontrado. "
            f"Disponiveis: {available}"
        )
    return cls()


def get_platform_names() -> list:
    """Retorna nomes das plataformas."""
    return list(PARSERS.keys())
