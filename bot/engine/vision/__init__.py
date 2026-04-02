#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - ENGINE VISION MODULE

Sistema de visão computacional para detecção de elementos do jogo.

Módulos:
- capture: Captura de tela usando mss
- templates: Reconhecimento por template matching
- ocr: Leitura de texto (fallback)
- detector: Orquestrador principal

Uso:
    from engine.vision import get_detector, get_capture, get_templates

    # Detector completo (recomendado)
    detector = get_detector()
    detector.load_profile_from_config("Monitor 1")
    detector.load_templates("assets/templates")

    mult = detector.read_multiplier()
    balance = detector.read_balance()
    is_bet_open = detector.is_bet_window_open()

    # Ou componentes individuais
    capture = get_capture()
    templates = get_templates()
"""

# Capture
from engine.vision.capture import (
    CaptureRegion,
    ScreenCapture,
    get_capture,
    reset_capture,
)

# Detector (orquestrador)
from engine.vision.detector import (
    DetectionResult,
    GameDetector,
    ScreenProfile,
    get_detector,
    reset_detector,
)

# OCR (fallback)
from engine.vision.ocr import OCRBackend, OCREngine, PreprocessMode, get_ocr, reset_ocr

# Templates
from engine.vision.templates import (
    DigitTemplate,
    TemplateEngine,
    TemplateMatch,
    TemplateSet,
    get_templates,
    reset_templates,
)

__all__ = [
    # Capture
    "ScreenCapture",
    "CaptureRegion",
    "get_capture",
    "reset_capture",
    # Templates
    "TemplateEngine",
    "TemplateSet",
    "TemplateMatch",
    "DigitTemplate",
    "get_templates",
    "reset_templates",
    # OCR
    "OCREngine",
    "OCRBackend",
    "PreprocessMode",
    "get_ocr",
    "reset_ocr",
    # Detector
    "GameDetector",
    "ScreenProfile",
    "DetectionResult",
    "get_detector",
    "reset_detector",
]
