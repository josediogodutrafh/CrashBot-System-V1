"""
Parser PGWin - Adaptador de protocolo WebSocket para plataforma PGWin.

Herda do BrabetParser pois provavelmente usa o mesmo motor de jogo.
"""

import logging
from typing import List

from src.ws.parsers.brabet import BrabetParser

logger = logging.getLogger(__name__)


class PGWinParser(BrabetParser):
    """Parser PGWin — herda protocolo Brabet (mesmo motor de jogo)."""

    @property
    def platform_name(self) -> str:
        return "pgwin"

    @property
    def game_tab_keywords(self) -> List[str]:
        return ["pgwin", "pg.win", "crash"]

    @property
    def game_url(self) -> str:
        return ""

    # parse_frame herdado do BrabetParser (mesmo protocolo)
