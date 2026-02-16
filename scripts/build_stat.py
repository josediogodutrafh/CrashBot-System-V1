"""
Crash_AI - Build Script ESTATISTICO (Flet + PyInstaller)
Empacota o bot estatistico em TucunareBotStat.exe.

Identico ao build.py mas usa run_stat.py como entry point
e inclui os modulos estatisticos.

Uso:
    python scripts/build_stat.py          # Build completo
    python scripts/build_stat.py --test   # Apenas testa imports
    python scripts/build_stat.py --dist   # Build + distribuicao
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"

ENTRY_POINT = PROJECT_ROOT / "run_stat.py"
ICON_PATH = PROJECT_ROOT / "tools" / "icone.ico"

VERSION = "3.1.0-stat"
EXE_NAME = "TucunareBotStat"

DATA_INCLUDES = [
    ("config", "config"),
    ("tools/Tesseract-OCR", "tools/Tesseract-OCR"),
    ("src/vision/templates", "src/vision/templates"),
    ("tools/icone.ico", "tools/icone.ico"),
    ("tools/abrir_chrome_debug.bat", "tools/abrir_chrome_debug.bat"),
]

HIDDEN_IMPORTS = [
    "src.gui.panels.header",
    "src.gui.panels.financial",
    "src.gui.panels.strategy",
    "src.gui.panels.stats",
    "src.gui.panels.history",
    "src.gui.panels.controls",
    "src.gui.panels.config",
    "src.gui.state",
    "src.gui.theme",
    "src.gui.app_mode",
    "src.bot.controller",
    "src.bot.calibration",
    "src.bot.strategy",
    "src.bot.bankroll",
    "src.bot.setups",
    "src.bot.setups_stat",
    "src.bot.schedule",
    "src.bot.menu",
    "src.ws.capture",
    "src.data.manager",
    "src.notifications.telegram",
    "src.security.hwid",
    "src.security.license",
    "src.config",
    "websocket",
    "pyautogui",
    "pyperclip",
    "pynput",
    "pynput.keyboard",
    "pynput.keyboard._win32",
    "pynput.mouse",
    "pynput.mouse._win32",
    "pytz",
    "PIL",
    "PIL.Image",
    "yaml",
    "dateutil",
    "tkinter",
    "flet",
    "flet.canvas",
    "flet_desktop",
]

EXCLUDE_MODULES = [
    "torch",
    "torchvision",
    "torchaudio",
    "scipy",
    "sklearn",
    "scikit-learn",
    "statsmodels",
    "ruptures",
    "hmmlearn",
    "duckdb",
    "polars",
    "plotly",
    "dash",
    "dash_bootstrap_components",
    "matplotlib",
    "cv2",
    "easyocr",
    "skimage",
    "rich",
    "dearpygui",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "sphinx",
    "pygments",
    "docutils",
    "pdbpp",
]


def test_imports():
    """Testa imports do bot estatistico."""
    print("=" * 60)
    print("TESTANDO IMPORTS (STAT)")
    print("=" * 60)

    tests = [
        ("App mode", "from src.gui.app_mode import set_mode, get_mode"),
        ("Setups stat", "from src.bot.setups_stat import STAT_SETUP_LIST, get_stat_setup"),
        ("GUI app", "from src.gui.app import main"),
        ("GUI state", "from src.gui.state import get_state, BotState"),
        ("GUI theme", "from src.gui.theme import BG_MAIN, card_container"),
        ("Flet", "import flet as ft"),
        ("WebSocket capture", "from src.ws.capture import CrashWSCapture, GamePhase"),
        ("Strategy engine", "from src.bot.strategy import StrategyEngine"),
        ("Bankroll manager", "from src.bot.bankroll import BankrollManager"),
        ("Database manager", "from src.data.manager import DatabaseManager"),
        ("Telegram", "from src.notifications.telegram import notify_session_summary"),
        ("HWID", "from src.security.hwid import get_hwid"),
        ("Config", "from src.config import PROJECT_ROOT, API_URL"),
        ("Setups", "from src.bot.setups import SETUP_LIST, BaseSetup"),
        ("Schedule", "from src.bot.schedule import ScheduleManager"),
        ("PyAutoGUI", "import pyautogui"),
        ("Requests", "import requests"),
        ("WebSocket", "import websocket"),
        ("PyTZ", "import pytz"),
        ("PyInstaller", "import PyInstaller"),
    ]

    ok = 0
    fail = 0
    for name, stmt in tests:
        try:
            exec(stmt)
            print(f"  [OK] {name}")
            ok += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            fail += 1

    print(f"\nResultado: {ok} OK, {fail} FAIL")
    return fail == 0


def build():
    """Executa o build do bot estatistico."""
    print("=" * 60)
    print(f"{EXE_NAME} v{VERSION} - FLET BUILD")
    print("=" * 60)

    if DIST_DIR.exists():
        print(f"Limpando {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    try:
        import PyInstaller.__main__
        from flet_cli.__pyinstaller.utils import copy_flet_bin
        import flet_cli.__pyinstaller.config as hook_config
    except ImportError as e:
        print(f"ERRO: Dependencia nao encontrada: {e}")
        print("  pip install flet pyinstaller")
        return False

    print("\n[1/4] Copiando Flet runtime...")
    hook_config.temp_bin_dir = copy_flet_bin()

    if hook_config.temp_bin_dir is not None:
        fletd_path = os.path.join(hook_config.temp_bin_dir, "fletd.exe")
        if os.path.exists(fletd_path):
            os.remove(fletd_path)

        exe_path = os.path.join(hook_config.temp_bin_dir, "flet", "flet.exe")
        if os.path.exists(exe_path) and ICON_PATH.exists():
            try:
                from flet_cli.__pyinstaller.win_utils import (
                    update_flet_view_icon,
                    update_flet_view_version_info,
                )
                update_flet_view_icon(exe_path, str(ICON_PATH))
                update_flet_view_version_info(
                    exe_path,
                    product_name=EXE_NAME,
                    file_description=f"{EXE_NAME} - Statistical Crash Bot",
                    product_version=VERSION,
                    file_version=f"{VERSION}.0",
                    company_name="TucunareBot",
                    copyright="",
                )
                print(f"  Icone atualizado em flet.exe")
            except Exception as e:
                print(f"  AVISO: Nao foi possivel atualizar icone: {e}")
        print(f"  Flet runtime copiado: OK")
    else:
        print("  AVISO: Flet runtime nao encontrado, continuando...")

    print(f"\n[2/4] Configurando PyInstaller...")

    sep = ";" if sys.platform == "win32" else ":"

    pyi_args = [
        str(ENTRY_POINT),
        "--noconfirm",
        "--noconsole",
        "--onefile",
        "--name", EXE_NAME,
        "--distpath", str(DIST_DIR),
    ]

    if ICON_PATH.exists():
        pyi_args.extend(["--icon", str(ICON_PATH)])

    for src_rel, dst_rel in DATA_INCLUDES:
        src_path = PROJECT_ROOT / src_rel
        if src_path.exists():
            pyi_args.extend(["--add-data", f"{src_path}{sep}{dst_rel}"])
            print(f"  + dados: {src_rel}")

    for mod in HIDDEN_IMPORTS:
        pyi_args.extend(["--hidden-import", mod])
    print(f"  + {len(HIDDEN_IMPORTS)} hidden imports")

    for mod in EXCLUDE_MODULES:
        pyi_args.extend(["--exclude-module", mod])
    print(f"  - {len(EXCLUDE_MODULES)} modulos excluidos")

    pyi_args.extend(["--version-file", _create_version_file()])

    print(f"\n[3/4] Compilando... (pode levar 5-15 minutos)")
    print(f"  Entry: {ENTRY_POINT}")
    print(f"  Output: {DIST_DIR / f'{EXE_NAME}.exe'}")

    try:
        PyInstaller.__main__.run(pyi_args)
    except SystemExit as e:
        if e.code != 0:
            print(f"\nBUILD FALHOU (exit code: {e.code})")
            return False
    finally:
        if hook_config.temp_bin_dir and os.path.exists(hook_config.temp_bin_dir):
            shutil.rmtree(hook_config.temp_bin_dir, ignore_errors=True)

    print(f"\n[4/4] Verificando...")
    exe_path = DIST_DIR / f"{EXE_NAME}.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  BUILD OK!")
        print(f"  Arquivo: {exe_path}")
        print(f"  Tamanho: {size_mb:.1f} MB")
        return True
    else:
        for exe in DIST_DIR.rglob(f"{EXE_NAME}.exe"):
            size_mb = exe.stat().st_size / (1024 * 1024)
            print(f"\n  BUILD OK!")
            print(f"  Encontrado em: {exe} ({size_mb:.1f} MB)")
            return True

        print("\nBuild concluido mas .exe nao encontrado.")
        return False


def _create_version_file() -> str:
    """Cria arquivo de version info para o Windows."""
    ver = VERSION.replace("-stat", "")
    parts = ver.split(".")
    major = parts[0] if len(parts) > 0 else "0"
    minor = parts[1] if len(parts) > 1 else "0"
    patch = parts[2] if len(parts) > 2 else "0"

    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'TucunareBot'),
         StringStruct(u'FileDescription', u'{EXE_NAME} - Statistical Crash Bot'),
         StringStruct(u'FileVersion', u'{VERSION}.0'),
         StringStruct(u'InternalName', u'{EXE_NAME}'),
         StringStruct(u'OriginalFilename', u'{EXE_NAME}.exe'),
         StringStruct(u'ProductName', u'{EXE_NAME}'),
         StringStruct(u'ProductVersion', u'{VERSION}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    version_file = BUILD_DIR / "version_info_stat.txt"
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    version_file.write_text(content, encoding="utf-8")
    return str(version_file)


def create_distribution():
    """Cria pasta de distribuicao com .exe + dados."""
    print("\n" + "=" * 60)
    print("CRIANDO DISTRIBUICAO (STAT)")
    print("=" * 60)

    dist_package = DIST_DIR / f"{EXE_NAME}-v{VERSION}"
    dist_package.mkdir(parents=True, exist_ok=True)

    exe_path = DIST_DIR / f"{EXE_NAME}.exe"
    if not exe_path.exists():
        for exe in DIST_DIR.rglob(f"{EXE_NAME}.exe"):
            exe_path = exe
            break
        else:
            print(f"ERRO: {EXE_NAME}.exe nao encontrado.")
            return False

    shutil.copy2(exe_path, dist_package / f"{EXE_NAME}.exe")

    bat_content = f'@echo off\ntitle {EXE_NAME} v{VERSION}\ncd /d "%~dp0"\n{EXE_NAME}.exe\npause\n'
    (dist_package / "iniciar.bat").write_text(bat_content)

    chrome_bat = PROJECT_ROOT / "tools" / "abrir_chrome_debug.bat"
    if chrome_bat.exists():
        shutil.copy2(chrome_bat, dist_package / "abrir_chrome_debug.bat")

    config_dir = dist_package / "config"
    config_dir.mkdir(exist_ok=True)

    env_template = (
        "# CrashBot Stat - Configuracao\n"
        "# Preencha com seus dados\n\n"
        "TELEGRAM_BOT_TOKEN=\n"
        "TELEGRAM_CHAT_ID=\n"
        "API_URL=https://crash-api-jose.onrender.com\n"
    )
    (config_dir / ".env").write_text(env_template)

    (dist_package / "data" / "db").mkdir(parents=True, exist_ok=True)

    print(f"Distribuicao criada: {dist_package}")
    print("Conteudo:")
    total_size = 0
    for item in sorted(dist_package.rglob("*")):
        if item.is_file():
            rel = item.relative_to(dist_package)
            sz = item.stat().st_size
            total_size += sz
            if sz > 1024 * 1024:
                print(f"  {rel} ({sz / 1024 / 1024:.1f} MB)")
            else:
                print(f"  {rel}")

    print(f"\nTotal: {total_size / 1024 / 1024:.1f} MB")
    return True


def main():
    parser = argparse.ArgumentParser(description=f"{EXE_NAME} v{VERSION} Build Script")
    parser.add_argument("--test", action="store_true", help="Apenas testa imports")
    parser.add_argument("--dist", action="store_true", help="Cria pacote de distribuicao")
    args = parser.parse_args()

    os.chdir(str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT))

    if args.test:
        success = test_imports()
        sys.exit(0 if success else 1)

    if not test_imports():
        print("\nIMPORTS FALHARAM - corrija antes de compilar.")
        sys.exit(1)

    if not build():
        sys.exit(1)

    if args.dist:
        create_distribution()

    print("\n" + "=" * 60)
    print("CONCLUIDO!")
    print("=" * 60)


if __name__ == "__main__":
    main()
