"""
Crash_AI - Configuração Central
Todos os paths e constantes do projeto em um único lugar.
"""

import os
import sys
from pathlib import Path

# ==============================================================================
# PROJECT ROOT
# ==============================================================================

def _get_project_root() -> Path:
    """Determina a raiz do projeto (dados do usuário).
    Frozen: pasta do .exe  |  Dev: raiz do repositório."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def _get_bundle_dir() -> Path:
    """Determina onde estão os assets bundled (config, templates, tools).
    Frozen: sys._MEIPASS (_internal/)  |  Dev: igual ao PROJECT_ROOT."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


PROJECT_ROOT = _get_project_root()
BUNDLE_DIR = _get_bundle_dir()

# ==============================================================================
# VERSION
# ==============================================================================
BOT_VERSION = "5.3.0"
BOT_NAME = "TucunareBot"

# ==============================================================================
# PATHS - DADOS
# ==============================================================================
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
MODELS_DIR = DATA_DIR / "models"
PARQUET_DIR = DATA_DIR / "parquet"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = PROCESSED_DIR / "cache"

# Bancos de dados
DB_PATH = DB_DIR / "crash_bot_historico.db"
ANALYSIS_DB_PATH = DB_DIR / "brabet_crash_COMPLETO.db"

# Modelos ML
MODEL_PATH = MODELS_DIR / "crash_classifier.pkl"
SCALER_PATH = MODELS_DIR / "data_scaler.pkl"

# Parquet
RAW_PARQUET = PARQUET_DIR / "brabet_crash_COMPLETO.parquet"
FEATURES_PARQUET = PROCESSED_DIR / "crash_features.parquet"

# ==============================================================================
# PATHS - CONFIGURAÇÃO
# ==============================================================================
CONFIG_DIR = PROJECT_ROOT / "config"
PROFILES_PATH = CONFIG_DIR / "profiles.json"
ENV_PATH = CONFIG_DIR / ".env"

# ==============================================================================
# PATHS - FERRAMENTAS
# ==============================================================================
TOOLS_DIR = BUNDLE_DIR / "tools"
TESSERACT_DIR = TOOLS_DIR / "Tesseract-OCR"
TESSERACT_PATH = TESSERACT_DIR / "tesseract.exe"

# ==============================================================================
# PATHS - VISION TEMPLATES
# ==============================================================================
VISION_DIR = BUNDLE_DIR / "src" / "vision"
TEMPLATES_DIR = VISION_DIR / "templates"
TEMPLATES_SALDO = TEMPLATES_DIR / "template_saldo"
TEMPLATES_DEBUG = TEMPLATES_DIR / "templates_debug"

# ==============================================================================
# PATHS - LOGS
# ==============================================================================
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ==============================================================================
# PATHS - LEGADO (compatibilidade)
# ==============================================================================
BASE_DIR = str(PROJECT_ROOT)
DB_NAME = "crash_bot_historico.db"
MODEL_NAME = "crash_classifier.pkl"
SCALER_NAME = "data_scaler.pkl"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ==============================================================================
# CREDENCIAIS (carrega de .env)
# ==============================================================================
def _load_env():
    """Carrega variáveis do .env se existir."""
    env_vars = {}
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
                    os.environ.setdefault(key.strip(), value.strip())
    return env_vars

_ENV = _load_env()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_URL = os.environ.get("API_URL", "https://crash-api-jose.onrender.com")

# ==============================================================================
# MULTI-PLATFORM
# ==============================================================================
RECORDINGS_DIR = DATA_DIR / "recordings"

MULTI_CONFIG_PATH = CONFIG_DIR / "multi_platforms.json"

# Default debug ports per platform
PLATFORM_PORTS = {
    "brabet": 9222,
    "7bra": 9224,
    "k813bet": 9225,
    "spbetl": 9226,
    "insbet": 9227,
}

# ==============================================================================
# GARANTIR DIRETÓRIOS
# ==============================================================================
for _d in [DB_DIR, MODELS_DIR, PARQUET_DIR, PROCESSED_DIR, CACHE_DIR, CONFIG_DIR, LOGS_DIR, RECORDINGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# COPIAR CONFIGS DEFAULT (frozen: _internal/config/ → <exe_dir>/config/)
# ==============================================================================
if getattr(sys, "frozen", False):
    _bundle_config = BUNDLE_DIR / "config"
    if _bundle_config.exists() and _bundle_config != CONFIG_DIR:
        import shutil
        for _f in _bundle_config.iterdir():
            _dest = CONFIG_DIR / _f.name
            if not _dest.exists():
                if _f.is_file():
                    shutil.copy2(str(_f), str(_dest))
                elif _f.is_dir():
                    shutil.copytree(str(_f), str(_dest))
