#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SETUPS ESTATISTICOS
===================

4 setups baseados nas descobertas dos notebooks 11-13:
- Flat 1.8x:       Aposta fixa, target 1.80 (Sharpe 0.355, DD 5.6%)
- Kelly 1.8x:      Kelly fraction dinamico, target 1.80 (Sharpe 0.223, DD 8.8%)
- Moderado 1.8x:   Martingale 1/2+1/2 com target fixo 1.80
- Adaptativo 1.8x:  Martingale 1/2+1/2 com trigger dinamico

Herdam de BaseSetup e usam as propriedades estatisticas
(target_fixed, sizing_mode, adaptive_trigger, etc).
"""

import logging
from typing import Dict, List

from src.bot.setups import BaseSetup

logger = logging.getLogger(__name__)


# ==============================================================================
# SETUPS ESTATISTICOS
# ==============================================================================

class SetupFlat18(BaseSetup):
    """Flat 1.8x - Aposta fixa, sem martingale.

    Melhor Sharpe no backtest (0.355), menor drawdown (5.6%).
    Cada entrada usa banca/10 como aposta fixa.
    _cycles com 10 unidades para dar divisor=10 (aposta = 10% da banca).
    """
    name = "flat_18"
    _cycles = [[1] * 10]  # divisor=10, aposta = banca/10
    target_fixed = 1.80
    threshold = 2.0
    trigger_base = 6
    sizing_mode = "flat"


class SetupKelly18(BaseSetup):
    """Kelly 1.8x - Tamanho de aposta via Kelly criterion.

    Melhor Sharpe no torneio de estrategias (0.223), DD 8.8%.
    Calcula fraction otimo baseado em win-rate das ultimas N rodadas.
    _cycles com 10 unidades para dar divisor=10 (base para Kelly).
    """
    name = "kelly_18"
    _cycles = [[1] * 10]  # divisor=10, base para Kelly
    target_fixed = 1.80
    threshold = 2.0
    trigger_base = 6
    sizing_mode = "kelly"
    kelly_window = 100


class SetupModerado18(BaseSetup):
    """Moderado 1.8x - Martingale 1/2+1/2 com target fixo.

    Mesma progressao do setup comercial Moderado, mas com target
    fixo em 1.80x ao inves de aleatorio 1.90-2.05x.
    """
    name = "moderado_18"
    _cycles = [[1, 2], [1, 2]]
    target_fixed = 1.80
    threshold = 2.0
    trigger_base = 6
    sizing_mode = "martingale"


class SetupAdaptativo18(BaseSetup):
    """Adaptativo 1.8x - Martingale com trigger dinamico.

    Mesma progressao 1/2+1/2, mas ajusta o trigger (5-8 baixas)
    baseado na porcentagem de LOWs nas ultimas 200 rodadas.
    Mais LOWs -> entra mais cedo; menos LOWs -> espera mais.
    """
    name = "adaptativo_18"
    _cycles = [[1, 2], [1, 2]]
    target_fixed = 1.80
    threshold = 2.0
    trigger_base = 6
    sizing_mode = "martingale"
    adaptive_trigger = True
    adaptive_window = 200


# ==============================================================================
# REGISTRO E FACTORY
# ==============================================================================

STAT_SETUPS = {
    "flat_18": SetupFlat18,
    "kelly_18": SetupKelly18,
    "moderado_18": SetupModerado18,
    "adaptativo_18": SetupAdaptativo18,
}

STAT_SETUP_LIST = list(STAT_SETUPS.keys())

STAT_DISPLAY_NAMES = {
    "flat_18": "Flat 1.8x",
    "kelly_18": "Kelly 1.8x",
    "moderado_18": "Moderado 1.8x",
    "adaptativo_18": "Adaptativo 1.8x",
}


def get_stat_display_name(setup_name: str) -> str:
    """Retorna o nome de exibicao de um setup estatistico."""
    return STAT_DISPLAY_NAMES.get(setup_name, setup_name)


def get_stat_setup(name: str) -> BaseSetup:
    """Retorna instancia do setup estatistico pelo nome."""
    cls = STAT_SETUPS.get(name)
    if cls:
        return cls()
    raise ValueError(
        f"Setup estatistico '{name}' nao encontrado. "
        f"Disponiveis: {STAT_SETUP_LIST}"
    )
