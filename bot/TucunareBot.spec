# -*- mode: python ; coding: utf-8 -*-
"""
TucunaréBot v3.0 - PyInstaller Build Spec
Exclui torch/ML para manter o executável leve.
"""

import sys
from pathlib import Path

block_cipher = None

# Diretório base
base_dir = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(base_dir)],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        # GUI
        'dearpygui',
        'dearpygui.dearpygui',
        # Vision
        'cv2',
        'numpy',
        'pytesseract',
        'mss',
        'mss.tools',
        'PIL',
        'PIL.Image',
        # Automação
        'pyautogui',
        # HTTP
        'requests',
        'urllib3',
        # Core
        'pydantic',
        'pydantic.main',
        'colorama',
        'tqdm',
        # Interno
        'core',
        'core.constants',
        'core.events',
        'core.state',
        'engine',
        'engine.vision',
        'engine.vision.capture',
        'engine.vision.detector',
        'engine.vision.ocr',
        'engine.vision.templates',
        'engine.strategy',
        'engine.strategy.trigger',
        'engine.strategy.martingale',
        'engine.trading',
        'engine.trading.executor',
        'gui',
        'gui.main_window',
        'gui.components',
        'gui.theme',
        'calibration',
        'calibration.profile_manager',
        'calibration.calibrator_window',
        'services',
        'services.licensing',
        'services.telemetry',
        'services.database',
        'services.notifications',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Excluir ML pesado para manter leve
    excludes=[
        'torch', 'torchvision', 'torchaudio',
        'stable_baselines3', 'gymnasium', 'gym',
        'optuna', 'pandas', 'scipy', 'sklearn', 'scikit-learn',
        'matplotlib', 'seaborn', 'plotly',
        'jupyter', 'notebook', 'ipykernel',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TucunareBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Janelado (sem console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
