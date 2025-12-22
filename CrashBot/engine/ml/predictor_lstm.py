#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - PREDITOR LSTM

Rede neural LSTM para prever comportamento de explosões.
Pode prever valor aproximado ou classificar (alta/baixa).

Uso:
    from engine.ml.predictor_lstm import LSTMPredictor, get_predictor

    predictor = get_predictor()

    # Treina com dados históricos
    predictor.train(X_train, y_train, epochs=100)

    # Faz previsão
    prediction = predictor.predict(last_20_explosions)

    # Salva/Carrega modelo
    predictor.save_model("models/lstm_v1.pt")
    predictor.load_model("models/lstm_v1.pt")
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# PyTorch imports
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None
    nn = None

# Core imports
from core.events import BotEvent, emit

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════


class PredictionMode(Enum):
    """Modos de predição."""

    REGRESSION = "regression"  # Prevê valor numérico
    CLASSIFICATION = "classification"  # Prevê alta/baixa


class PredictionResult(Enum):
    """Resultado da classificação."""

    LOW = "low"  # Explosão baixa (< threshold)
    HIGH = "high"  # Explosão alta (>= threshold)
    UNCERTAIN = "uncertain"  # Confiança baixa


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Prediction:
    """Resultado de uma predição."""

    value: float  # Valor previsto ou probabilidade
    confidence: float  # Confiança (0-1)
    classification: PredictionResult  # LOW, HIGH ou UNCERTAIN
    raw_output: Any = None  # Saída bruta da rede

    @property
    def is_low(self) -> bool:
        """Retorna True se prevê explosão baixa."""
        return self.classification == PredictionResult.LOW

    @property
    def is_confident(self) -> bool:
        """Retorna True se confiança é alta."""
        return self.confidence >= 0.7


@dataclass
class TrainingMetrics:
    """Métricas de treinamento."""

    epoch: int
    train_loss: float
    val_loss: Optional[float] = None
    accuracy: Optional[float] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# MODELO LSTM
# ═══════════════════════════════════════════════════════════════════════════════

