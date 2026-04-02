#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false

"""
CRASHBOT v3.0 - CALIBRATION MODULE

Sistema de calibração visual para configurar regiões de captura
e pontos de clique na tela do jogo.

Uso:
    from calibration import CalibrationWindow, ProfileManager

    # Abrir janela de calibração
    calibrator = CalibrationWindow()
    calibrator.show()

    # Ou gerenciar perfis diretamente
    manager = ProfileManager()
    profile = manager.load("brabet")
    manager.save(profile)
"""

from __future__ import annotations

# Main Window
from calibration.calibrator_window import CalibratorWindow, launch_calibrator

# Live Preview
from calibration.live_preview import LivePreview, ReadingResult

# Profile Manager
from calibration.profile_manager import (
    CalibrationProfile,
    ProfileManager,
    get_profile_manager,
)

# Region Selector
from calibration.region_selector import RegionSelector, SelectionMode, SelectionResult

__all__ = [
    # Profile Manager
    "CalibrationProfile",
    "ProfileManager",
    "get_profile_manager",
    # Region Selector
    "RegionSelector",
    "SelectionMode",
    "SelectionResult",
    # Live Preview
    "LivePreview",
    "ReadingResult",
    # Main Window
    "CalibratorWindow",
    "launch_calibrator",
]

__version__ = "3.0.0"
