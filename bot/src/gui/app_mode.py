#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
APP MODE - Configuracao de modo em runtime.
"""

from typing import Dict, List, Tuple

from src.bot.setups import (
    BaseSetup,  # noqa: F401
    SETUP_LIST,
    SETUP_DISPLAY_NAMES,
    get_setup,  # noqa: F401
    get_display_name,  # noqa: F401
)

_current_mode: str = "commercial"


def set_mode(mode: str) -> None:
    global _current_mode
    _current_mode = mode


def get_mode() -> str:
    return _current_mode


def get_setup_list() -> List[str]:
    return SETUP_LIST


def get_display_names() -> Dict[str, str]:
    return dict(SETUP_DISPLAY_NAMES)


def get_setup_buttons() -> List[Tuple[str, str]]:
    return [
        ("F1 Agress", "agressivo"),
        ("F2 Moder", "moderado"),
        ("F3 Conserv", "conservador"),
    ]


def get_title() -> str:
    return "CrashBot v3.1"
