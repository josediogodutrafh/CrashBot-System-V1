import os
import sys


def get_base_dir():
    """
    Define a raiz do projeto de forma inteligente.
    """
    if getattr(sys, "frozen", False):
        # MODO EXE: A raiz é onde o .exe está
        return os.path.dirname(sys.executable)
    else:
        # MODO DEV: O arquivo está em /src, então a raiz é uma pasta acima (..)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- Definição Universal de Caminhos ---
BASE_DIR = get_base_dir()

# Caminhos Absolutos (Funcionam no Exe e no VS Code)
DB_DIR = os.path.join(BASE_DIR, "banco de dados")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# 1. Banco de Dados
# Garante que a pasta exista no modo Dev, no Exe o usuário tem que ter a pasta
if not getattr(sys, "frozen", False):
    os.makedirs(DB_DIR, exist_ok=True)

DB_NAME = "crash_bot_historico.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)

# 2. Modelos de ML
MODEL_NAME = "crash_classifier.pkl"
MODEL_PATH = os.path.join(MODELS_DIR, MODEL_NAME)

SCALER_NAME = "data_scaler.pkl"
SCALER_PATH = os.path.join(MODELS_DIR, SCALER_NAME)

# 3. Configuração JSON
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