if HAS_TORCH:

    class LSTMModel(nn.Module):
        """
        Rede LSTM para previsão de séries temporais.

        Arquitetura:
        - LSTM layers com dropout
        - Fully connected layers
        - Output: regressão ou classificação
        """

        def __init__(
            self,
            input_size: int = 1,
            hidden_size: int = 64,
            num_layers: int = 2,
            output_size: int = 1,
            dropout: float = 0.2,
            bidirectional: bool = False,
        ):
            super().__init__()

            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.bidirectional = bidirectional
            self.num_directions = 2 if bidirectional else 1

            # LSTM
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
                bidirectional=bidirectional,
            )

            # Fully connected
            fc_input_size = hidden_size * self.num_directions
            self.fc = nn.Sequential(
                nn.Linear(fc_input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_size, output_size),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Forward pass."""
            # x shape: (batch, sequence, features)

            # LSTM
            lstm_out, (h_n, c_n) = self.lstm(x)

            # Usa último hidden state
            if self.bidirectional:
                # Concatena forward e backward
                hidden = torch.cat((h_n[-2], h_n[-1]), dim=1)
            else:
                hidden = h_n[-1]

            # Fully connected
            out = self.fc(hidden)

            return out

    class AttentionLSTMModel(nn.Module):
        """
        LSTM com mecanismo de atenção.

        Permite que o modelo foque em partes específicas da sequência.
        """

        def __init__(
            self,
            input_size: int = 1,
            hidden_size: int = 64,
            num_layers: int = 2,
            output_size: int = 1,
            dropout: float = 0.2,
        ):
            super().__init__()

            self.hidden_size = hidden_size
            self.num_layers = num_layers

            # LSTM
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
            )

            # Attention
            self.attention = nn.Sequential(
                nn.Linear(hidden_size, hidden_size),
                nn.Tanh(),
                nn.Linear(hidden_size, 1),
            )

            # Output
            self.fc = nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_size // 2, output_size),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Forward pass com atenção."""
            # LSTM
            lstm_out, _ = self.lstm(x)
            # lstm_out shape: (batch, sequence, hidden)

            # Attention weights
            attn_weights = self.attention(lstm_out)
            attn_weights = torch.softmax(attn_weights, dim=1)
            # attn_weights shape: (batch, sequence, 1)

            # Weighted sum
            context = torch.sum(attn_weights * lstm_out, dim=1)
            # context shape: (batch, hidden)

            # Output
            out = self.fc(context)

            return out


# ═══════════════════════════════════════════════════════════════════════════════
# LSTM PREDICTOR
# ═══════════════════════════════════════════════════════════════════════════════


class LSTMPredictor:
    """
    Preditor baseado em LSTM.

    Features:
        - Suporta regressão e classificação
        - Atenção opcional
        - Treinamento com validação
        - Early stopping
        - Salvar/carregar modelos
        - Normalização automática

    Exemplo:
        predictor = LSTMPredictor(mode=PredictionMode.CLASSIFICATION)

        # Treina
        metrics = predictor.train(X, y, epochs=100, val_split=0.2)

        # Prediz
        prediction = predictor.predict(sequence)
        if prediction.is_low and prediction.is_confident:
            print("Alta probabilidade de explosão baixa!")
    """

    def __init__(
        self,
        mode: PredictionMode = PredictionMode.CLASSIFICATION,
        input_size: int = 1,
        hidden_size: int = 64,
        num_layers: int = 2,
        sequence_length: int = 20,
        threshold: float = 2.0,
        use_attention: bool = True,
        device: Optional[str] = None,
    ):
        """
        Inicializa o preditor.

        Args:
            mode: Modo de predição (regression/classification)
            input_size: Número de features por timestep
            hidden_size: Tamanho do hidden state do LSTM
            num_layers: Número de camadas LSTM
            sequence_length: Tamanho da sequência de entrada
            threshold: Limiar para classificação (baixa/alta)
            use_attention: Se True, usa modelo com atenção
            device: Device para PyTorch ("cuda" ou "cpu")
        """
        if not HAS_TORCH:
            raise ImportError("PyTorch não encontrado. Instale com: pip install torch")

        self._lock = threading.Lock()

        # Configurações
        self._mode = mode
        self._input_size = input_size
        self._hidden_size = hidden_size
        self._num_layers = num_layers
        self._sequence_length = sequence_length
        self._threshold = threshold
        self._use_attention = use_attention

        # Device
        if device:
            self._device = torch.device(device)
        else:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Output size
        output_size = 1 if mode == PredictionMode.REGRESSION else 2

        # Modelo
        if use_attention:
            self._model = AttentionLSTMModel(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                output_size=output_size,
            )
        else:
            self._model = LSTMModel(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                output_size=output_size,
            )

        self._model.to(self._device)

        # Normalização
        self._mean: Optional[float] = None
        self._std: Optional[float] = None

        # Histórico de treino
        self._training_history: List[TrainingMetrics] = []
        self._is_trained = False

        logger.info(
            f"LSTMPredictor inicializado: mode={mode.value}, "
            f"device={self._device}, attention={use_attention}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # TREINAMENTO
    # ═══════════════════════════════════════════════════════════════════════════

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        val_split: float = 0.2,
        early_stopping_patience: int = 10,
        verbose: bool = True,
    ) -> List[TrainingMetrics]:
        """
        Treina o modelo.

        Args:
            X: Dados de entrada (num_samples, sequence_length, features)
            y: Labels (num_samples,)
            epochs: Número de épocas
            batch_size: Tamanho do batch
            learning_rate: Taxa de aprendizado
            val_split: Fração para validação
            early_stopping_patience: Épocas sem melhora para parar
            verbose: Se True, mostra progresso

        Returns:
            Lista de métricas por época
        """
        with self._lock:
            # Normaliza dados
            self._mean = float(np.mean(X))
            self._std = float(np.std(X))
            if self._std > 0:
                X_norm = (X - self._mean) / self._std
            else:
                X_norm = X - self._mean

            # Converte para tensores
            X_tensor = torch.FloatTensor(X_norm).to(self._device)

            if self._mode == PredictionMode.CLASSIFICATION:
                y_tensor = torch.LongTensor(y).to(self._device)
            else:
                y_tensor = torch.FloatTensor(y).to(self._device)

            # Split treino/validação
            val_size = int(len(X_tensor) * val_split)
            train_size = len(X_tensor) - val_size

            indices = torch.randperm(len(X_tensor))
            train_indices = indices[:train_size]
            val_indices = indices[train_size:]

            X_train, y_train = X_tensor[train_indices], y_tensor[train_indices]
            X_val, y_val = X_tensor[val_indices], y_tensor[val_indices]

            # DataLoaders
            train_dataset = TensorDataset(X_train, y_train)
            train_loader = DataLoader(
                train_dataset, batch_size=batch_size, shuffle=True
            )

            # Loss e optimizer
            if self._mode == PredictionMode.CLASSIFICATION:
                criterion = nn.CrossEntropyLoss()
            else:
                criterion = nn.MSELoss()

            optimizer = optim.Adam(self._model.parameters(), lr=learning_rate)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode="min", factor=0.5, patience=5
            )

            # Early stopping
            best_val_loss = float("inf")
            patience_counter = 0
            best_model_state = None

            # Training loop
            self._training_history = []

            for epoch in range(epochs):
                # Train
                self._model.train()
                train_loss = 0.0

                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()

                    outputs = self._model(batch_X)

                    if self._mode == PredictionMode.REGRESSION:
                        outputs = outputs.squeeze()

                    loss = criterion(outputs, batch_y)
                    loss.backward()

                    # Gradient clipping
                    torch.nn.utils.clip_grad_norm_(
                        self._model.parameters(), max_norm=1.0
                    )

                    optimizer.step()
                    train_loss += loss.item()

                train_loss /= len(train_loader)

                # Validation
                self._model.eval()
                with torch.no_grad():
                    val_outputs = self._model(X_val)

                    if self._mode == PredictionMode.REGRESSION:
                        val_outputs = val_outputs.squeeze()

                    val_loss = criterion(val_outputs, y_val).item()

                    # Accuracy para classificação
                    accuracy = None
                    if self._mode == PredictionMode.CLASSIFICATION:
                        _, predicted = torch.max(val_outputs, 1)
                        accuracy = (predicted == y_val).float().mean().item()

                # Learning rate scheduling
                scheduler.step(val_loss)

                # Métricas
                metrics = TrainingMetrics(
                    epoch=epoch + 1,
                    train_loss=train_loss,
                    val_loss=val_loss,
                    accuracy=accuracy,
                )
                self._training_history.append(metrics)

                if verbose and (epoch + 1) % 10 == 0:
                    acc_str = f", acc={accuracy:.4f}" if accuracy else ""
                    print(
                        f"Epoch {epoch+1}/{epochs} - train_loss={train_loss:.4f}, val_loss={val_loss:.4f}{acc_str}"
                    )

                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_model_state = self._model.state_dict().copy()
                else:
                    patience_counter += 1
                    if patience_counter >= early_stopping_patience:
                        if verbose:
                            print(f"Early stopping na época {epoch+1}")
                        break

            # Restaura melhor modelo
            if best_model_state:
                self._model.load_state_dict(best_model_state)

            self._is_trained = True

            logger.info(
                f"Treino concluído: {len(self._training_history)} épocas, best_val_loss={best_val_loss:.4f}"
            )

            return self._training_history

    # ═══════════════════════════════════════════════════════════════════════════
    # PREDIÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def predict(self, sequence: Union[np.ndarray, List[float]]) -> Prediction:
        """
        Faz predição para uma sequência.

        Args:
            sequence: Sequência de explosões (últimos N valores)

        Returns:
            Prediction com valor, confiança e classificação
        """
        if not self._is_trained:
            logger.warning("Modelo não treinado!")
            return Prediction(
                value=0.0,
                confidence=0.0,
                classification=PredictionResult.UNCERTAIN,
            )

        with self._lock:
            # Prepara input
            if isinstance(sequence, list):
                sequence = np.array(sequence)

            # Ajusta tamanho
            if len(sequence) < self._sequence_length:
                padding = np.zeros(self._sequence_length - len(sequence))
                sequence = np.concatenate([padding, sequence])
            elif len(sequence) > self._sequence_length:
                sequence = sequence[-self._sequence_length :]

            # Normaliza
            if self._std and self._std > 0:
                sequence_norm = (sequence - self._mean) / self._std
            else:
                sequence_norm = sequence - (self._mean or 0)

            # Reshape para (1, sequence, features)
            X = sequence_norm.reshape(1, self._sequence_length, self._input_size)
            X_tensor = torch.FloatTensor(X).to(self._device)

            # Predição
            self._model.eval()
            with torch.no_grad():
                output = self._model(X_tensor)

            # Processa output
            if self._mode == PredictionMode.CLASSIFICATION:
                probabilities = torch.softmax(output, dim=1)
                prob_low = probabilities[0, 0].item()  # Classe 0 = baixa
                prob_high = probabilities[0, 1].item()  # Classe 1 = alta

                confidence = max(prob_low, prob_high)

                if confidence < 0.6:
                    classification = PredictionResult.UNCERTAIN
                elif prob_low > prob_high:
                    classification = PredictionResult.LOW
                else:
                    classification = PredictionResult.HIGH

                value = prob_low  # Probabilidade de ser baixa

            else:  # REGRESSION
                value = output[0, 0].item()

                # Desnormaliza
                if self._std and self._std > 0:
                    value = value * self._std + self._mean
                else:
                    value = value + (self._mean or 0)

                # Classifica baseado no threshold
                if value < self._threshold:
                    classification = PredictionResult.LOW
                else:
                    classification = PredictionResult.HIGH

                # Confiança baseada na distância do threshold
                distance = abs(value - self._threshold)
                confidence = min(1.0, distance / 2.0)

            return Prediction(
                value=value,
                confidence=confidence,
                classification=classification,
                raw_output=output.cpu().numpy(),
            )

    def predict_batch(self, sequences: np.ndarray) -> List[Prediction]:
        """
        Faz predições para múltiplas sequências.

        Args:
            sequences: Array (num_samples, sequence_length, features)

        Returns:
            Lista de Predictions
        """
        predictions = []

        for i in range(len(sequences)):
            seq = sequences[i, :, 0] if sequences.ndim == 3 else sequences[i]
            pred = self.predict(seq)
            predictions.append(pred)

        return predictions

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTÊNCIA
    # ═══════════════════════════════════════════════════════════════════════════

    def save_model(self, filepath: str) -> bool:
        """
        Salva o modelo treinado.

        Args:
            filepath: Caminho do arquivo .pt

        Returns:
            True se salvou com sucesso
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            state = {
                "model_state_dict": self._model.state_dict(),
                "mean": self._mean,
                "std": self._std,
                "mode": self._mode.value,
                "input_size": self._input_size,
                "hidden_size": self._hidden_size,
                "num_layers": self._num_layers,
                "sequence_length": self._sequence_length,
                "threshold": self._threshold,
                "use_attention": self._use_attention,
                "is_trained": self._is_trained,
                "training_history": [
                    {
                        "epoch": m.epoch,
                        "train_loss": m.train_loss,
                        "val_loss": m.val_loss,
                        "accuracy": m.accuracy,
                    }
                    for m in self._training_history
                ],
            }

            torch.save(state, filepath)
            logger.info(f"Modelo salvo em: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """
        Carrega um modelo salvo.

        Args:
            filepath: Caminho do arquivo .pt

        Returns:
            True se carregou com sucesso
        """
        try:
            state = torch.load(filepath, map_location=self._device)

            self._model.load_state_dict(state["model_state_dict"])
            self._mean = state.get("mean")
            self._std = state.get("std")
            self._is_trained = state.get("is_trained", True)

            logger.info(f"Modelo carregado de: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def is_trained(self) -> bool:
        """Verifica se o modelo está treinado."""
        return self._is_trained

    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações do modelo."""
        total_params = sum(p.numel() for p in self._model.parameters())
        trainable_params = sum(
            p.numel() for p in self._model.parameters() if p.requires_grad
        )

        return {
            "mode": self._mode.value,
            "input_size": self._input_size,
            "hidden_size": self._hidden_size,
            "num_layers": self._num_layers,
            "sequence_length": self._sequence_length,
            "threshold": self._threshold,
            "use_attention": self._use_attention,
            "device": str(self._device),
            "is_trained": self._is_trained,
            "total_params": total_params,
            "trainable_params": trainable_params,
            "training_epochs": len(self._training_history),
        }

    def get_training_history(self) -> List[Dict[str, Any]]:
        """Retorna histórico de treinamento."""
        return [
            {
                "epoch": m.epoch,
                "train_loss": m.train_loss,
                "val_loss": m.val_loss,
                "accuracy": m.accuracy,
            }
            for m in self._training_history
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_lstm_predictor: Optional[LSTMPredictor] = None
_predictor_lock = threading.Lock()


def get_predictor(**kwargs) -> LSTMPredictor:
    """
    Retorna a instância singleton do LSTMPredictor.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _lstm_predictor

    if _lstm_predictor is None:
        with _predictor_lock:
            if _lstm_predictor is None:
                _lstm_predictor = LSTMPredictor(**kwargs)

    return _lstm_predictor


def reset_predictor() -> None:
    """Reseta o preditor (útil para testes)."""
    global _lstm_predictor
    with _predictor_lock:
        _lstm_predictor = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO LSTM PREDICTOR - CrashBot v3.0")
    print("=" * 60)

    if not HAS_TORCH:
        print("❌ PyTorch não instalado!")
        exit(1)

    print(f"\n✅ PyTorch disponível")
    print(f"   Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")

    # Cria preditor
    predictor = LSTMPredictor(
        mode=PredictionMode.CLASSIFICATION,
        hidden_size=32,
        num_layers=1,
        sequence_length=20,
        use_attention=True,
    )

    print(f"\n✅ LSTMPredictor criado")
    info = predictor.get_model_info()
    for key, value in info.items():
        print(f"   {key}: {value}")

    # Gera dados sintéticos para teste
    print(f"\n--- Gerando Dados Sintéticos ---")
    import random

    num_samples = 1000
    sequence_length = 20

    # Gera sequências
    X = []
    y = []

    for _ in range(num_samples):
        # Gera sequência
        seq = []
        for _ in range(sequence_length):
            if random.random() < 0.6:
                seq.append(random.uniform(1.0, 1.99))
            else:
                seq.append(random.uniform(2.0, 10.0))

        # Próximo valor (target)
        next_val = (
            random.uniform(1.0, 1.99)
            if random.random() < 0.6
            else random.uniform(2.0, 10.0)
        )

        X.append(seq)
        y.append(0 if next_val < 2.0 else 1)  # 0 = baixa, 1 = alta

    X = np.array(X, dtype=np.float32).reshape(num_samples, sequence_length, 1)
    y = np.array(y, dtype=np.int64)

    print(f"   X shape: {X.shape}")
    print(f"   y shape: {y.shape}")
    print(f"   Classes: {np.bincount(y)}")

    # Treina
    print(f"\n--- Treinamento ---")
    metrics = predictor.train(
        X,
        y,
        epochs=50,
        batch_size=32,
        val_split=0.2,
        early_stopping_patience=10,
        verbose=True,
    )

    print(f"\n   Épocas treinadas: {len(metrics)}")
    if metrics:
        final = metrics[-1]
        print(f"   Loss final: {final.train_loss:.4f}")
        if final.accuracy:
            print(f"   Accuracy final: {final.accuracy:.4f}")

    # Teste de predição
    print(f"\n--- Teste de Predição ---")

    test_sequences = [
        [
            1.2,
            1.5,
            1.3,
            1.8,
            1.4,
            1.6,
            1.9,
            1.2,
            1.5,
            1.3,
            1.8,
            1.4,
            1.6,
            1.9,
            1.2,
            1.5,
            1.3,
            1.8,
            1.4,
            1.6,
        ],  # Muitas baixas
        [
            3.2,
            2.5,
            4.3,
            2.8,
            3.4,
            2.6,
            5.9,
            2.2,
            3.5,
            2.3,
            4.8,
            3.4,
            2.6,
            5.9,
            3.2,
            2.5,
            4.3,
            2.8,
            3.4,
            2.6,
        ],  # Muitas altas
    ]

    for i, seq in enumerate(test_sequences):
        pred = predictor.predict(seq)
        print(f"\n   Sequência {i+1}:")
        print(f"      Classificação: {pred.classification.value}")
        print(f"      Confiança: {pred.confidence:.2%}")
        print(f"      Prob. baixa: {pred.value:.2%}")

    # Salva modelo
    print(f"\n--- Persistência ---")
    if predictor.save_model("models/test_lstm.pt"):
        print(f"   ✅ Modelo salvo")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
