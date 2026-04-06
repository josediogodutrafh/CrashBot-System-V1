#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crash Lab - Modo Multi-Plataforma (Cérebro)
Execute: python run_multi.py

Abre dashboard para 4 plataformas simultâneas:
  - Brabet  (porta 9222)
  - Onebra  (porta 9223)
  - PGWin   (porta 9224)
  - Winbra  (porta 9225)
"""

import os
import sys
from pathlib import Path

# Garante que a raiz do projeto está no sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["APP_MODE"] = "multi"

# Quando rodando como .exe (PyInstaller), apontar FLET_VIEW_PATH para o
# cliente Flet bundled, evitando download em runtime (que falha sem internet
# ou com problemas de SSL na máquina do cliente)
if getattr(sys, "frozen", False):
    bundle_dir = Path(sys._MEIPASS)
    flet_client_path = bundle_dir / "flet_desktop" / "app" / "flet"
    if flet_client_path.exists():
        os.environ["FLET_VIEW_PATH"] = str(flet_client_path)

from src.gui.app_multi import main

if __name__ == "__main__":
    main()
