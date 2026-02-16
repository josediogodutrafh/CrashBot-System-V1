#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
APP MODE - Configuracao de modo em runtime.

Define se a app esta rodando no modo "commercial" (setups originais)
ou "statistical" (setups baseados em analise estatistica).

Todos os panels da GUI chamam funcoes deste modulo para obter
listas de setups, nomes de exibicao, etc.
"""

from typing import Dict, List, Tuple

from src.bot.setups import (
    BaseSetup,
    SETUP_LIST,
    SETUP_DISPLAY_NAMES,
    get_setup as _get_commercial_setup,
    get_display_name as _get_commercial_display_name,
)
from src.bot.setups_stat import (
    STAT_SETUP_LIST,
    STAT_DISPLAY_NAMES,
    get_stat_setup as _get_stat_setup,
    get_stat_display_name as _get_stat_display_name,
)

# ==============================================================================
# ESTADO GLOBAL
# ==============================================================================

_current_mode: str = "commercial"


def set_mode(mode: str) -> None:
    """Define o modo da aplicacao ('commercial' ou 'statistical')."""
    global _current_mode
    if mode not in ("commercial", "statistical"):
        raise ValueError(f"Modo invalido: {mode}. Use 'commercial' ou 'statistical'.")
    _current_mode = mode


def get_mode() -> str:
    """Retorna o modo atual."""
    return _current_mode


# ==============================================================================
# RESOLUCAO DINAMICA
# ==============================================================================

def get_setup_list() -> List[str]:
    """Retorna lista de nomes internos dos setups do modo atual."""
    if _current_mode == "statistical":
        return STAT_SETUP_LIST
    return SETUP_LIST


def get_display_names() -> Dict[str, str]:
    """Retorna dict {nome_interno: nome_exibicao} do modo atual."""
    if _current_mode == "statistical":
        return dict(STAT_DISPLAY_NAMES)
    return dict(SETUP_DISPLAY_NAMES)


def get_display_name(setup_name: str) -> str:
    """Retorna nome de exibicao para um setup."""
    if _current_mode == "statistical":
        return _get_stat_display_name(setup_name)
    return _get_commercial_display_name(setup_name)


def get_setup(name: str) -> BaseSetup:
    """Retorna instancia do setup pelo nome (resolve pelo modo)."""
    if _current_mode == "statistical":
        return _get_stat_setup(name)
    return _get_commercial_setup(name)


def get_setup_buttons() -> List[Tuple[str, str]]:
    """Retorna lista de (label_botao, nome_interno) para os controles.

    Comercial: 7 setups com F1-F7
    Estatistico: 4 setups com F1-F4
    """
    if _current_mode == "statistical":
        return [
            ("F1 Flat", "flat_18"),
            ("F2 Kelly", "kelly_18"),
            ("F3 Moder", "moderado_18"),
            ("F4 Adapt", "adaptativo_18"),
        ]
    return [
        ("F1 Conserv", "1/2"),
        ("F2 Moder", "1/2 + 1/2"),
        ("F3 Resist", "1/2 + 1/2 + 1/2"),
        ("F4 Equil", "1/2/4"),
        ("F5 Duplo", "1/2/4 + 1/2/4"),
        ("F6 Agress", "1/2/4/8"),
        ("F7 Ultra", "1/2/4/8/16"),
    ]


def get_title() -> str:
    """Retorna titulo da janela para o modo atual."""
    if _current_mode == "statistical":
        return "TucunareBotStat v3.1 - Statistical Mode"
    return "CrashBot v3.1 - Crash Game Assistant"
