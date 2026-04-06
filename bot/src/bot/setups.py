#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SETUPS DE JOGO - Martingale Classico
=====================================

3 modos com banca fixa (usuario define quanto arriscar):

Agressivo:    1x, 2x         (2 bets, divisor 3)
Moderado:     1x, 2x, 4x     (3 bets, divisor 7)
Conservador:  1x, 2x, 4x, 8x (4 bets, divisor 15)

Bet base = banca / divisor
Trigger: 6 LOWs consecutivos (< 2.0x)
"""

import logging
from abc import ABC
from typing import List

logger = logging.getLogger(__name__)


class BaseSetup(ABC):
    """Classe base para setups de jogo."""

    name: str = ""
    pattern: List[int] = []
    threshold: float = 2.0
    trigger_base: int = 6

    @property
    def divisor(self) -> int:
        """Soma dos multiplicadores."""
        return sum(self.pattern)

    @property
    def max_dobras(self) -> int:
        return len(self.pattern)

    def get_bet(self, dobra: int, banca: float) -> float:
        """Valor da aposta para a dobra (0-based).

        Args:
            dobra: Indice da dobra (0, 1, 2, 3).
            banca: Valor fixo da banca.
        """
        if dobra < 0 or dobra >= len(self.pattern):
            return 0.0
        unit = banca / self.divisor
        return max(1.0, round(unit * self.pattern[dobra], 2))

    def get_all_bets(self, banca: float) -> dict:
        """Tabela completa {dobra: valor}."""
        unit = banca / self.divisor
        return {
            i + 1: max(1.0, round(unit * m, 2))
            for i, m in enumerate(self.pattern)
        }

    def get_description(self) -> str:
        prog = "/".join(str(m) for m in self.pattern)
        return (
            f"{self.name} ({prog}, "
            f"banca/{self.divisor})"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} '{self.name}'>"


# ============================================================
# 3 MODOS
# ============================================================

class SetupAgressivo(BaseSetup):
    """Agressivo: 2 bets (1x, 2x). Banca/3."""
    name = "agressivo"
    pattern = [1, 2]


class SetupModerado(BaseSetup):
    """Moderado: 3 bets (1x, 2x, 4x). Banca/7."""
    name = "moderado"
    pattern = [1, 2, 4]


class SetupConservador(BaseSetup):
    """Conservador: 4 bets (1x, 2x, 4x, 8x). Banca/15."""
    name = "conservador"
    pattern = [1, 2, 4, 8]


# ============================================================
# REGISTRO E FACTORY
# ============================================================

AVAILABLE_SETUPS = {
    "agressivo": SetupAgressivo,
    "moderado": SetupModerado,
    "conservador": SetupConservador,
}

SETUP_LIST = list(AVAILABLE_SETUPS.keys())

SETUP_DISPLAY_NAMES = {
    "agressivo": "Agressivo (1/2)",
    "moderado": "Moderado (1/2/4)",
    "conservador": "Conservador (1/2/4/8)",
}


def get_display_name(setup_name: str) -> str:
    """Retorna nome de exibicao."""
    return SETUP_DISPLAY_NAMES.get(
        setup_name, setup_name
    )


def get_setup(name: str = "moderado") -> BaseSetup:
    """Retorna instancia do setup pelo nome."""
    cls = AVAILABLE_SETUPS.get(name)
    if cls:
        return cls()
    return SetupModerado()
