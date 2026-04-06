"""
Parser Winbra - Adaptador de protocolo WebSocket para plataforma Winbra.

Herda do BrabetParser pois provavelmente usa o mesmo motor de jogo.
"""

import logging
from typing import List

from src.ws.parsers.brabet import BrabetParser

logger = logging.getLogger(__name__)


class WinbraParser(BrabetParser):
    """Parser Winbra — herda protocolo Brabet (mesmo motor de jogo)."""

    @property
    def platform_name(self) -> str:
        return "winbra"

    @property
    def game_tab_keywords(self) -> List[str]:
        return ["winbra", "win.bra", "crash"]

    @property
    def game_url(self) -> str:
        return ""

    # parse_frame herdado do BrabetParser (mesmo protocolo)
