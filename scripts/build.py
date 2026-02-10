"""
Crash_AI - Build Script (Nuitka)
Compila o bot em .exe nativo via Nuitka.

Uso:
    python scripts/build.py          # Build completo
    python scripts/build.py --test   # Apenas testa imports (sem compilar)

Requisitos:
    pip install nuitka ordered-set zstandard
    + C compiler (MSVC ou MinGW-w64)
"""

import argparse
import shutil
import subprocess
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

# Diretórios de dados para incluir no build
DATA_INCLUDES = [
    ("config", "config"),                          # profiles.json, .env
    ("tools/Tesseract-OCR", "tools/Tesseract-OCR"),  # OCR engine
    ("src/vision/templates", "src/vision/templates"),  # Template images
    ("tools/icone.ico", "tools/icone.ico"),          # App icon
    ("tools/abrir_chrome_debug.bat", "tools/abrir_chrome_debug.bat"),
]

# Pacotes Python que o bot usa
PACKAGES = [
    "src",
    "requests",
    "websocket",
    "pyautogui",
    "pyperclip",
    "pynput",
    "rich",
    "pytz",
    "PIL",           # Pillow
    "yaml",          # PyYAML
    "dateutil",      # python-dateutil
    "tkinter",
]

# Módulos a excluir (não usados no bot client)
EXCLUDE_MODULES = [
    "dash",
    "plotly",
    "duckdb",
    "polars",
    "statsmodels",
    "ruptures",
    "hmmlearn",
    "torch",
    "torchvision",
    "sklearn",
    "scipy",
    "easyocr",
    "cv2",
    "skimage",
    "pandas",
    "numpy",        # se não for usado diretamente no bot
    "matplotlib",
    "notebook",
    "jupyter",
    "IPython",
    "pytest",
    "dash_bootstrap_components",
]


def test_imports():
    """Testa se todos os imports do bot funcionam."""
    print("=" * 60)
    print("TESTANDO IMPORTS")
    print("=" * 60)

    tests = [
        ("run.py entry point", "from src.bot.controller import main"),
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
        ("Rich", "from rich.console import Console"),
        ("PyAutoGUI", "import pyautogui"),
        ("Requests", "import requests"),
        ("WebSocket", "import websocket"),
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


def check_nuitka():
    """Verifica se Nuitka está instalado."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True, text=True
        )
        version = result.stdout.strip().split("\n")[0]
        print(f"Nuitka encontrado: {version}")
        return True
    except Exception:
        print("ERRO: Nuitka nao instalado!")
        print("  pip install nuitka ordered-set zstandard")
        return False


def check_compiler():
    """Verifica se um compilador C está disponível."""
    # Tenta MSVC primeiro
    for compiler in ["cl", "gcc", "cc"]:
        if shutil.which(compiler):
            print(f"Compilador encontrado: {compiler}")
            return True

    # Nuitka pode achar o MSVC via VS installer
    print("AVISO: Compilador C nao encontrado no PATH.")
    print("  Nuitka vai tentar achar MSVC automaticamente.")
    print("  Se falhar, instale: Visual Studio Build Tools ou MinGW-w64")
    return True  # Deixa o Nuitka tentar


def build():
    """Executa o build com Nuitka."""
    print("=" * 60)
    print("CRASH_AI - NUITKA BUILD")
    print("=" * 60)

    if not check_nuitka():
        return False

    check_compiler()

    # Limpar builds anteriores
    if DIST_DIR.exists():
        print(f"Limpando {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    # Montar comando Nuitka
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",                    # Gera pasta standalone
        "--onefile",                       # Empacota tudo em 1 .exe
        f"--output-dir={DIST_DIR}",
        "--output-filename=CrashBot.exe",

        # Identificação
        "--company-name=TucunareBot",
        "--product-name=CrashBot",
        "--product-version=3.0.0",
        "--file-description=CrashBot - Crash Game Assistant",
    ]

    # Icon
    icon_path = PROJECT_ROOT / "tools" / "icone.ico"
    if icon_path.exists():
        cmd.append(f"--windows-icon-from-ico={icon_path}")

    # Disable console (manter console para o Rich UI)
    cmd.append("--windows-console-mode=force")

    # Incluir pacotes
    for pkg in PACKAGES:
        cmd.append(f"--include-package={pkg}")

    # Excluir pacotes desnecessários
    for mod in EXCLUDE_MODULES:
        cmd.append(f"--nofollow-import-to={mod}")

    # Incluir dados
    for src, dst in DATA_INCLUDES:
        src_path = PROJECT_ROOT / src
        if src_path.exists():
            if src_path.is_dir():
                cmd.append(f"--include-data-dir={src_path}={dst}")
            else:
                cmd.append(f"--include-data-files={src_path}={dst}")
            print(f"  Incluindo: {src}")
        else:
            print(f"  AVISO: Nao encontrado: {src}")

    # Plugin para tkinter (usado no bot para dialogs)
    cmd.append("--enable-plugin=tk-inter")

    # Entry point
    cmd.append(str(ENTRY_POINT))

    print("\nComando Nuitka:")
    print(" ".join(cmd[:5]) + " \\\n  " + " \\\n  ".join(cmd[5:]))
    print()

    # Executar build
    print("Iniciando compilacao... (pode levar 10-30 minutos)")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode == 0:
        exe_path = DIST_DIR / "CrashBot.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\nBUILD OK!")
            print(f"  Arquivo: {exe_path}")
            print(f"  Tamanho: {size_mb:.1f} MB")
        else:
            print("\nBuild concluido mas .exe nao encontrado.")
            print(f"  Verifique: {DIST_DIR}")
        return True
    else:
        print(f"\nBUILD FALHOU (exit code: {result.returncode})")
        return False


def create_distribution():
    """Cria pasta de distribuição com .exe + dados necessários."""
    print("\n" + "=" * 60)
    print("CRIANDO DISTRIBUICAO")
    print("=" * 60)

    dist_package = DIST_DIR / "CrashBot-v3.0.0"
    dist_package.mkdir(parents=True, exist_ok=True)

    exe_path = DIST_DIR / "CrashBot.exe"
    if not exe_path.exists():
        print("ERRO: CrashBot.exe nao encontrado. Rode o build primeiro.")
        return False

    # Copiar .exe
    shutil.copy2(exe_path, dist_package / "CrashBot.exe")

    # Copiar iniciar.bat adaptado
    bat_content = '@echo off\ntitle CrashBot v3.0\ncd /d "%~dp0"\nCrashBot.exe\npause\n'
    (dist_package / "iniciar.bat").write_text(bat_content)

    # Copiar Chrome debug helper
    chrome_bat = PROJECT_ROOT / "tools" / "abrir_chrome_debug.bat"
    if chrome_bat.exists():
        shutil.copy2(chrome_bat, dist_package / "abrir_chrome_debug.bat")

    # Criar config/ vazio com template
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
    for item in sorted(dist_package.rglob("*")):
        if item.is_file():
            rel = item.relative_to(dist_package)
            print(f"  {rel}")

    return True


def main():
    parser = argparse.ArgumentParser(description="CrashBot Build Script (Nuitka)")
    parser.add_argument("--test", action="store_true", help="Apenas testa imports")
    parser.add_argument("--dist", action="store_true", help="Cria pacote de distribuicao apos build")
    args = parser.parse_args()

    # Garantir que estamos na raiz do projeto
    import os
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
