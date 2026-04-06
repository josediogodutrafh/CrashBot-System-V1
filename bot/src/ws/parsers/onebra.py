"""
Parser Onebra - Adaptador de protocolo WebSocket para plataforma Onebra.

Herda do BrabetParser pois usa o mesmo motor de jogo (white-label).
Se o protocolo for diferente, os frames são gravados para análise.
"""

import logging
from typing import List

from src.ws.parsers.brabet import BrabetParser

logger = logging.getLogger(__name__)


class OnebraParser(BrabetParser):
    """Parser Onebra — herda protocolo Brabet (mesmo motor de jogo).

    Se o protocolo for diferente, ative recording para capturar frames
    e implemente parse_frame() customizado.
    """

    @property
    def platform_name(self) -> str:
        return "onebra"

    @property
    def game_tab_keywords(self) -> List[str]:
        return ["onebra", "1bra", "crash"]

    @property
    def game_url(self) -> str:
        return ""

    # parse_frame herdado do BrabetParser (mesmo protocolo)
    # Recording também herdado (BrabetParser.parse_frame já grava se ativo)
