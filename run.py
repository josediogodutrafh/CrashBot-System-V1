#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crash_AI - Entry Point Principal
Execute: python run.py
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto está no sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.gui.app import main

if __name__ == "__main__":
    main()
