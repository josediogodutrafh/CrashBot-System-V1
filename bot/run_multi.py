#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crash Lab - Modo Multi-Plataforma (Cérebro)
Execute: python run_multi.py

Abre dashboard para 5 plataformas simultâneas:
  - Brabet   (porta 9222)
  - 7Bra     (porta 9224)
  - K813Bet  (porta 9225)
  - SPBetl   (porta 9226)
  - InsBet   (porta 9227)
"""

import os
import sys
from pathlib import Path

# PyInstaller com console=False define sys.stdout/stderr como None,
# o que quebra uvicorn/logging. Redirecionar para devnull.
if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

# Garante que a raiz do projeto está no sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["APP_MODE"] = "multi"

from src.gui.app_multi import main

if __name__ == "__main__":
    main()
