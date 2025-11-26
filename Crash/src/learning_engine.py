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

# CORREÇÃO F401: TimeSeriesSplit será utilizado agora.
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from config import DB_PATH, MODEL_PATH, SCALER_PATH

# Configuração do logger para este módulo
logger = logging.getLogger(__name__)

# ==============================================================================
# CONSTANTES GLOBAIS
# ==============================================================================
# CORREÇÃO E501: Quebrado para legibilidade
TARGET_MULTIPLIER: float = 2.0
N_SPLITS_CV: int = 5
MIN_SAMPLES_FOR_TRAINING: int = 100

# (--- MUDANÇA AQUI ---)
# Define o número mínimo de histórico necessário para fazer uma previsão.
REQUIRED_HISTORY_FOR_PREDICTION: int = 250


class LearningEngine:
    """
    Motor de Machine Learning para o bot, com validação por TimeSeriesSplit.
    """

    # MÉTODO __init__ NOVO (Substitua o antigo por este)
    def __init__(self):
        """
        Inicializa o motor, definindo os caminhos a partir do config.py
        e carregando modelo/scaler.
        """
        # A lógica de 'project_root' foi removida pois não funciona no .exe

        # Usamos os caminhos importados do config.py
        # O 'Path()' garante que eles sejam objetos Path, como o resto
        # do seu código espera.
        self.model_path: Path = Path(MODEL_PATH)
        self.scaler_path: Path = Path(SCALER_PATH)

        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None

        self.load_model_and_scaler()

    def _load_data_from_db(self) -> pd.DataFrame:
        """Conecta ao banco de dados e carrega o histórico de rodadas."""
        db_path = DB_PATH
        logger.info(f"Carregando dados de: {db_path}")
        try:
            with sqlite3.connect(db_path) as conn:
                query = """
                    SELECT timestamp, multiplicador
                    FROM multiplicadores_historico
                    ORDER BY timestamp ASC
                """
                # parse_dates é crucial para o TimeSeriesSplit funcionar bem
                df = pd.read_sql_query(query, conn, parse_dates=["timestamp"])
            # Garante que o índice seja o timestamp para operações temporais
            df = df.set_index("timestamp").sort_index()
            logger.info(f"{len(df)} registros carregados.")
            return df
        except Exception as e:
            # CORREÇÃO E501: Mensagem de erro quebrada
            logger.error(
                f"Falha ao carregar dados do banco de dados: {e}", exc_info=True
            )
            return pd.DataFrame()

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforma dados brutos em features para o modelo."""
        # (--- MUDANÇA AQUI ---)
        logger.info("Iniciando engenharia de features (Janelas 5, 15, 30)...")
        # CORREÇÃO Sourcery: Evitar inplace=True, usar atribuição
        df_featured = df.copy()

        # Features de Lag
        for i in range(1, 4):
            df_featured[f"lag_{i}"] = df_featured["multiplicador"].shift(i)

        # (--- MUDANÇA AQUI ---)
        # Features de Média Móvel e Desvio Padrão (Janelas Ampliadas)
        window_sizes = [20, 30, 50, 100, 250]

        for window_size in window_sizes:
            # shift(1) garante que usamos apenas dados passados para prever o futuro
            rolling_series = (
                df_featured["multiplicador"].shift(1).rolling(window=window_size)
            )
            df_featured[f"rolling_mean_{window_size}"] = rolling_series.mean()
            df_featured[f"rolling_std_{window_size}"] = rolling_series.std()
        # (--- FIM DA MUDANÇA ---)

        # Feature de Streak (contagem de baixos consecutivos)
        is_low = df_featured["multiplicador"].shift(1) < TARGET_MULTIPLIER
        # CORREÇÃO Pylance & Refatoração: Lógica de streak mais robusta
        # Calcula a soma cumulativa de 'is_low'
        # Converte True/False para 1/0 ANTES de somar
        cumulative_lows = is_low.astype(int).cumsum()
        # Encontra os pontos onde a streak é quebrada (não é 'low')
        streak_breaks = cumulative_lows.where(~is_low)
        # Preenche os valores NaN (onde a streak continua) com o último valor válido
        filled_breaks = streak_breaks.ffill().fillna(0)
        # Subtrai para obter a contagem da streak atual
        df_featured["low_streak"] = (cumulative_lows - filled_breaks).astype(int)

        # Alvo (target)
        df_featured["target"] = (
            df_featured["multiplicador"] >= TARGET_MULTIPLIER
        ).astype(int)

        # Remove linhas com NaN resultantes dos shifts/rollings
        # (Isto agora removerá as primeiras 30 linhas)
        df_featured = df_featured.dropna()

        # CORREÇÃO E501: Mensagem de log quebrada
        logger.info(
            f"Engenharia de features concluída. {len(df_featured)} amostras válidas."
        )
        return df_featured

    # USO DE TUPLE: Devolve uma tupla com DataFrame e Series
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

    # USO DE DICT: Retorna um dicionário com as métricas
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

        # Define stats_hit_class ANTES do if/else com dica de tipo
        stats_hit_class: Dict[str, Any] = {}
        if isinstance(report_dict, dict):
            stats_hit_class = report_dict.get("1", {})
        else:
            logger.warning(f"report_dict não é um dicionário, mas {type(report_dict)}")

        precision_hit = 0.0
        recall_hit = 0.0

        # Verificação explícita
        if isinstance(stats_hit_class, dict):
            # USA # type: ignore para silenciar o falso positivo persistente do Pylance
            precision_hit = stats_hit_class.get("precision", 0.0)
            recall_hit = stats_hit_class.get("recall", 0.0)
        else:
            logger.warning(
                f"Esperado dict para stats da classe '1', recebeu {type(stats_hit_class)}"
            )

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

        # --- Escalar os dados (APENAS FIT, NÃO TRANSFORM) ---
        # RandomForest não precisa de scaling, mas vamos salvar o scaler
        # caso outro modelo precise no futuro.
        self.scaler = StandardScaler()
        self.scaler.fit(X)  # Apenas "aprende" os dados (com nomes)
        logger.info("StandardScaler foi treinado (fit).")
        self.save_scaler()  # Salva o scaler treinado

        # NOTA: NÃO VAMOS USAR 'X_scaled'. Vamos usar 'X' (o DataFrame)
        #       diretamente, para que o modelo aprenda os 'feature_names_in_'.

        # --- Validação Cruzada com TimeSeriesSplit ---
        logger.info(f"Iniciando Validação Cruzada com {N_SPLITS_CV} splits...")
        tscv = TimeSeriesSplit(n_splits=N_SPLITS_CV)
        model_cv = RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight="balanced"
        )
        all_metrics = []

        # --- INÍCIO DO BLOCO TRY/EXCEPT CORRIGIDO ---
        try:
            # --- MUDANÇA AQUI: tscv.split(X), não X_scaled ---
            for split_count, (train_index, test_index) in enumerate(tscv.split(X), 1):
                # --- MUDANÇA AQUI: .iloc[train_index] ---
                X_train, X_test = X.iloc[train_index], X.iloc[test_index]
                y_train, y_test = y.iloc[train_index], y.iloc[test_index]

                model_cv.fit(X_train, y_train)
                y_pred_cv = model_cv.predict(X_test)

                # --- LÓGICA DO TRY (Que estava faltando) ---
                split_metrics = self._evaluate_model(
                    y_test, y_pred_cv, f"(Split {split_count}/{N_SPLITS_CV})"
                )
                all_metrics.append(
                    split_metrics["accuracy"]
                )  # Guarda acurácia do split

            if all_metrics:
                logger.info("-" * 50)
                logger.info(
                    f"Validação Cruzada Concluída - Acurácia Média: {np.mean(all_metrics):.2%}"
                )
                logger.info("-" * 50)
            else:
                logger.warning("Nenhuma métrica coletada da validação cruzada.")

        except Exception as e:
            # --- A "SUTURA" (O BLOCO EXCEPT QUE FALTAVA) ---
            logger.error(f"Erro durante a validação cruzada: {e}", exc_info=True)
            logger.warning("Prosseguindo com o treinamento no dataset completo...")
        # --- FIM DO BLOCO TRY/EXCEPT CORRIGIDO ---

        # --- Treinamento Final no Dataset Completo ---
        # (Esta era a linha 257 que dava o erro)
        logger.info("Iniciando treinamento final no dataset completo...")
        self.model = RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight="balanced"
        )
        # --- MUDANÇA AQUI: model.fit(X, y), não X_scaled ---
        self.model.fit(X, y)
        logger.info("Treinamento final concluído.")

        # Avaliação final no conjunto de treino (apenas para referência)
        # --- MUDANÇA AQUI: model.predict(X), não X_scaled ---
        final_predictions = self.model.predict(X)
        final_metrics = self._evaluate_model(y, final_predictions, "(Treino Completo)")
        logger.info(f"Métricas de avaliação (treino completo): {final_metrics}")

        # Salva o modelo final treinado
        self.save_model()

    def predict(self, recent_history: List[float]) -> Optional[float]:
        """Faz uma previsão em tempo real."""
        if not self.model or not self.scaler:
            logger.debug("Modelo/Scaler não carregado.")
            return None

        if len(recent_history) < REQUIRED_HISTORY_FOR_PREDICTION:
            # CORREÇÃO E501: Mensagem quebrada
            logger.debug(
                f"Histórico insuficiente ({len(recent_history)}/{REQUIRED_HISTORY_FOR_PREDICTION})."
            )
            return None

        # O 'try' DEVE estar neste nível de indentação
        try:
            # --- Recriação de Features Ao Vivo ---
            # (Todo este bloco DEVE estar indentado dentro do 'try')
            live_data = pd.DataFrame({"multiplicador": recent_history})

            features_live = {
                f"lag_{i}": live_data["multiplicador"].iloc[-i] for i in range(1, 4)
            }

            # (--- MUDANÇA AQUI ---)
            # Rolling (Janelas 20, 30, 50, 100, 250)
            window_sizes = [20, 30, 50, 100, 250]

            for window_size in window_sizes:
                # A guarda (if) no início da função garante que temos 30 de histórico
                rolling_window = live_data["multiplicador"].rolling(window=window_size)
                features_live[f"rolling_mean_{window_size}"] = (
                    rolling_window.mean().iloc[-1]
                )
                features_live[f"rolling_std_{window_size}"] = rolling_window.std().iloc[
                    -1
                ]

            # Streak
            is_low = live_data["multiplicador"] < TARGET_MULTIPLIER
            # CORREÇÃO E111, E117: Indentação
            # Converte True/False para 1/0 ANTES de somar
            cumulative_lows = is_low.astype(int).cumsum()
            # CORREÇÃO E111: Indentação
            streak_breaks = cumulative_lows.where(~is_low)
            # CORREÇÃO E501, E111, E117: Linha quebrada e indentação
            filled_breaks = streak_breaks.ffill().fillna(0)
            # CORREÇÃO E111: Indentação
            last_low_streak = (cumulative_lows - filled_breaks).astype(int).iloc[-1]

            features_live["low_streak"] = last_low_streak

            X_live = pd.DataFrame([features_live])

            # --- CORREÇÃO DO CRASH (NaN) ---
            # Substitui quaisquer NaNs (de janelas não preenchidas) por 0
            X_live = X_live.fillna(0)
            # --- FIM DA CORREÇÃO ---

            # O 'try' interno DEVE estar indentado aqui
            try:
                # CORREÇÃO E261, E501: Espaço antes do comentário e linha quebrada
                X_live = X_live[self.model.feature_names_in_]  # Garante a ordem correta
            except AttributeError:
                # CORREÇÃO E501: Mensagem quebrada
                logger.error("Modelo sem 'feature_names_in_'. Verifique versão/tipo.")
                return None
            except KeyError as e:
                logger.error(f"Feature ausente ao vivo: {e}")
                return None

            # --- Previsão ---
            # O modelo foi treinado em dados não escalados, então
            # prevemos com dados não escalados.
            # X_live_scaled = self.scaler.transform(X_live) # LINHA REMOVIDA

            probability = self.model.predict_proba(X_live)[0][
                1
            ]  # Probabilidade da classe 1 (Hit)

            return float(probability)

        # O 'except' DEVE estar alinhado com o 'try' principal
        except Exception as e:
            # CORREÇÃO E501: Mensagem de erro quebrada
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
                # CORREÇÃO E501: Mensagem de erro quebrada
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
                # CORREÇÃO E501: Mensagem de erro quebrada
                logger.error(f"Erro ao salvar modelo: {e}", exc_info=True)
        else:
            logger.warning("Modelo não está treinado. Nada para salvar.")

    # Renomeado para clareza
    def load_model_and_scaler(self):
        """Carrega modelo e scaler salvos."""
        model_loaded, scaler_loaded = False, False
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Modelo carregado de: {self.model_path}")
                model_loaded = True
            except Exception as e:
                # CORREÇÃO E501: Mensagem de erro quebrada
                logger.error(f"Erro ao carregar modelo salvo ({self.model_path}): {e}")
                self.model = None

        if self.scaler_path.exists():
            try:
                self.scaler = joblib.load(self.scaler_path)
                logger.info(f"Scaler carregado de: {self.scaler_path}")
                scaler_loaded = True
            except Exception as e:
                # CORREÇÃO E114, E117, E501: Indentação e linha quebrada
                logger.error(f"Erro ao carregar scaler salvo ({self.scaler_path}): {e}")
                self.scaler = None

        if not model_loaded or not scaler_loaded:
            # CORREÇÃO E114, E117, W291: Indentação e espaço extra
            logger.info("Modelo ou scaler não encontrado/carregado.")
