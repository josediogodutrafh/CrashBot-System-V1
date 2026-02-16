#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crash_AI - Entry Point Estatistico
Execute: python run_stat.py

Identico ao run.py mas ativa o modo "statistical" com 4 setups
baseados nas analises dos notebooks 11-13.
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto esta no sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ativar modo estatistico ANTES de importar a GUI
from src.gui.app_mode import set_mode
set_mode("statistical")

from src.gui.app import main

if __name__ == "__main__":
    main()
