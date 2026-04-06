#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TREND CACHE
===========

Pre-computes daily intraday profiles from the historical parquet file
and caches them in a small parquet for fast reloads.

Each daily profile is a 24-point curve of cumulative %LOW deviation
from the expected 55% baseline. This captures whether a given day
ran "hot" (more LOWs = more betting opportunities) or "cold".

First run: reads ~3.96M rows from crash_features.parquet (~0.5s)
Subsequent runs: loads cached daily_profiles.parquet (~50KB, <0.1s)
"""

import logging
import time
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Expected %LOW per round (from NB-11 statistical profile: 54.55%)
# Using exact empirical rate so daily deviations center around 0
EXPECTED_PCT_LOW = 0.5455

# Minimum rounds for a day to be valid (skip partial days)
MIN_ROUNDS_PER_DAY = 100

# Classification thresholds (cumulative deviation units)
# Calibrated on 1145 days: ML=16%, Q=20%, N=37%, F=27%
CLASS_MUITO_LUCRATIVO = 25.0
CLASS_QUENTE = 5.0
CLASS_FRIO = -25.0


def _get_cache_path() -> Path:
    """Get the cache file path."""
    from src.config import CACHE_DIR
    return CACHE_DIR / "daily_profiles.parquet"


def _get_source_path() -> Path:
    """Get the source parquet path, with fallback to Crash_AI."""
    from src.config import FEATURES_PARQUET
    if FEATURES_PARQUET.exists():
        return FEATURES_PARQUET

    # Fallback: try Crash_AI production data
    fallback = Path(r"c:\IA\Crash_AI\data\processed\crash_features.parquet")
    if fallback.exists():
        logger.info(f"Using fallback parquet: {fallback}")
        return fallback

    raise FileNotFoundError(
        f"Parquet not found at {FEATURES_PARQUET} or {fallback}. "
        "Run NB-01 to generate crash_features.parquet."
    )


def load_or_compute_profiles() -> List[dict]:
    """Load cached daily profiles, or compute from parquet if stale/missing.

    Returns:
        List of dicts with keys: date, hourly_deviation (np.ndarray of 24),
        total_rounds, final_deviation, classification.
    """
    cache_path = _get_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if _is_cache_valid(cache_path):
        logger.info("Loading cached daily profiles...")
        return _load_from_cache(cache_path)

    logger.info("Computing daily profiles from parquet (first time or stale cache)...")
    profiles = _compute_from_parquet()
    _save_to_cache(profiles, cache_path)
    return profiles


def _is_cache_valid(cache_path: Path) -> bool:
    """Check if cache exists and is newer than source parquet."""
    if not cache_path.exists():
        return False
    try:
        source_path = _get_source_path()
        return cache_path.stat().st_mtime > source_path.stat().st_mtime
    except FileNotFoundError:
        return False


def _compute_from_parquet() -> List[dict]:
    """Load the parquet and compute daily profiles.

    Reads only 3 columns (date, multiplicador, hora) to minimize memory.
    Groups by date+hour, computes cumulative %LOW deviation curve per day.
    """
    source_path = _get_source_path()
    start = time.time()

    df = pd.read_parquet(
        source_path,
        columns=["date", "multiplicador", "hora"],
    )
    logger.info(f"Loaded {len(df):,} rows from parquet in {time.time()-start:.1f}s")

    # Extract date-only for grouping
    df["day"] = pd.to_datetime(df["date"]).dt.date

    # Group by day+hour: count total and LOWs
    grouped = (
        df.groupby(["day", "hora"])
        .agg(
            n_rounds=("multiplicador", "count"),
            n_low=("multiplicador", lambda x: (x < 2.0).sum()),
        )
        .reset_index()
    )

    # Filter days with enough rounds
    day_totals = df.groupby("day")["multiplicador"].count().reset_index()
    day_totals.columns = ["day", "total_rounds"]
    valid_days = day_totals[day_totals["total_rounds"] >= MIN_ROUNDS_PER_DAY]

    profiles = []
    for _, day_row in valid_days.iterrows():
        day = day_row["day"]
        total = int(day_row["total_rounds"])
        day_data = grouped[grouped["day"] == day].set_index("hora")

        # Build 24-hour cumulative deviation curve
        curve = np.zeros(24)
        cumulative = 0.0
        for h in range(24):
            if h in day_data.index:
                row = day_data.loc[h]
                n = int(row["n_rounds"])
                n_low = int(row["n_low"])
                if n > 0:
                    actual_pct = n_low / n
                    hourly_dev = (actual_pct - EXPECTED_PCT_LOW) * n
                    cumulative += hourly_dev
            curve[h] = cumulative

        # Classify
        final = float(curve[-1])
        if final >= CLASS_MUITO_LUCRATIVO:
            cls = "MUITO_LUCRATIVO"
        elif final >= CLASS_QUENTE:
            cls = "QUENTE"
        elif final <= CLASS_FRIO:
            cls = "FRIO"
        else:
            cls = "NORMAL"

        profiles.append({
            "date": str(day),
            "hourly_deviation": curve,
            "total_rounds": total,
            "final_deviation": final,
            "classification": cls,
        })

    elapsed = time.time() - start
    logger.info(
        f"Computed {len(profiles)} daily profiles in {elapsed:.1f}s "
        f"({len(valid_days)} valid days)"
    )
    return profiles


def _save_to_cache(profiles: List[dict], cache_path: Path):
    """Save profiles to parquet cache for fast reloads."""
    rows = []
    for p in profiles:
        row = {
            "date": p["date"],
            "total_rounds": p["total_rounds"],
            "final_deviation": p["final_deviation"],
            "classification": p["classification"],
        }
        for h in range(24):
            row[f"h{h:02d}"] = float(p["hourly_deviation"][h])
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_parquet(cache_path, index=False)
    logger.info(f"Saved {len(profiles)} profiles to cache: {cache_path}")


def _load_from_cache(cache_path: Path) -> List[dict]:
    """Load profiles from parquet cache."""
    df = pd.read_parquet(cache_path)
    hour_cols = [f"h{h:02d}" for h in range(24)]

    profiles = []
    for _, row in df.iterrows():
        curve = np.array([row[c] for c in hour_cols])
        profiles.append({
            "date": row["date"],
            "hourly_deviation": curve,
            "total_rounds": int(row["total_rounds"]),
            "final_deviation": float(row["final_deviation"]),
            "classification": row["classification"],
        })

    logger.info(f"Loaded {len(profiles)} cached daily profiles")
    return profiles
