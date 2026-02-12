"""
Crash_AI - Build Script (Flet + PyInstaller)
Empacota o bot em .exe usando PyInstaller com runtime Flet.

Replica o que 'flet pack' faz internamente, mas com controle total
sobre --exclude-module para evitar incluir torch, scipy, etc.

Uso:
    python scripts/build.py          # Build completo
    python scripts/build.py --test   # Apenas testa imports (sem compilar)
    python scripts/build.py --dist   # Build + cria pacote distribuicao

Requisitos:
    pip install flet pyinstaller
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

ENTRY_POINT = PROJECT_ROOT / "run.py"
ICON_PATH = PROJECT_ROOT / "tools" / "icone.ico"

VERSION = "3.1.0"

# Diretórios/arquivos de dados para incluir no build
# Formato: (source_relative, dest_relative)
DATA_INCLUDES = [
    ("config", "config"),
    ("tools/Tesseract-OCR", "tools/Tesseract-OCR"),
    ("src/vision/templates", "src/vision/templates"),
    ("tools/icone.ico", "tools/icone.ico"),
    ("tools/abrir_chrome_debug.bat", "tools/abrir_chrome_debug.bat"),
]

# Hidden imports que o PyInstaller pode nao detectar automaticamente
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
    "src.bot.controller",
    "src.bot.strategy",
    "src.bot.bankroll",
    "src.bot.setups",
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

# Módulos pesados a excluir (não usados pelo bot GUI)
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
]


def test_imports():
    """Testa se todos os imports do bot funcionam."""
    print("=" * 60)
    print("TESTANDO IMPORTS")
    print("=" * 60)

    tests = [
        ("GUI app", "from src.gui.app import main"),
        ("GUI state", "from src.gui.state import get_state, BotState"),
        ("GUI theme", "from src.gui.theme import BG_MAIN, card_container"),
        ("Flet", "import flet as ft"),
        ("Flet Canvas", "import flet.canvas as cv"),
        ("Flet Desktop", "import flet_desktop"),
        ("WebSocket capture", "from src.ws.capture import CrashWSCapture, GamePhase"),
        ("Strategy engine", "from src.bot.strategy import StrategyEngine"),
        ("Bankroll manager", "from src.bot.bankroll import BankrollManager"),
        ("Database manager", "from src.data.manager import DatabaseManager"),
        ("Telegram", "from src.notifications.telegram import notify_session_summary"),
        ("HWID", "from src.security.hwid import get_hwid"),
        ("Config", "from src.config import PROJECT_ROOT, API_URL"),
        ("Setups", "from src.bot.setups import SETUP_LIST, get_setup"),
        ("Schedule", "from src.bot.schedule import ScheduleManager"),
        ("Menu", "from src.bot.menu import HotKeyListener"),
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
    """Executa o build replicando 'flet pack' com excludes."""
    print("=" * 60)
    print(f"CRASHBOT v{VERSION} - FLET BUILD")
    print("=" * 60)

    # Limpar builds anteriores
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

    # =========================================================================
    # 1. Copiar flet runtime (replica o que flet pack faz)
    # =========================================================================
    print("\n[1/4] Copiando Flet runtime...")
    hook_config.temp_bin_dir = copy_flet_bin()

    if hook_config.temp_bin_dir is not None:
        # Remover fletd.exe (servidor, não necessário)
        fletd_path = os.path.join(hook_config.temp_bin_dir, "fletd.exe")
        if os.path.exists(fletd_path):
            os.remove(fletd_path)

        # Atualizar ícone do flet.exe
        exe_path = os.path.join(hook_config.temp_bin_dir, "flet", "flet.exe")
        if os.path.exists(exe_path) and ICON_PATH.exists():
            try:
                from flet_cli.__pyinstaller.win_utils import (
                    update_flet_view_icon,
                    update_flet_view_version_info,
                )
                update_flet_view_icon(exe_path, str(ICON_PATH))

                version_info_path = update_flet_view_version_info(
                    exe_path,
                    product_name="CrashBot",
                    file_description="CrashBot - Crash Game Assistant",
                    product_version=VERSION,
                    file_version=f"{VERSION}.0",
                    company_name="TucunareBot",
                    copyright="",
                )
                print(f"  Flet runtime: {hook_config.temp_bin_dir}")
                print(f"  Icone atualizado em flet.exe")
            except Exception as e:
                print(f"  AVISO: Nao foi possivel atualizar icone: {e}")
        print(f"  Flet runtime copiado: OK")
    else:
        print("  AVISO: Flet runtime nao encontrado, continuando...")

    # =========================================================================
    # 2. Montar argumentos do PyInstaller
    # =========================================================================
    print("\n[2/4] Configurando PyInstaller...")

    sep = ";" if sys.platform == "win32" else ":"

    pyi_args = [
        str(ENTRY_POINT),
        "--noconfirm",
        "--noconsole",
        "--onefile",
        "--name", "TucunareBot",
        "--distpath", str(DIST_DIR),
    ]

    # Ícone
    if ICON_PATH.exists():
        pyi_args.extend(["--icon", str(ICON_PATH)])

    # Dados
    for src_rel, dst_rel in DATA_INCLUDES:
        src_path = PROJECT_ROOT / src_rel
        if src_path.exists():
            pyi_args.extend(["--add-data", f"{src_path}{sep}{dst_rel}"])
            print(f"  + dados: {src_rel}")

    # Hidden imports
    for mod in HIDDEN_IMPORTS:
        pyi_args.extend(["--hidden-import", mod])
    print(f"  + {len(HIDDEN_IMPORTS)} hidden imports")

    # EXCLUIR módulos pesados
    for mod in EXCLUDE_MODULES:
        pyi_args.extend(["--exclude-module", mod])
    print(f"  - {len(EXCLUDE_MODULES)} modulos excluidos (torch, scipy, etc.)")

    # Version info (Windows)
    pyi_args.extend([
        "--version-file", _create_version_file(),
    ])

    # =========================================================================
    # 3. Executar PyInstaller
    # =========================================================================
    print(f"\n[3/4] Compilando... (pode levar 5-15 minutos)")
    print(f"  Entry: {ENTRY_POINT}")
    print(f"  Output: {DIST_DIR / 'TucunareBot.exe'}")

    try:
        PyInstaller.__main__.run(pyi_args)
    except SystemExit as e:
        if e.code != 0:
            print(f"\nBUILD FALHOU (exit code: {e.code})")
            return False
    finally:
        # Cleanup flet temp dir
        if hook_config.temp_bin_dir and os.path.exists(hook_config.temp_bin_dir):
            shutil.rmtree(hook_config.temp_bin_dir, ignore_errors=True)

    # =========================================================================
    # 4. Verificar resultado
    # =========================================================================
    print(f"\n[4/4] Verificando...")
    exe_path = DIST_DIR / "TucunareBot.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  BUILD OK!")
        print(f"  Arquivo: {exe_path}")
        print(f"  Tamanho: {size_mb:.1f} MB")
        return True
    else:
        # Verificar em subpastas
        for exe in DIST_DIR.rglob("TucunareBot.exe"):
            size_mb = exe.stat().st_size / (1024 * 1024)
            print(f"\n  BUILD OK!")
            print(f"  Encontrado em: {exe} ({size_mb:.1f} MB)")
            return True

        print("\nBuild concluido mas .exe nao encontrado.")
        return False


def _create_version_file() -> str:
    """Cria arquivo de version info para o Windows."""
    parts = VERSION.split(".")
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
         StringStruct(u'FileDescription', u'CrashBot - Crash Game Assistant'),
         StringStruct(u'FileVersion', u'{VERSION}.0'),
         StringStruct(u'InternalName', u'TucunareBot'),
         StringStruct(u'OriginalFilename', u'TucunareBot.exe'),
         StringStruct(u'ProductName', u'CrashBot'),
         StringStruct(u'ProductVersion', u'{VERSION}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    version_file = BUILD_DIR / "version_info.txt"
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    version_file.write_text(content, encoding="utf-8")
    return str(version_file)


def create_distribution():
    """Cria pasta de distribuição com .exe + dados necessários."""
    print("\n" + "=" * 60)
    print("CRIANDO DISTRIBUICAO")
    print("=" * 60)

    dist_package = DIST_DIR / f"CrashBot-v{VERSION}"
    dist_package.mkdir(parents=True, exist_ok=True)

    # Encontrar o .exe
    exe_path = DIST_DIR / "TucunareBot.exe"
    if not exe_path.exists():
        for exe in DIST_DIR.rglob("TucunareBot.exe"):
            exe_path = exe
            break
        else:
            print("ERRO: TucunareBot.exe nao encontrado. Rode o build primeiro.")
            return False

    # Copiar .exe
    shutil.copy2(exe_path, dist_package / "TucunareBot.exe")

    # Copiar iniciar.bat
    bat_content = f'@echo off\ntitle CrashBot v{VERSION}\ncd /d "%~dp0"\nTucunareBot.exe\npause\n'
    (dist_package / "iniciar.bat").write_text(bat_content)

    # Copiar Chrome debug helper
    chrome_bat = PROJECT_ROOT / "tools" / "abrir_chrome_debug.bat"
    if chrome_bat.exists():
        shutil.copy2(chrome_bat, dist_package / "abrir_chrome_debug.bat")

    # Criar config/ com template
    config_dir = dist_package / "config"
    config_dir.mkdir(exist_ok=True)

    env_template = (
        "# CrashBot - Configuracao\n"
        "# Preencha com seus dados\n\n"
        "TELEGRAM_BOT_TOKEN=\n"
        "TELEGRAM_CHAT_ID=\n"
        "API_URL=https://crash-api-jose.onrender.com\n"
    )
    (config_dir / ".env").write_text(env_template)

    # Criar data/db/ vazio
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
    parser = argparse.ArgumentParser(description=f"CrashBot v{VERSION} Build Script")
    parser.add_argument("--test", action="store_true", help="Apenas testa imports")
    parser.add_argument("--dist", action="store_true", help="Cria pacote de distribuicao apos build")
    args = parser.parse_args()

    # Garantir que estamos na raiz do projeto
    os.chdir(str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT))

    if args.test:
        success = test_imports()
        sys.exit(0 if success else 1)

    # Build completo
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
