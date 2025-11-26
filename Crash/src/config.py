import os
import sys


def get_base_dir():
    """
    Determina o diretório base para o script, funcione ele como .py
    ou como um executável "congelado" do PyInstaller (--onefile).
    """
    if getattr(sys, "frozen", False):
        # Se estiver "congelado" (rodando como .exe)
        return os.path.dirname(sys.executable)
    else:
        # Se estiver rodando como .py normal
        return os.path.dirname(os.path.abspath(__file__))


# --- Definição Universal de Caminhos ---
BASE_DIR = get_base_dir()

# 1. Banco de Dados (Leitura/Escrita)
DB_NAME = "crash_bot_historico.db"
DB_PATH = os.path.join(BASE_DIR, DB_NAME)
DATABASE_URL = f"sqlite:///{DB_PATH}"  # Para SQLAlchemy (se precisar)

# 2. Modelo de ML (Estático, Leitura)
MODEL_NAME = "crash_classifier.pkl"
MODEL_PATH = os.path.join(BASE_DIR, MODEL_NAME)

# 3. Scaler de ML (Estático, Leitura) - A ADIÇÃO IMPORTANTE
SCALER_NAME = "data_scaler.pkl"
SCALER_PATH = os.path.join(BASE_DIR, SCALER_NAME)
