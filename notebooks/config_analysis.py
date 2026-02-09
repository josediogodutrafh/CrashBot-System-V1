"""
Config centralizado para todos os notebooks de análise.
Importar em cada notebook com: from config_analysis import *
"""

import os
from pathlib import Path

# ==============================================================================
# PATHS
# ==============================================================================
NOTEBOOKS_DIR = Path(__file__).parent
PROJECT_ROOT = NOTEBOOKS_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "brabet_crash_COMPLETO.db"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

PARQUET_FEATURES = PROCESSED_DATA_DIR / "crash_features.parquet"

# ==============================================================================
# CONSTANTES DO JOGO
# ==============================================================================
LOW_THRESHOLD = 2.0          # Multiplicador abaixo disso = LOW
HIGH_THRESHOLD = 2.0         # Multiplicador acima/igual = HIGH
TRAGEDY_STREAK = 12          # 12+ LOWs consecutivos = tragédia

# ==============================================================================
# JANELAS DE ANÁLISE
# ==============================================================================
ROLLING_WINDOWS = [5, 10, 20, 50, 100, 250]
LAG_PERIODS = list(range(1, 11))  # lag_1 a lag_10

# ==============================================================================
# ESTRATÉGIA 1-2-4-1-2-4
# ==============================================================================
STRATEGY_TRIGGER = 6         # Entrar após 6 LOWs consecutivos
STRATEGY_TARGET = 2.0        # Alvo do multiplicador
STRATEGY_PATTERN = [1, 2, 4, 1, 2, 4]  # Padrão de sizing
STRATEGY_BREAK_AT = 12       # Quebra se atingir 12 LOWs

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def load_raw_data():
    """Carrega dados brutos do banco SQLite via DuckDB (rápido para 3.9M rows)."""
    try:
        import duckdb
        conn = duckdb.connect()
        df = conn.execute(f"""
            SELECT
                id,
                date,
                time,
                numericResult as multiplicador,
                result,
                type as tipo,
                externalId
            FROM sqlite_scan('{DB_PATH}', 'crash_rounds')
            ORDER BY date ASC
        """).fetchdf()
        conn.close()
        print(f"Carregados {len(df):,} registros via DuckDB")
        return df
    except ImportError:
        import sqlite3
        import pandas as pd
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query("""
            SELECT
                id,
                date,
                time,
                numericResult as multiplicador,
                result,
                type as tipo,
                externalId
            FROM crash_rounds
            ORDER BY date ASC
        """, conn)
        conn.close()
        print(f"Carregados {len(df):,} registros via sqlite3")
        return df


def load_processed_data():
    """Carrega dados já processados (com features) do Parquet."""
    import pandas as pd
    if PARQUET_FEATURES.exists():
        df = pd.read_parquet(PARQUET_FEATURES)
        print(f"Carregados {len(df):,} registros processados do Parquet")
        return df
    else:
        print("Dados processados não encontrados. Execute o notebook 01 primeiro.")
        return None


# ==============================================================================
# VERIFICAÇÃO
# ==============================================================================
if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"DB path:      {DB_PATH}")
    print(f"DB exists:    {DB_PATH.exists()}")
    if DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute("SELECT COUNT(*) FROM crash_rounds")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"Total rows:   {count:,}")
