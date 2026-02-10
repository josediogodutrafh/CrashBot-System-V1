#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SETUPS DE JOGO
==============

7 setups de martingale com notacao de ciclos (+):
- 1/2                  Conservador  (banca/3, 2 dobras)
- 1/2 + 1/2            Moderado     (banca/6, 4 dobras)
- 1/2 + 1/2 + 1/2      Resistente   (banca/9, 6 dobras)
- 1/2/4                Equilibrado  (banca/7, 3 dobras)
- 1/2/4 + 1/2/4        Duplo        (banca/14, 6 dobras)
- 1/2/4/8              Agressivo    (banca/15, 4 dobras)
- 1/2/4/8/16           Ultra        (banca/31, 5 dobras)

Conceito:
- "/" separa dobras dentro de um ciclo
- "+" separa ciclos (reinicia a progressao)
- Se perdeu todos os ciclos -> BREAK (perdeu a banca)
"""

import logging
from abc import ABC
from typing import Dict, List

logger = logging.getLogger(__name__)


class BaseSetup(ABC):
    """Classe base para todos os setups de jogo."""

    name: str = ""
    _cycles: List[List[int]] = []

    @property
    def cycles(self) -> List[List[int]]:
        return self._cycles

    @property
    def pattern(self) -> List[int]:
        """Sequencia plana de multiplicadores."""
        return [m for cycle in self.cycles for m in cycle]

    @property
    def divisor(self) -> int:
        """Soma total dos multiplicadores (para calcular unit)."""
        return sum(self.pattern)

    @property
    def max_dobras(self) -> int:
        return len(self.pattern)

    @property
    def n_cycles(self) -> int:
        return len(self.cycles)

    def calculate_unit(self, banca: float) -> float:
        """Calcula o valor da unidade base."""
        return banca / self.divisor

    def get_bet(self, position: int, banca: float) -> float:
        """Retorna o valor da aposta para a posicao (0-based)."""
        if position < 0 or position >= self.max_dobras:
            return 0.0
        unit = self.calculate_unit(banca)
        return max(1.0, round(unit * self.pattern[position], 2))

    def get_all_bets(self, banca: float) -> Dict[int, float]:
        """Retorna tabela completa de apostas {dobra_1based: valor}."""
        unit = self.calculate_unit(banca)
        return {
            i + 1: max(1.0, round(unit * p, 2))
            for i, p in enumerate(self.pattern)
        }

    def get_position_info(self, position: int) -> dict:
        """Retorna info de ciclo para uma posicao (0-based)."""
        pos = 0
        for ci, cycle in enumerate(self.cycles):
            if position < pos + len(cycle):
                return {
                    "cycle": ci + 1,
                    "total_cycles": self.n_cycles,
                    "pos_in_cycle": position - pos + 1,
                    "cycle_size": len(cycle),
                }
            pos += len(cycle)
        return {
            "cycle": self.n_cycles,
            "total_cycles": self.n_cycles,
            "pos_in_cycle": 1,
            "cycle_size": 1,
        }

    def get_bets_by_cycle(self, banca: float) -> List[dict]:
        """Retorna apostas agrupadas por ciclo."""
        unit = self.calculate_unit(banca)
        result = []
        global_pos = 0
        for ci, cycle in enumerate(self.cycles):
            for di, mult in enumerate(cycle):
                value = max(1.0, round(unit * mult, 2))
                result.append({
                    "cycle": ci + 1,
                    "pos_in_cycle": di + 1,
                    "global_pos": global_pos + 1,
                    "multiplier": mult,
                    "value": value,
                    "baixas": 6 + global_pos,
                })
                global_pos += 1
        return result

    def get_description(self) -> str:
        """Descricao legivel do setup."""
        n = self.n_cycles
        ciclo_str = f"{n} ciclo{'s' if n > 1 else ''}"
        return (
            f"{self.name} (banca/{self.divisor}, "
            f"{self.max_dobras} dobras, {ciclo_str})"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} '{self.name}'>"


# ==============================================================================
# SETUPS CONCRETOS
# ==============================================================================

class Setup12(BaseSetup):
    """1/2 - Conservador: 2 dobras, bust rapido, unit grande."""
    name = "1/2"
    _cycles = [[1, 2]]


class Setup12_12(BaseSetup):
    """1/2 + 1/2 - Moderado: 4 dobras em 2 ciclos."""
    name = "1/2 + 1/2"
    _cycles = [[1, 2], [1, 2]]


class Setup12_12_12(BaseSetup):
    """1/2 + 1/2 + 1/2 - Resistente: 6 dobras em 3 ciclos."""
    name = "1/2 + 1/2 + 1/2"
    _cycles = [[1, 2], [1, 2], [1, 2]]


class Setup124(BaseSetup):
    """1/2/4 - Equilibrado: 3 dobras, padrao classico."""
    name = "1/2/4"
    _cycles = [[1, 2, 4]]


class Setup124_124(BaseSetup):
    """1/2/4 + 1/2/4 - Duplo: 6 dobras em 2 ciclos."""
    name = "1/2/4 + 1/2/4"
    _cycles = [[1, 2, 4], [1, 2, 4]]


class Setup1248(BaseSetup):
    """1/2/4/8 - Agressivo: 4 dobras, unit menor."""
    name = "1/2/4/8"
    _cycles = [[1, 2, 4, 8]]


class Setup124816(BaseSetup):
    """1/2/4/8/16 - Ultra: 5 dobras, unit minima."""
    name = "1/2/4/8/16"
    _cycles = [[1, 2, 4, 8, 16]]


# ==============================================================================
# SETUP INTELIGENTE (adapta ao contexto - mantido para compatibilidade)
# ==============================================================================

class SetupInteligente(BaseSetup):
    """Adapta agressividade ao horario premium."""
    name = "Inteligente"
    _cycles = [[1, 2, 4]]  # default

    def __init__(self):
        self._inner_setup: BaseSetup = Setup124()

    @property
    def cycles(self) -> List[List[int]]:
        return self._inner_setup.cycles

    def adapt(self, is_premium: bool, premium_strength: str = "normal"):
        if is_premium and premium_strength == "strong":
            self._inner_setup = Setup12()
        elif is_premium:
            self._inner_setup = Setup124()
        else:
            self._inner_setup = Setup1248()
        logger.debug(
            f"Inteligente adaptado -> {self._inner_setup.name} "
            f"(premium={is_premium}, strength={premium_strength})"
        )

    def get_description(self) -> str:
        inner = self._inner_setup.name
        return f"Inteligente (atual: {inner}, adapta ao horario)"


# ==============================================================================
# REGISTRO E FACTORY
# ==============================================================================

AVAILABLE_SETUPS = {
    "1/2": Setup12,
    "1/2 + 1/2": Setup12_12,
    "1/2 + 1/2 + 1/2": Setup12_12_12,
    "1/2/4": Setup124,
    "1/2/4 + 1/2/4": Setup124_124,
    "1/2/4/8": Setup1248,
    "1/2/4/8/16": Setup124816,
}

# Lista ordenada para menus
SETUP_LIST = list(AVAILABLE_SETUPS.keys())

# Nomes comerciais para exibicao ao usuario
SETUP_DISPLAY_NAMES = {
    "1/2":                "Conservador",
    "1/2 + 1/2":          "Moderado",
    "1/2 + 1/2 + 1/2":   "Resistente",
    "1/2/4":              "Equilibrado",
    "1/2/4 + 1/2/4":     "Duplo",
    "1/2/4/8":            "Agressivo",
    "1/2/4/8/16":         "Ultra",
    "Inteligente":        "Automatico",
}


def get_display_name(setup_name: str) -> str:
    """Retorna o nome comercial de um setup."""
    return SETUP_DISPLAY_NAMES.get(setup_name, setup_name)


def get_setup(name: str) -> BaseSetup:
    """Retorna instancia do setup pelo nome."""
    cls = AVAILABLE_SETUPS.get(name)
    if cls:
        return cls()
    if name == "Inteligente":
        return SetupInteligente()
    raise ValueError(
        f"Setup '{name}' nao encontrado. "
        f"Disponiveis: {list(AVAILABLE_SETUPS.keys())}"
    )
