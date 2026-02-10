#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - DATA COLLECTOR

Coleta, armazena e prepara dados para treinamento de modelos de IA.
Gerencia histórico de explosões, apostas e resultados.

Uso:
    from engine.ml.data_collector import DataCollector, get_collector

    collector = get_collector()

    # Adiciona explosão
    collector.add_explosion(1.45)

    # Adiciona resultado de aposta
    collector.add_bet_result(bet=10.0, target=1.85, result="win", profit=8.50)

    # Obtém dados para treino
    X, y = collector.get_training_data(sequence_length=20)

    # Exporta/Importa
    collector.export_to_csv("data/historico.csv")
    collector.import_from_csv("data/historico.csv")
"""

from __future__ import annotations

import csv
import json
import logging
import os
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Core imports
from core.events import BotEvent, emit, get_event_bus

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ExplosionRecord:
    """Registro de uma explosão."""

    value: float
    timestamp: str
    round_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BetRecord:
    """Registro de uma aposta."""

    amount: float
    target: float
    result: str  # "win", "loss", "skip"
    profit: float
    explosion_value: float
    dobra: int
    timestamp: str
    balance_before: float = 0.0
    balance_after: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionStats:
    """Estatísticas de uma sessão."""

    start_time: str
    end_time: Optional[str] = None
    total_explosions: int = 0
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: float = 0.0
    initial_balance: float = 0.0
    final_balance: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATA COLLECTOR
# ═══════════════════════════════════════════════════════════════════════════════


class DataCollector:
    """
    Coletor e preparador de dados para ML.

    Features:
        - Armazena histórico de explosões em memória
        - Persiste dados em arquivo
        - Prepara dados para LSTM (sequências)
        - Prepara dados para RL (estados)
        - Calcula features derivadas
        - Normalização automática

    Exemplo:
        collector = DataCollector()

        # Durante operação do bot
        collector.add_explosion(1.45)
        collector.add_explosion(2.34)

        # Para treinar modelo
        X, y = collector.get_training_data(sequence_length=20)

        # Para RL
        state = collector.get_current_state()
    """

    def __init__(
        self,
        max_memory: int = 100000,
        data_dir: str = "data",
        emit_events: bool = True,
    ):
        """
        Inicializa o coletor de dados.

        Args:
            max_memory: Máximo de registros em memória
            data_dir: Diretório para persistência
            emit_events: Se True, emite eventos no EventBus
        """
        self._lock = threading.Lock()
        self._emit_events = emit_events

        # Configurações
        self._max_memory = max_memory
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Dados em memória
        self._explosions: deque = deque(maxlen=max_memory)
        self._bets: deque = deque(maxlen=max_memory)

        # Contadores
        self._round_number = 0
        self._session_stats = SessionStats(start_time=datetime.now().isoformat())

        # Cache de features
        self._features_cache: Dict[str, Any] = {}
        self._cache_valid = False

        # Auto-save
        self._auto_save_interval = 1000  # A cada N explosões
        self._unsaved_count = 0

        logger.debug(f"DataCollector inicializado (max_memory={max_memory})")

    # ═══════════════════════════════════════════════════════════════════════════
    # COLETA DE DADOS
    # ═══════════════════════════════════════════════════════════════════════════

    def add_explosion(self, value: float, timestamp: Optional[str] = None) -> None:
        """
        Registra uma nova explosão.

        Args:
            value: Valor da explosão
            timestamp: Timestamp (usa atual se None)
        """
        with self._lock:
            self._round_number += 1

            record = ExplosionRecord(
                value=value,
                timestamp=timestamp or datetime.now().isoformat(),
                round_number=self._round_number,
            )

            self._explosions.append(record)
            self._session_stats.total_explosions += 1
            self._cache_valid = False

            # Auto-save
            self._unsaved_count += 1
            if self._unsaved_count >= self._auto_save_interval:
                self._auto_save()

        if self._emit_events:
            emit(
                BotEvent.EXPLOSION_DETECTED,
                {
                    "value": value,
                    "round": self._round_number,
                },
            )

        logger.debug(f"Explosão registrada: {value}x (round {self._round_number})")

    def add_bet_result(
        self,
        amount: float,
        target: float,
        result: str,
        profit: float,
        explosion_value: float,
        dobra: int = 1,
        balance_before: float = 0.0,
        balance_after: float = 0.0,
    ) -> None:
        """
        Registra resultado de uma aposta.

        Args:
            amount: Valor apostado
            target: Alvo (multiplicador)
            result: "win" ou "loss"
            profit: Lucro/prejuízo
            explosion_value: Valor da explosão
            dobra: Nível da dobra (1-4)
            balance_before: Saldo antes
            balance_after: Saldo depois
        """
        with self._lock:
            record = BetRecord(
                amount=amount,
                target=target,
                result=result,
                profit=profit,
                explosion_value=explosion_value,
                dobra=dobra,
                timestamp=datetime.now().isoformat(),
                balance_before=balance_before,
                balance_after=balance_after,
            )

            self._bets.append(record)
            self._session_stats.total_bets += 1

            if result == "win":
                self._session_stats.wins += 1
            elif result == "loss":
                self._session_stats.losses += 1

            self._session_stats.total_profit += profit
            self._cache_valid = False

        logger.debug(f"Aposta registrada: R${amount:.2f} @ {target}x = {result}")

    def add_explosions_bulk(self, values: List[float]) -> None:
        """
        Adiciona múltiplas explosões de uma vez (importação).

        Args:
            values: Lista de valores de explosão
        """
        with self._lock:
            for value in values:
                self._round_number += 1
                record = ExplosionRecord(
                    value=value,
                    timestamp=datetime.now().isoformat(),
                    round_number=self._round_number,
                )
                self._explosions.append(record)

            self._session_stats.total_explosions += len(values)
            self._cache_valid = False

        logger.info(f"Importadas {len(values)} explosões em bulk")

    # ═══════════════════════════════════════════════════════════════════════════
    # PREPARAÇÃO DE DADOS PARA ML
    # ═══════════════════════════════════════════════════════════════════════════

    def get_explosions_array(self, limit: Optional[int] = None) -> np.ndarray:
        """
        Retorna explosões como array numpy.

        Args:
            limit: Limita quantidade (None = todas)

        Returns:
            Array 1D com valores das explosões
        """
        with self._lock:
            explosions = list(self._explosions)

        if limit:
            explosions = explosions[-limit:]

        return np.array([e.value for e in explosions], dtype=np.float32)

    def get_training_data(
        self,
        sequence_length: int = 20,
        target_offset: int = 1,
        normalize: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara dados para treinamento de LSTM.

        Cria sequências de explosões passadas (X) e próxima explosão (y).

        Args:
            sequence_length: Tamanho da sequência de entrada
            target_offset: Quantas explosões à frente prever
            normalize: Se True, normaliza os dados

        Returns:
            Tupla (X, y) onde:
            - X: shape (num_samples, sequence_length, num_features)
            - y: shape (num_samples,)
        """
        values = self.get_explosions_array()

        if len(values) < sequence_length + target_offset:
            logger.warning(
                f"Dados insuficientes: {len(values)} < {sequence_length + target_offset}"
            )
            return np.array([]), np.array([])

        # Normalização
        if normalize:
            mean = np.mean(values)
            std = np.std(values)
            if std > 0:
                values_norm = (values - mean) / std
            else:
                values_norm = values - mean
        else:
            values_norm = values

        # Cria sequências
        X = []
        y = []

        for i in range(len(values_norm) - sequence_length - target_offset + 1):
            X.append(values_norm[i : i + sequence_length])
            y.append(values_norm[i + sequence_length + target_offset - 1])

        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.float32)

        # Adiciona dimensão de features (LSTM espera 3D)
        X = X.reshape(X.shape[0], X.shape[1], 1)

        logger.info(f"Dados de treino preparados: X={X.shape}, y={y.shape}")
        return X, y

    def get_training_data_with_features(
        self,
        sequence_length: int = 20,
        normalize: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara dados com features derivadas para LSTM.

        Features por timestep:
        - value: valor da explosão
        - is_low: 1 se < 2.0, 0 se >= 2.0
        - rolling_mean_5: média móvel de 5
        - rolling_std_5: desvio padrão móvel de 5
        - streak: sequência de lows consecutivos

        Returns:
            Tupla (X, y) com features expandidas
        """
        values = self.get_explosions_array()

        if len(values) < sequence_length + 1:
            return np.array([]), np.array([])

        # Calcula features
        features = self._calculate_features(values)

        # Normaliza se necessário
        if normalize:
            features = self._normalize_features(features)

        # Cria sequências
        X = []
        y = []

        for i in range(len(features) - sequence_length):
            X.append(features[i : i + sequence_length])
            y.append(
                1 if values[i + sequence_length] < 2.0 else 0
            )  # Classifica próxima

        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.float32)

        logger.info(f"Dados com features preparados: X={X.shape}, y={y.shape}")
        return X, y

    def _calculate_features(self, values: np.ndarray) -> np.ndarray:
        """Calcula features derivadas para cada timestep."""
        n = len(values)
        num_features = 5
        features = np.zeros((n, num_features), dtype=np.float32)

        # Feature 0: valor original
        features[:, 0] = values

        # Feature 1: is_low (binário)
        features[:, 1] = (values < 2.0).astype(np.float32)

        # Feature 2: média móvel de 5
        for i in range(n):
            start = max(0, i - 4)
            features[i, 2] = np.mean(values[start : i + 1])

        # Feature 3: desvio padrão móvel de 5
        for i in range(n):
            start = max(0, i - 4)
            if i - start > 0:
                features[i, 3] = np.std(values[start : i + 1])

        # Feature 4: streak de lows
        streak = 0
        for i in range(n):
            if values[i] < 2.0:
                streak += 1
            else:
                streak = 0
            features[i, 4] = streak

        return features

    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """Normaliza features usando min-max scaling."""
        normalized = np.zeros_like(features)

        for i in range(features.shape[1]):
            col = features[:, i]
            min_val = np.min(col)
            max_val = np.max(col)

            if max_val > min_val:
                normalized[:, i] = (col - min_val) / (max_val - min_val)
            else:
                normalized[:, i] = 0.0

        return normalized

    # ═══════════════════════════════════════════════════════════════════════════
    # DADOS PARA REINFORCEMENT LEARNING
    # ═══════════════════════════════════════════════════════════════════════════

    def get_current_state(self, history_size: int = 20) -> np.ndarray:
        """
        Retorna estado atual para o agente de RL.

        Estado inclui:
        - Últimas N explosões normalizadas
        - Streak atual de lows
        - Média das últimas N
        - Volatilidade (std)

        Args:
            history_size: Quantidade de explosões no histórico

        Returns:
            Array 1D com o estado atual
        """
        values = self.get_explosions_array(limit=history_size)

        if len(values) < history_size:
            # Pad com zeros se não tiver dados suficientes
            padding = np.zeros(history_size - len(values))
            values = np.concatenate([padding, values])

        # Normaliza valores (divide por 10 para manter em range razoável)
        values_norm = values / 10.0

        # Calcula features agregadas
        mean = np.mean(values) / 10.0 if len(values) > 0 else 0
        std = np.std(values) / 10.0 if len(values) > 1 else 0

        # Conta streak de lows
        streak = 0
        for v in reversed(values):
            if v < 2.0:
                streak += 1
            else:
                break
        streak_norm = streak / 10.0

        # Monta estado
        state = np.concatenate([values_norm, [mean, std, streak_norm]])

        return state.astype(np.float32)

    def get_state_size(self, history_size: int = 20) -> int:
        """Retorna tamanho do vetor de estado para RL."""
        return history_size + 3  # valores + mean + std + streak

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTATÍSTICAS E ANÁLISE
    # ═══════════════════════════════════════════════════════════════════════════

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos dados coletados."""
        with self._lock:
            values = [e.value for e in self._explosions]

        if not values:
            return {"total": 0}

        values_arr = np.array(values)
        threshold = 2.0

        lows = values_arr[values_arr < threshold]
        highs = values_arr[values_arr >= threshold]

        return {
            "total": len(values),
            "mean": float(np.mean(values_arr)),
            "std": float(np.std(values_arr)),
            "min": float(np.min(values_arr)),
            "max": float(np.max(values_arr)),
            "median": float(np.median(values_arr)),
            "lows_count": len(lows),
            "highs_count": len(highs),
            "lows_percent": len(lows) / len(values) * 100,
            "lows_mean": float(np.mean(lows)) if len(lows) > 0 else 0,
            "highs_mean": float(np.mean(highs)) if len(highs) > 0 else 0,
            "session_stats": asdict(self._session_stats),
        }

    def get_streak_analysis(self, threshold: float = 2.0) -> Dict[str, Any]:
        """Analisa sequências de explosões baixas."""
        values = self.get_explosions_array()

        if len(values) == 0:
            return {"total_streaks": 0}

        streaks = []
        current_streak = 0

        for v in values:
            if v < threshold:
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0

        if current_streak > 0:
            streaks.append(current_streak)

        if not streaks:
            return {"total_streaks": 0}

        return {
            "total_streaks": len(streaks),
            "max_streak": max(streaks),
            "avg_streak": np.mean(streaks),
            "streak_distribution": {
                i: streaks.count(i) for i in range(1, max(streaks) + 1)
            },
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTÊNCIA
    # ═══════════════════════════════════════════════════════════════════════════

    def export_to_csv(self, filepath: str) -> bool:
        """
        Exporta explosões para arquivo CSV.

        Args:
            filepath: Caminho do arquivo

        Returns:
            True se exportou com sucesso
        """
        try:
            with self._lock:
                explosions = list(self._explosions)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["value", "timestamp", "round_number"]
                )
                writer.writeheader()
                for e in explosions:
                    writer.writerow(e.to_dict())

            logger.info(f"Exportados {len(explosions)} registros para {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erro ao exportar: {e}")
            return False

    def import_from_csv(self, filepath: str, append: bool = True) -> int:
        """
        Importa explosões de arquivo CSV.

        Args:
            filepath: Caminho do arquivo
            append: Se True, adiciona aos dados existentes

        Returns:
            Número de registros importados
        """
        try:
            if not append:
                with self._lock:
                    self._explosions.clear()
                    self._round_number = 0

            count = 0
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                values = []
                for row in reader:
                    values.append(float(row["value"]))
                    count += 1

                self.add_explosions_bulk(values)

            logger.info(f"Importados {count} registros de {filepath}")
            return count

        except Exception as e:
            logger.error(f"Erro ao importar: {e}")
            return 0

    def export_to_json(self, filepath: str) -> bool:
        """Exporta todos os dados para JSON."""
        try:
            with self._lock:
                data = {
                    "explosions": [e.to_dict() for e in self._explosions],
                    "bets": [b.to_dict() for b in self._bets],
                    "session_stats": asdict(self._session_stats),
                    "exported_at": datetime.now().isoformat(),
                }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Dados exportados para {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erro ao exportar JSON: {e}")
            return False

    def _auto_save(self) -> None:
        """Auto-save periódico."""
        try:
            filepath = self._data_dir / "autosave_explosions.csv"
            self.export_to_csv(str(filepath))
            self._unsaved_count = 0
        except Exception as e:
            logger.error(f"Erro no auto-save: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    def clear(self) -> None:
        """Limpa todos os dados em memória."""
        with self._lock:
            self._explosions.clear()
            self._bets.clear()
            self._round_number = 0
            self._cache_valid = False
            self._session_stats = SessionStats(start_time=datetime.now().isoformat())

        logger.info("Dados limpos")

    @property
    def explosion_count(self) -> int:
        """Retorna quantidade de explosões."""
        return len(self._explosions)

    @property
    def bet_count(self) -> int:
        """Retorna quantidade de apostas."""
        return len(self._bets)

    def get_recent_explosions(self, limit: int = 10) -> List[float]:
        """Retorna últimas N explosões."""
        with self._lock:
            explosions = list(self._explosions)
        return [e.value for e in explosions[-limit:]]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_data_collector: Optional[DataCollector] = None
_collector_lock = threading.Lock()


def get_collector() -> DataCollector:
    """
    Retorna a instância singleton do DataCollector.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _data_collector

    if _data_collector is None:
        with _collector_lock:
            if _data_collector is None:
                _data_collector = DataCollector()

    return _data_collector


def reset_collector() -> None:
    """Reseta o coletor de dados (útil para testes)."""
    global _data_collector
    with _collector_lock:
        if _data_collector:
            _data_collector.clear()
        _data_collector = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO DATA COLLECTOR - CrashBot v3.0")
    print("=" * 60)

    # Cria coletor
    collector = DataCollector(emit_events=False)
    print(f"\n✅ DataCollector criado")

    # Simula explosões
    print(f"\n--- Simulando Explosões ---")
    import random

    test_values = []
    for _ in range(100):
        # Simula distribuição similar ao jogo real
        if random.random() < 0.6:  # 60% baixas
            value = random.uniform(1.0, 1.99)
        else:
            value = random.uniform(2.0, 10.0)
        test_values.append(round(value, 2))

    collector.add_explosions_bulk(test_values)
    print(f"   {collector.explosion_count} explosões adicionadas")

    # Estatísticas
    print(f"\n--- Estatísticas ---")
    stats = collector.get_statistics()
    print(f"   Total: {stats['total']}")
    print(f"   Média: {stats['mean']:.2f}")
    print(f"   Min: {stats['min']:.2f}")
    print(f"   Max: {stats['max']:.2f}")
    print(f"   Lows: {stats['lows_percent']:.1f}%")

    # Análise de streaks
    print(f"\n--- Análise de Streaks ---")
    streaks = collector.get_streak_analysis()
    print(f"   Total de streaks: {streaks['total_streaks']}")
    print(f"   Max streak: {streaks.get('max_streak', 0)}")
    print(f"   Média streak: {streaks.get('avg_streak', 0):.1f}")

    # Dados para LSTM
    print(f"\n--- Dados para LSTM ---")
    X, y = collector.get_training_data(sequence_length=20)
    if len(X) > 0:
        print(f"   X shape: {X.shape}")
        print(f"   y shape: {y.shape}")

    # Dados com features
    print(f"\n--- Dados com Features ---")
    X_feat, y_feat = collector.get_training_data_with_features(sequence_length=20)
    if len(X_feat) > 0:
        print(f"   X shape: {X_feat.shape}")
        print(f"   y shape: {y_feat.shape}")
        print(f"   Features: valor, is_low, rolling_mean, rolling_std, streak")

    # Estado para RL
    print(f"\n--- Estado para RL ---")
    state = collector.get_current_state(history_size=20)
    print(f"   State shape: {state.shape}")
    print(f"   State size: {collector.get_state_size()}")

    # Exportação
    print(f"\n--- Exportação ---")
    if collector.export_to_csv("data/test_export.csv"):
        print(f"   ✅ CSV exportado")
    if collector.export_to_json("data/test_export.json"):
        print(f"   ✅ JSON exportado")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
