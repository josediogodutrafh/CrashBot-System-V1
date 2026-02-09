"""
Data Loader - Carrega e processa dados do banco SQLite.
Cache em memória para performance.
"""

import sqlite3
from functools import lru_cache

import numpy as np
import pandas as pd

from config import DB_PATH, LOW_THRESHOLD, PROCESSED_PARQUET


def load_raw_data() -> pd.DataFrame:
    """Carrega dados brutos do SQLite."""
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

    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["date", "multiplicador"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def load_processed_data() -> pd.DataFrame | None:
    """Carrega dados processados do Parquet (com features)."""
    if PROCESSED_PARQUET.exists():
        return pd.read_parquet(PROCESSED_PARQUET)
    return None


def enrich_data(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona features básicas se não existirem."""
    if "is_low" not in df.columns:
        df["is_low"] = (df["multiplicador"] < LOW_THRESHOLD).astype(int)

    if "hora" not in df.columns:
        df["hora"] = df["date"].dt.hour

    if "dia_semana" not in df.columns:
        df["dia_semana"] = df["date"].dt.dayofweek

    if "ano_mes" not in df.columns:
        df["ano_mes"] = df["date"].dt.strftime("%Y-%m")

    if "low_streak" not in df.columns:
        streaks = np.zeros(len(df), dtype=int)
        vals = df["is_low"].values
        for i in range(1, len(vals)):
            if vals[i] == 1:
                streaks[i] = streaks[i - 1] + 1
        df["low_streak"] = streaks

    return df


def get_data() -> pd.DataFrame:
    """Ponto de entrada principal - retorna dados prontos para o dashboard."""
    df = load_processed_data()
    if df is None:
        df = load_raw_data()
        df = enrich_data(df)
    return df


def compute_kpis(df: pd.DataFrame) -> dict:
    """Calcula KPIs principais para o dashboard."""
    total = len(df)
    avg_mult = df["multiplicador"].mean()
    median_mult = df["multiplicador"].median()
    pct_low = df["is_low"].mean() * 100
    max_streak = int(df["low_streak"].max())
    max_mult = df["multiplicador"].max()
    tragedies = int((df["low_streak"] >= 12).sum())

    date_min = df["date"].min()
    date_max = df["date"].max()

    return {
        "total_rounds": total,
        "avg_multiplier": avg_mult,
        "median_multiplier": median_mult,
        "pct_low": pct_low,
        "max_streak": max_streak,
        "max_multiplier": max_mult,
        "tragedies": tragedies,
        "date_min": date_min,
        "date_max": date_max,
    }


def compute_conditional_probs(df: pd.DataFrame, max_pos: int = 20) -> pd.DataFrame:
    """Calcula P(next=LOW | current_streak=k)."""
    results = []
    is_low = df["is_low"].values
    streaks = df["low_streak"].values

    for pos in range(max_pos + 1):
        mask = streaks == pos
        indices = np.where(mask)[0]
        indices = indices[indices < len(is_low) - 1]
        if len(indices) == 0:
            continue
        next_vals = is_low[indices + 1]
        results.append({
            "posicao": pos,
            "prob_next_low": next_vals.mean(),
            "amostra": len(indices),
        })

    return pd.DataFrame(results)


def compute_streak_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula distribuição de streaks observada vs teórica."""
    is_low = df["is_low"].values
    streaks = df["low_streak"].values

    # Encontrar fins de sequência
    ends = []
    for i in range(len(streaks) - 1):
        if streaks[i] > 0 and is_low[i + 1] == 0:
            ends.append(streaks[i])
    if streaks[-1] > 0:
        ends.append(streaks[-1])

    observed = pd.Series(ends).value_counts().sort_index()
    p_low = df["is_low"].mean()
    total = len(ends)

    rows = []
    for k in range(1, int(observed.index.max()) + 1):
        obs = observed.get(k, 0)
        teo = total * (p_low ** k) * (1 - p_low)
        rows.append({
            "streak": k,
            "observado": obs,
            "teorico": teo,
            "razao": obs / teo if teo > 0 else 0,
        })

    return pd.DataFrame(rows)
