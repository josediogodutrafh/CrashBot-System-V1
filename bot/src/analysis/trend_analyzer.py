#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TREND ANALYZER
==============

Intraday trend analyzer using historical daily profile similarity.
One instance per platform. Finds days similar to today's pattern,
projects the remainder of the day, and classifies day quality.

Thread-safe: feed_round() from WS thread, get_state() from GUI thread.
"""

import logging
import threading
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.analysis.trend_cache import (
    EXPECTED_PCT_LOW,
    CLASS_MUITO_LUCRATIVO,
    CLASS_QUENTE,
    CLASS_FRIO,
)

logger = logging.getLogger(__name__)

# %LOW empírico por plataforma (dados reais do DB)
# Brabet: 55%, Onebra: 52%, PGWin: 51%, Winbra: 48%
PLATFORM_PCT_LOW = {
    "brabet": 0.5455,
    "onebra": 0.5210,
    "pgwin": 0.5140,
    "winbra": 0.4790,
}

# Similarity thresholds
MIN_CORRELATION = 0.60
MAX_SIMILAR_DAYS = 30
MIN_HOURS_FOR_ANALYSIS = 2

# Re-analysis interval
REANALYSIS_INTERVAL_SECONDS = 60
MIN_ROUNDS_BETWEEN_ANALYSIS = 10

# Description messages per classification
CLASS_DESCRIPTIONS = {
    "MUITO_LUCRATIVO": "Excelente dia para operar! Ligar os bots.",
    "QUENTE": "Tendencia positiva nas proximas horas.",
    "NORMAL": "Sem tendencia definida. Cautela.",
    "FRIO": "Dia dificil. Considerar nao operar.",
    "AGUARDANDO": "Coletando dados do dia...",
    "DADOS_INSUFICIENTES": "Poucos dias similares encontrados.",
}

# Colors for each classification
CLASS_COLORS = {
    "MUITO_LUCRATIVO": "#66BB6A",  # NEON_GREEN
    "QUENTE": "#4fc3f7",           # NEON_BLUE
    "NORMAL": "#9e9eb8",           # TEXT_SECONDARY
    "FRIO": "#FF6B6B",            # NEON_RED
    "AGUARDANDO": "#5c5c7a",      # TEXT_DIM
    "DADOS_INSUFICIENTES": "#FFC107",  # NEON_YELLOW
}


class TrendAnalyzer:
    """Intraday trend analyzer using historical daily profile similarity.

    One instance per platform. Loads cached daily profiles on init,
    receives real-time rounds, and periodically re-analyzes.
    """

    def __init__(self, platform_name: str = "brabet"):
        self.platform_name = platform_name
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"trend.{platform_name}")

        # Baseline %LOW para esta plataforma
        self._expected_pct_low = PLATFORM_PCT_LOW.get(
            platform_name, EXPECTED_PCT_LOW
        )

        # Historical daily profiles (loaded from cache)
        self._profiles: List[dict] = []
        self._profiles_loaded = False
        self._profiles_count = 0

        # Today's accumulator
        self._today_rounds_by_hour: Dict[int, List[float]] = {}
        self._today_curve: np.ndarray = np.zeros(24)
        self._today_date: Optional[date] = None
        self._current_hour: int = 0
        self._total_rounds_today: int = 0

        # Analysis results
        self._state: dict = self._empty_state()
        self._last_analysis_time: float = 0.0
        self._rounds_since_analysis: int = 0

        # Load profiles in background
        self._load_thread = threading.Thread(
            target=self._load_profiles_async,
            daemon=True,
            name=f"trend-load-{platform_name}",
        )
        self._load_thread.start()

    def _empty_state(self) -> dict:
        """Return empty/default state."""
        return {
            "day_class": "AGUARDANDO",
            "day_class_color": CLASS_COLORS["AGUARDANDO"],
            "day_class_desc": CLASS_DESCRIPTIONS["AGUARDANDO"],
            "prob_positive_end": 0.0,
            "median_expected": 0.0,
            "remaining_variation": 0.0,
            "range_p10": 0.0,
            "range_p90": 0.0,
            "consensus_pct": 0.0,
            "today_curve": [],
            "current_hour": 0,
            "band_p10": [],
            "band_p25": [],
            "band_p50": [],
            "band_p75": [],
            "band_p90": [],
            "similar_days": [],
            "n_similar_found": 0,
            "ready": False,
            "profiles_loaded": False,
            "profiles_count": 0,
            "total_rounds_today": 0,
        }

    # -- Profile Loading --

    def _load_profiles_async(self):
        """Load cached daily profiles in background thread."""
        try:
            from src.analysis.trend_cache import load_or_compute_profiles
            profiles = load_or_compute_profiles()
            with self._lock:
                self._profiles = profiles
                self._profiles_loaded = True
                self._profiles_count = len(profiles)
            self._logger.info(
                f"Loaded {len(profiles)} daily profiles for trend analysis"
            )
        except Exception as e:
            self._logger.error(f"Failed to load trend profiles: {e}")
            with self._lock:
                self._state["error"] = str(e)

    # -- Real-time Feed --

    def feed_round(self, crash_value: float, timestamp: Optional[datetime] = None):
        """Feed a new round result. Called from WS callback thread."""
        if timestamp is None:
            timestamp = datetime.now()

        today = timestamp.date()
        hour = timestamp.hour

        with self._lock:
            # Reset if new day
            if self._today_date != today:
                self._today_date = today
                self._today_rounds_by_hour = {}
                self._today_curve = np.zeros(24)
                self._rounds_since_analysis = 0
                self._total_rounds_today = 0
                self._state = self._empty_state()

            # Accumulate
            if hour not in self._today_rounds_by_hour:
                self._today_rounds_by_hour[hour] = []
            self._today_rounds_by_hour[hour].append(crash_value)
            self._current_hour = hour
            self._rounds_since_analysis += 1
            self._total_rounds_today += 1

            # Recompute today's curve
            self._recompute_today_curve()

    def _recompute_today_curve(self):
        """Recompute today's hourly cumulative deviation curve.
        Must be called while holding _lock.

        Usa self._expected_pct_low (per-platform) como baseline,
        mas normaliza para o mesmo eixo dos perfis historicos (55%)
        para que a correlacao de Pearson funcione cross-platform.
        """
        cumulative = 0.0
        for h in range(24):
            rounds = self._today_rounds_by_hour.get(h, [])
            if rounds:
                n_low = sum(1 for v in rounds if v < 2.0)
                n_total = len(rounds)
                actual_pct = n_low / n_total
                # Desvio relativo ao baseline da plataforma
                hourly_dev = (actual_pct - self._expected_pct_low) * n_total
                cumulative += hourly_dev
            self._today_curve[h] = cumulative

    # -- Analysis --

    def should_analyze(self) -> bool:
        """Check if enough time/rounds have passed for re-analysis."""
        if not self._profiles_loaded:
            return False
        now = time.time()
        if now - self._last_analysis_time < REANALYSIS_INTERVAL_SECONDS:
            return False
        if self._rounds_since_analysis < MIN_ROUNDS_BETWEEN_ANALYSIS:
            return False
        return True

    def analyze(self):
        """Run similarity analysis. Called periodically."""
        with self._lock:
            if not self._profiles_loaded:
                return
            if self._current_hour < MIN_HOURS_FOR_ANALYSIS:
                self._state["profiles_loaded"] = True
                self._state["profiles_count"] = self._profiles_count
                self._state["total_rounds_today"] = self._total_rounds_today
                return

            today_partial = self._today_curve[: self._current_hour + 1].copy()
            profiles = self._profiles  # safe: list itself doesn't mutate
            current_hour = self._current_hour
            today_curve_full = self._today_curve.copy()
            total_rounds = self._total_rounds_today

        # Find similar days (outside lock for performance)
        similar = self._find_similar_days(today_partial, profiles, current_hour)

        # Compute projections
        state = self._compute_projections(
            similar, today_partial, current_hour, today_curve_full
        )
        state["profiles_loaded"] = True
        state["profiles_count"] = len(profiles)
        state["total_rounds_today"] = total_rounds

        with self._lock:
            self._state = state
            self._last_analysis_time = time.time()
            self._rounds_since_analysis = 0

    def _find_similar_days(
        self,
        today_partial: np.ndarray,
        profiles: List[dict],
        current_hour: int,
    ) -> List[Tuple[dict, float]]:
        """Find historical days most similar to today's partial curve."""
        if len(today_partial) < MIN_HOURS_FOR_ANALYSIS:
            return []

        # Skip if today's curve is flat (all zeros)
        if np.std(today_partial) < 1e-10:
            return []

        scored = []
        for prof in profiles:
            hist_partial = prof["hourly_deviation"][: current_hour + 1]

            # Skip flat days
            if np.std(hist_partial) < 1e-10:
                continue

            # Pearson correlation
            corr = np.corrcoef(today_partial, hist_partial)[0, 1]
            if np.isnan(corr) or corr < MIN_CORRELATION:
                continue

            # RMSE as secondary quality metric
            rmse = float(np.sqrt(np.mean((today_partial - hist_partial) ** 2)))

            # Combined score: high correlation, low RMSE
            score = corr - 0.05 * rmse
            scored.append((prof, float(corr), score))

        # Sort by score descending
        scored.sort(key=lambda x: x[2], reverse=True)
        return [(p, c) for p, c, _ in scored[:MAX_SIMILAR_DAYS]]

    def _compute_projections(
        self,
        similar: List[Tuple[dict, float]],
        today_partial: np.ndarray,
        current_hour: int,
        today_curve_full: np.ndarray,
    ) -> dict:
        """Compute percentile bands, metrics, and classification."""
        state = self._empty_state()
        state["today_curve"] = today_curve_full[: current_hour + 1].tolist()
        state["current_hour"] = current_hour
        state["n_similar_found"] = len(similar)

        if len(similar) < 5:
            state["day_class"] = "DADOS_INSUFICIENTES"
            state["day_class_color"] = CLASS_COLORS["DADOS_INSUFICIENTES"]
            state["day_class_desc"] = CLASS_DESCRIPTIONS["DADOS_INSUFICIENTES"]
            state["ready"] = True
            return state

        # Collect full 24h curves from similar days
        curves = np.array([p["hourly_deviation"] for p, _ in similar])

        # Percentile bands (full 24h projection)
        state["band_p10"] = np.percentile(curves, 10, axis=0).tolist()
        state["band_p25"] = np.percentile(curves, 25, axis=0).tolist()
        state["band_p50"] = np.percentile(curves, 50, axis=0).tolist()
        state["band_p75"] = np.percentile(curves, 75, axis=0).tolist()
        state["band_p90"] = np.percentile(curves, 90, axis=0).tolist()

        # Key metrics from final values
        final_values = curves[:, -1]
        state["prob_positive_end"] = float(np.mean(final_values > 0) * 100)
        state["median_expected"] = float(np.median(final_values))

        # Remaining variation: median of (final - current) for similar days
        current_values = curves[:, current_hour]
        remaining = final_values - current_values
        state["remaining_variation"] = float(np.median(remaining))

        # Range P10-P90
        state["range_p10"] = float(np.percentile(final_values, 10))
        state["range_p90"] = float(np.percentile(final_values, 90))

        # Consensus: % of similar days where remaining direction matches median
        median_remaining = np.median(remaining)
        if abs(median_remaining) > 0.1:
            direction = np.sign(median_remaining)
            agree = np.sum(np.sign(remaining) == direction)
            state["consensus_pct"] = float(agree / len(remaining) * 100)
        else:
            state["consensus_pct"] = 50.0

        # Classification based on median projected end
        median_end = state["median_expected"]
        if median_end >= CLASS_MUITO_LUCRATIVO:
            cls = "MUITO_LUCRATIVO"
        elif median_end >= CLASS_QUENTE:
            cls = "QUENTE"
        elif median_end <= CLASS_FRIO:
            cls = "FRIO"
        else:
            cls = "NORMAL"

        state["day_class"] = cls
        state["day_class_color"] = CLASS_COLORS[cls]
        state["day_class_desc"] = CLASS_DESCRIPTIONS[cls]

        # Top 5 similar days for overlay chart
        top5 = similar[:5]
        state["similar_days"] = [
            {
                "date": p["date"],
                "curve": p["hourly_deviation"].tolist(),
                "correlation": round(corr, 3),
                "final": round(p["final_deviation"], 1),
            }
            for p, corr in top5
        ]

        state["ready"] = True
        return state

    # -- State for GUI --

    def get_state(self) -> dict:
        """Return thread-safe snapshot for GUI rendering."""
        with self._lock:
            # Return a copy to avoid mutation
            return dict(self._state)
