"""
WS Parsers - Adaptadores de protocolo por plataforma.
"""

from src.ws.parsers.base import BaseParser, ParsedEvent  # noqa: F401
from src.ws.parsers.brabet import BrabetParser
from src.ws.parsers.sevenbra import SevenBraParser
from src.ws.parsers.k813bet import K813BetParser
from src.ws.parsers.spbetl import SPBetlParser
from src.ws.parsers.insbet import InsBetParser

PARSERS = {
    "brabet": BrabetParser,
    "7bra": SevenBraParser,
    "k813bet": K813BetParser,
    "spbetl": SPBetlParser,
    "insbet": InsBetParser,
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
