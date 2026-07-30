"""
Parser InsBet - Adaptador de protocolo WebSocket para plataforma InsBet.

Herda do BrabetParser pois provavelmente usa o mesmo motor de jogo (white-label).
Se o protocolo for diferente, ative recording para capturar frames
e implemente parse_frame() customizado.
"""

import logging
from typing import List

from src.ws.parsers.brabet import BrabetParser

logger = logging.getLogger(__name__)


class InsBetParser(BrabetParser):
    """Parser InsBet — herda protocolo Brabet (mesmo motor de jogo)."""

    @property
    def platform_name(self) -> str:
        return "insbet"

    @property
    def game_tab_keywords(self) -> List[str]:
        return ["insbet", "crash"]

    @property
    def game_url(self) -> str:
        return ""

    # parse_frame herdado do BrabetParser (mesmo protocolo)
