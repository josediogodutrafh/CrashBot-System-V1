#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LEARNING ENGINE - O Cérebro Preditivo do Bot
Responsável por treinar, avaliar e fazer previsões com Machine Learning.
Utiliza TimeSeriesSplit para validação robusta.
"""

# ==============================================================================
# 1. IMPORTS DE BIBLIOTECAS PADRÃO
# ==============================================================================
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ==============================================================================
# 2. IMPORTS DE BIBLIOTECAS DE TERCEIROS (CORE)
# ==============================================================================
import joblib
import numpy as np
import pandas as pd

# ==============================================================================
# 3. IMPORTS DO SCIKIT-LEARN (FERRAMENTAS DE ML)
# ==============================================================================
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from src.config import DB_PATH, MODEL_PATH, SCALER_PATH

# Configuração do logger para este módulo
logger = logging.getLogger(__name__)

# ==============================================================================
# CONSTANTES GLOBAIS
# ==============================================================================
TARGET_MULTIPLIER: float = 2.0
N_SPLITS_CV: int = 5
MIN_SAMPLES_FOR_TRAINING: int = 100
REQUIRED_HISTORY_FOR_PREDICTION: int = 250


class LearningEngine:
    """
    Motor de Machine Learning para o bot, com validação por TimeSeriesSplit.
    """

    def __init__(self):
        """
        Inicializa o motor, definindo os caminhos a partir do config.py
        e carregando modelo/scaler.
        """
        self.model_path: Path = Path(MODEL_PATH)
        self.scaler_path: Path = Path(SCALER_PATH)

        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None

        self.load_model_and_scaler()

    def _load_data_from_db(self) -> pd.DataFrame:
        """Conecta ao banco de dados e carrega o histórico de rodadas."""
        db_path = str(DB_PATH)
        logger.info(f"Carregando dados de: {db_path}")
        try:
            with sqlite3.connect(db_path) as conn:
                query = """
                    SELECT timestamp, multiplicador
                    FROM multiplicadores_historico
                    ORDER BY timestamp ASC
                """
                df = pd.read_sql_query(query, conn, parse_dates=["timestamp"])
            df = df.set_index("timestamp").sort_index()
            logger.info(f"{len(df)} registros carregados.")
            return df
        except Exception as e:
            logger.error(
                f"Falha ao carregar dados do banco de dados: {e}", exc_info=True
            )
            return pd.DataFrame()

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforma dados brutos em features para o modelo."""
        logger.info("Iniciando engenharia de features (Janelas 5, 15, 30)...")
        df_featured = df.copy()

        # Features de Lag
        for i in range(1, 4):
            df_featured[f"lag_{i}"] = df_featured["multiplicador"].shift(i)

        # Features de Média Móvel e Desvio Padrão
        window_sizes = [20, 30, 50, 100, 250]

        for window_size in window_sizes:
            rolling_series = (
                df_featured["multiplicador"].shift(1).rolling(window=window_size)
            )
            df_featured[f"rolling_mean_{window_size}"] = rolling_series.mean()
            df_featured[f"rolling_std_{window_size}"] = rolling_series.std()

        # Feature de Streak
        is_low = df_featured["multiplicador"].shift(1) < TARGET_MULTIPLIER
        cumulative_lows = is_low.astype(int).cumsum()
        streak_breaks = cumulative_lows.where(~is_low)
        filled_breaks = streak_breaks.ffill().fillna(0)
        df_featured["low_streak"] = (cumulative_lows - filled_breaks).astype(int)

        # Alvo (target)
        df_featured["target"] = (
            df_featured["multiplicador"] >= TARGET_MULTIPLIER
        ).astype(int)

        df_featured = df_featured.dropna()

        logger.info(
            f"Engenharia de features concluída. {len(df_featured)} amostras válidas."
        )
        return df_featured

    def _split_features_target(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Separa o DataFrame em features (X) e alvo (y)."""
        features_to_exclude = ["timestamp", "multiplicador", "target"]
        features = [col for col in df.columns if col not in features_to_exclude]
        X = df[features]
        y = df["target"]
        logger.debug(f"Features selecionadas para X: {features}")
        logger.debug(f"Shape de X: {X.shape}, Shape de y: {y.shape}")
        return X, y

    def _evaluate_model(
        self, y_true: pd.Series, y_pred: np.ndarray, split_info: str = ""
    ) -> Dict[str, float]:
        """Mede a performance, exibe relatório e retorna métricas."""
        accuracy = accuracy_score(y_true, y_pred)
        report_text = classification_report(y_true, y_pred, zero_division=0)
        report_dict = classification_report(
            y_true, y_pred, output_dict=True, zero_division=0
        )

        logger.info(f"Acurácia {split_info}: {accuracy:.2%}")
        print(f"\n--- Relatório de Classificação ({split_info.strip()}) ---\n")
        print(report_text)
        print("-" * (len(split_info) + 41) + "\n")

        stats_hit_class: Dict[str, Any] = {}
        if isinstance(report_dict, dict):
            stats_hit_class = report_dict.get("1", {})

        precision_hit = 0.0
        recall_hit = 0.0

        if isinstance(stats_hit_class, dict):
            precision_hit = stats_hit_class.get("precision", 0.0)
            recall_hit = stats_hit_class.get("recall", 0.0)

        return {
            "accuracy": float(accuracy),
            "precision_hit": float(precision_hit),
            "recall_hit": float(recall_hit),
        }

    def train_model(self):
        """Orquestra o pipeline completo de treinamento e validação do modelo."""
        data = self._load_data_from_db()
        if len(data) < MIN_SAMPLES_FOR_TRAINING:
            logger.error(
                f"Dados insuficientes ({len(data)}/{MIN_SAMPLES_FOR_TRAINING})."
            )
            return

        featured_data = self._create_features(data)
        if featured_data.empty:
            logger.error("Falha ao criar features.")
            return

        X, y = self._split_features_target(featured_data)

        self.scaler = StandardScaler()
        self.scaler.fit(X)
        logger.info("StandardScaler foi treinado (fit).")
        self.save_scaler()

        logger.info(f"Iniciando Validação Cruzada com {N_SPLITS_CV} splits...")
        tscv = TimeSeriesSplit(n_splits=N_SPLITS_CV)
        model_cv = RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight="balanced"
        )
        all_metrics = []

        try:
            for split_count, (train_index, test_index) in enumerate(tscv.split(X), 1):
                X_train, X_test = X.iloc[train_index], X.iloc[test_index]
                y_train, y_test = y.iloc[train_index], y.iloc[test_index]

                model_cv.fit(X_train, y_train)
                y_pred_cv = model_cv.predict(X_test)

                split_metrics = self._evaluate_model(
                    y_test, y_pred_cv, f"(Split {split_count}/{N_SPLITS_CV})"
                )
                all_metrics.append(split_metrics["accuracy"])

            if all_metrics:
                logger.info("-" * 50)
                logger.info(
                    f"Validação Cruzada Concluída - Acurácia Média: {np.mean(all_metrics):.2%}"
                )
                logger.info("-" * 50)

        except Exception as e:
            logger.error(f"Erro durante a validação cruzada: {e}", exc_info=True)
            logger.warning("Prosseguindo com o treinamento no dataset completo...")

        logger.info("Iniciando treinamento final no dataset completo...")
        self.model = RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight="balanced"
        )
        self.model.fit(X, y)
        logger.info("Treinamento final concluído.")

        final_predictions = self.model.predict(X)
        final_metrics = self._evaluate_model(y, final_predictions, "(Treino Completo)")
        logger.info(f"Métricas de avaliação (treino completo): {final_metrics}")

        self.save_model()

    def predict(self, recent_history: List[float]) -> Optional[float]:
        """Faz uma previsão em tempo real."""
        if not self.model or not self.scaler:
            logger.debug("Modelo/Scaler não carregado.")
            return None

        if len(recent_history) < REQUIRED_HISTORY_FOR_PREDICTION:
            logger.debug(
                f"Histórico insuficiente ({len(recent_history)}/{REQUIRED_HISTORY_FOR_PREDICTION})."
            )
            return None

        try:
            live_data = pd.DataFrame({"multiplicador": recent_history})

            features_live = {
                f"lag_{i}": live_data["multiplicador"].iloc[-i] for i in range(1, 4)
            }

            window_sizes = [20, 30, 50, 100, 250]

            for window_size in window_sizes:
                rolling_window = live_data["multiplicador"].rolling(window=window_size)
                features_live[f"rolling_mean_{window_size}"] = (
                    rolling_window.mean().iloc[-1]
                )
                features_live[f"rolling_std_{window_size}"] = rolling_window.std().iloc[
                    -1
                ]

            # Streak
            is_low = live_data["multiplicador"] < TARGET_MULTIPLIER
            cumulative_lows = is_low.astype(int).cumsum()
            streak_breaks = cumulative_lows.where(~is_low)
            filled_breaks = streak_breaks.ffill().fillna(0)
            last_low_streak = (cumulative_lows - filled_breaks).astype(int).iloc[-1]

            features_live["low_streak"] = last_low_streak

            X_live = pd.DataFrame([features_live])
            X_live = X_live.fillna(0)

            try:
                X_live = X_live[self.model.feature_names_in_]
            except AttributeError:
                logger.error("Modelo sem 'feature_names_in_'. Verifique versão/tipo.")
                return None
            except KeyError as e:
                logger.error(f"Feature ausente ao vivo: {e}")
                return None

            probability = self.model.predict_proba(X_live)[0][1]
            return float(probability)

        except Exception as e:
            logger.error(f"Erro durante a previsão: {e}", exc_info=True)
            return None

    def save_scaler(self):
        """Salva o objeto scaler em disco."""
        if self.scaler:
            self.scaler_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                joblib.dump(self.scaler, self.scaler_path)
                logger.info(f"Scaler salvo em: {self.scaler_path}")
            except Exception as e:
                logger.error(f"Erro ao salvar scaler: {e}", exc_info=True)
        else:
            logger.warning("Scaler não está treinado. Nada para salvar.")

    def save_model(self):
        """Salva o modelo treinado em disco."""
        if self.model:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                joblib.dump(self.model, self.model_path)
                logger.info(f"Modelo salvo em: {self.model_path}")
            except Exception as e:
                logger.error(f"Erro ao salvar modelo: {e}", exc_info=True)
        else:
            logger.warning("Modelo não está treinado. Nada para salvar.")

    def load_model_and_scaler(self):
        """Carrega modelo e scaler salvos."""
        model_loaded, scaler_loaded = False, False
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Modelo carregado de: {self.model_path}")
                model_loaded = True
            except Exception as e:
                logger.error(f"Erro ao carregar modelo salvo ({self.model_path}): {e}")
                self.model = None

        if self.scaler_path.exists():
            try:
                self.scaler = joblib.load(self.scaler_path)
                logger.info(f"Scaler carregado de: {self.scaler_path}")
                scaler_loaded = True
            except Exception as e:
                logger.error(f"Erro ao carregar scaler salvo ({self.scaler_path}): {e}")
                self.scaler = None

        if not model_loaded or not scaler_loaded:
            logger.info("Modelo ou scaler não encontrado/carregado.")
