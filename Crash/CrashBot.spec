# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src\\bot_controller.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        # Tesseract-OCR (engine de OCR)
        ('Tesseract-OCR', 'Tesseract-OCR'),
        
        # Modelos de Machine Learning
        ('models\\crash_classifier.pkl', 'models'),
        ('models\\data_scaler.pkl', 'models'),
        
        # Templates de visão
        ('src\\vision\\templates\\templates_debug', 'src\\vision\\templates\\templates_debug'),
        ('src\\vision\\templates\\template_saldo', 'src\\vision\\templates\\template_saldo'),
    ],
    hiddenimports=[
        'sklearn.ensemble._forest',
        'sklearn.tree._classes',
        'sklearn.neighbors._typedefs',
        'sklearn.utils._cython_blas',
        'sklearn.utils._typedefs',
        'scipy.special._cdflib',
        'pytesseract',
        'cv2',
        'numpy',
        'mss',
        'pyautogui',
        'pyperclip',
        'rich',
        'requests',
        'winsound',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icone.ico'],
)