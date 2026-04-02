#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - OTIMIZADOR DE HIPERPARÂMETROS

Usa Optuna para encontrar automaticamente os melhores parâmetros.
Otimiza estratégias, modelos LSTM e agentes RL.

Uso:
    from engine.ml.optimizer import HyperOptimizer, get_optimizer

    optimizer = get_optimizer()

    # Otimiza parâmetros de estratégia
    best_params = optimizer.optimize_strategy(
        explosions_data=data,
        n_trials=100,
    )

    # Otimiza modelo LSTM
    best_params = optimizer.optimize_lstm(
        X_train, y_train,
        n_trials=50,
    )
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# Optuna
try:
    import optuna
    from optuna.pruners import MedianPruner
    from optuna.samplers import TPESampler

    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    optuna = None

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class OptimizationTarget(Enum):
    """Alvos de otimização."""

    STRATEGY = "strategy"  # Parâmetros de estratégia
    LSTM = "lstm"  # Modelo LSTM
    RL_AGENT = "rl_agent"  # Agente RL
    MARTINGALE = "martingale"  # Parâmetros de martingale


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class OptimizationResult:
    """Resultado de uma otimização."""

    target: OptimizationTarget
    best_params: Dict[str, Any]
    best_value: float
    n_trials: int
    optimization_time: float
    all_trials: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target.value,
            "best_params": self.best_params,
            "best_value": self.best_value,
            "n_trials": self.n_trials,
            "optimization_time": self.optimization_time,
        }


@dataclass
class StrategyParams:
    """Parâmetros otimizáveis da estratégia."""

    threshold: float = 2.0
    lows_needed: int = 8
    target_multiplier: float = 1.85
    base_bet_divisor: int = 15
    max_dobra: int = 4


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULADOR DE ESTRATÉGIA
# ═══════════════════════════════════════════════════════════════════════════════


class StrategySimulator:
    """
    Simula uma estratégia com dados históricos.

    Usado pelo Optuna para avaliar diferentes parâmetros.
    """

    def __init__(
        self,
        explosions: List[float],
        initial_balance: float = 1000.0,
    ):
        """
        Inicializa o simulador.

        Args:
            explosions: Lista de explosões históricas
            initial_balance: Saldo inicial
        """
        self._explosions = explosions
        self._initial_balance = initial_balance

    def simulate(
        self,
        threshold: float,
        lows_needed: int,
        target: float,
        base_bet_divisor: int,
        max_dobra: int,
    ) -> Dict[str, float]:
        """
        Simula a estratégia com os parâmetros dados.

        Returns:
            Dicionário com métricas de performance
        """
        balance = self._initial_balance
        base_bet = self._initial_balance / base_bet_divisor

        # Multipliers do martingale
        multipliers = {i: 2 ** (i - 1) for i in range(1, max_dobra + 1)}

        # Estado
        low_count = 0
        current_dobra = 1

        # Métricas
        total_bets = 0
        wins = 0
        losses = 0
        max_drawdown = 0
        peak_balance = balance

        for explosion in self._explosions:
            # Atualiza contagem de lows
            if explosion < threshold:
                low_count += 1
            else:
                low_count = 0

            # Verifica se deve apostar
            if low_count >= lows_needed:
                # Calcula valor da aposta
                bet_amount = base_bet * multipliers.get(current_dobra, 1)

                # Verifica se tem saldo
                if bet_amount > balance:
                    bet_amount = balance

                if bet_amount < 1.0:
                    continue

                total_bets += 1

                # Simula resultado
                if explosion >= target:
                    # WIN
                    profit = bet_amount * (target - 1)
                    balance += profit
                    wins += 1
                    current_dobra = 1
                else:
                    # LOSS
                    balance -= bet_amount
                    losses += 1

                    if current_dobra < max_dobra:
                        current_dobra += 1
                    else:
                        current_dobra = 1

                # Reset contagem após aposta
                low_count = 0

                # Atualiza métricas
                if balance > peak_balance:
                    peak_balance = balance

                drawdown = (
                    (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
                )
                max_drawdown = max(max_drawdown, drawdown)

                # Faliu?
                if balance < 1.0:
                    break

        # Calcula métricas finais
        profit = balance - self._initial_balance
        roi = profit / self._initial_balance * 100
        win_rate = wins / total_bets * 100 if total_bets > 0 else 0

        return {
            "final_balance": balance,
            "profit": profit,
            "roi": roi,
            "total_bets": total_bets,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown * 100,
            "survived": balance >= 1.0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# HYPER OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════════


class HyperOptimizer:
    """
    Otimizador de hiperparâmetros usando Optuna.

    Encontra automaticamente os melhores parâmetros para:
    - Estratégia de apostas (threshold, lows_needed, target)
    - Modelo LSTM (hidden_size, layers, learning_rate)
    - Agente RL (learning_rate, gamma, etc)

    Exemplo:
        optimizer = HyperOptimizer()

        # Otimiza estratégia
        result = optimizer.optimize_strategy(
            explosions_data=historico,
            n_trials=100,
        )

        print(f"Melhores parâmetros: {result.best_params}")
        print(f"Melhor ROI: {result.best_value:.2f}%")
    """

    def __init__(
        self,
        storage: Optional[str] = None,
        study_name_prefix: str = "crashbot",
    ):
        """
        Inicializa o otimizador.

        Args:
            storage: URL do banco de dados Optuna (opcional)
            study_name_prefix: Prefixo para nomes de estudos
        """
        if not HAS_OPTUNA:
            raise ImportError("Optuna não encontrado. Instale com: pip install optuna")

        self._lock = threading.Lock()
        self._storage = storage
        self._study_name_prefix = study_name_prefix

        # Histórico de otimizações
        self._results: List[OptimizationResult] = []

        logger.info("HyperOptimizer inicializado")

    # ═══════════════════════════════════════════════════════════════════════════
    # OTIMIZAÇÃO DE ESTRATÉGIA
    # ═══════════════════════════════════════════════════════════════════════════

    def optimize_strategy(
        self,
        explosions_data: List[float],
        initial_balance: float = 1000.0,
        n_trials: int = 100,
        timeout: Optional[int] = None,
        n_jobs: int = 1,
        show_progress: bool = True,
    ) -> OptimizationResult:
        """
        Otimiza parâmetros da estratégia.

        Args:
            explosions_data: Dados históricos de explosões
            initial_balance: Saldo inicial para simulação
            n_trials: Número de tentativas
            timeout: Timeout em segundos
            n_jobs: Número de jobs paralelos
            show_progress: Se True, mostra barra de progresso

        Returns:
            OptimizationResult com melhores parâmetros
        """
        simulator = StrategySimulator(explosions_data, initial_balance)

        def objective(trial: optuna.Trial) -> float:
            # Sugere parâmetros
            threshold = trial.suggest_float("threshold", 1.5, 3.0, step=0.1)
            lows_needed = trial.suggest_int("lows_needed", 4, 12)
            target = trial.suggest_float("target", 1.3, 2.5, step=0.05)
            base_bet_divisor = trial.suggest_int("base_bet_divisor", 10, 25)
            max_dobra = trial.suggest_int("max_dobra", 2, 6)

            # Simula
            metrics = simulator.simulate(
                threshold=threshold,
                lows_needed=lows_needed,
                target=target,
                base_bet_divisor=base_bet_divisor,
                max_dobra=max_dobra,
            )

            # Penaliza se não sobreviveu
            if not metrics["survived"]:
                return -1000.0

            # Objetivo: maximizar ROI ajustado por drawdown
            roi = metrics["roi"]
            drawdown_penalty = metrics["max_drawdown"] * 0.5

            return roi - drawdown_penalty

        # Cria estudo
        study_name = f"{self._study_name_prefix}_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        sampler = TPESampler(seed=42)
        pruner = MedianPruner(n_startup_trials=10)

        study = optuna.create_study(
            study_name=study_name,
            storage=self._storage,
            direction="maximize",
            sampler=sampler,
            pruner=pruner,
        )

        # Otimiza
        start_time = datetime.now()

        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            n_jobs=n_jobs,
            show_progress_bar=show_progress,
        )

        optimization_time = (datetime.now() - start_time).total_seconds()

        # Resultado
        result = OptimizationResult(
            target=OptimizationTarget.STRATEGY,
            best_params=study.best_params,
            best_value=study.best_value,
            n_trials=len(study.trials),
            optimization_time=optimization_time,
            all_trials=[
                {"params": t.params, "value": t.value}
                for t in study.trials
                if t.value is not None
            ],
        )

        self._results.append(result)

        logger.info(f"Otimização concluída: ROI={result.best_value:.2f}%")
        logger.info(f"Melhores parâmetros: {result.best_params}")

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # OTIMIZAÇÃO DE LSTM
    # ═══════════════════════════════════════════════════════════════════════════

    def optimize_lstm(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        n_trials: int = 50,
        timeout: Optional[int] = None,
        show_progress: bool = True,
    ) -> OptimizationResult:
        """
        Otimiza hiperparâmetros do modelo LSTM.

        Args:
            X_train: Dados de treino
            y_train: Labels de treino
            X_val: Dados de validação (opcional)
            y_val: Labels de validação (opcional)
            n_trials: Número de tentativas
            timeout: Timeout em segundos
            show_progress: Se True, mostra barra de progresso

        Returns:
            OptimizationResult com melhores parâmetros
        """
        # Import local para evitar dependência circular
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
            from torch.utils.data import DataLoader, TensorDataset
        except ImportError:
            raise ImportError("PyTorch necessário para otimização de LSTM")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Split validação se não fornecido
        if X_val is None:
            val_size = int(len(X_train) * 0.2)
            indices = np.random.permutation(len(X_train))
            train_idx, val_idx = indices[val_size:], indices[:val_size]
            X_val, y_val = X_train[val_idx], y_train[val_idx]
            X_train, y_train = X_train[train_idx], y_train[train_idx]

        def objective(trial: optuna.Trial) -> float:
            # Sugere hiperparâmetros
            hidden_size = trial.suggest_int("hidden_size", 16, 128, step=16)
            num_layers = trial.suggest_int("num_layers", 1, 3)
            dropout = trial.suggest_float("dropout", 0.0, 0.5, step=0.1)
            learning_rate = trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True)
            batch_size = trial.suggest_categorical("batch_size", [16, 32, 64, 128])

            # Cria modelo simples
            input_size = X_train.shape[2] if X_train.ndim == 3 else 1
            output_size = (
                len(np.unique(y_train)) if y_train.dtype in [np.int32, np.int64] else 1
            )
            is_classification = output_size > 1

            class SimpleLSTM(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.lstm = nn.LSTM(
                        input_size=input_size,
                        hidden_size=hidden_size,
                        num_layers=num_layers,
                        batch_first=True,
                        dropout=dropout if num_layers > 1 else 0,
                    )
                    self.fc = nn.Linear(hidden_size, output_size)

                def forward(self, x):
                    lstm_out, _ = self.lstm(x)
                    out = self.fc(lstm_out[:, -1, :])
                    return out

            model = SimpleLSTM().to(device)

            # Loss e optimizer
            if is_classification:
                criterion = nn.CrossEntropyLoss()
            else:
                criterion = nn.MSELoss()

            optimizer_torch = optim.Adam(model.parameters(), lr=learning_rate)

            # DataLoaders
            X_train_tensor = torch.FloatTensor(X_train).to(device)
            X_val_tensor = torch.FloatTensor(X_val).to(device)

            if is_classification:
                y_train_tensor = torch.LongTensor(y_train).to(device)
                y_val_tensor = torch.LongTensor(y_val).to(device)
            else:
                y_train_tensor = torch.FloatTensor(y_train).to(device)
                y_val_tensor = torch.FloatTensor(y_val).to(device)

            train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
            train_loader = DataLoader(
                train_dataset, batch_size=batch_size, shuffle=True
            )

            # Treina por poucas épocas
            n_epochs = 20

            for epoch in range(n_epochs):
                model.train()
                for batch_X, batch_y in train_loader:
                    optimizer_torch.zero_grad()
                    outputs = model(batch_X)
                    if not is_classification:
                        outputs = outputs.squeeze()
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer_torch.step()

                # Avalia
                model.eval()
                with torch.no_grad():
                    val_outputs = model(X_val_tensor)
                    if not is_classification:
                        val_outputs = val_outputs.squeeze()
                    val_loss = criterion(val_outputs, y_val_tensor).item()

                # Pruning
                trial.report(val_loss, epoch)
                if trial.should_prune():
                    raise optuna.TrialPruned()

            return val_loss

        # Cria estudo
        study_name = (
            f"{self._study_name_prefix}_lstm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        study = optuna.create_study(
            study_name=study_name,
            storage=self._storage,
            direction="minimize",
            sampler=TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=5),
        )

        # Otimiza
        start_time = datetime.now()

        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=show_progress,
        )

        optimization_time = (datetime.now() - start_time).total_seconds()

        # Resultado
        result = OptimizationResult(
            target=OptimizationTarget.LSTM,
            best_params=study.best_params,
            best_value=study.best_value,
            n_trials=len(study.trials),
            optimization_time=optimization_time,
            all_trials=[
                {"params": t.params, "value": t.value}
                for t in study.trials
                if t.value is not None
            ],
        )

        self._results.append(result)

        logger.info(f"Otimização LSTM concluída: val_loss={result.best_value:.4f}")
        logger.info(f"Melhores parâmetros: {result.best_params}")

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # OTIMIZAÇÃO DE RL
    # ═══════════════════════════════════════════════════════════════════════════

    def optimize_rl(
        self,
        explosions_data: Optional[List[float]] = None,
        n_trials: int = 20,
        timesteps_per_trial: int = 10000,
        timeout: Optional[int] = None,
        show_progress: bool = True,
    ) -> OptimizationResult:
        """
        Otimiza hiperparâmetros do agente RL.

        Args:
            explosions_data: Dados reais para o ambiente
            n_trials: Número de tentativas
            timesteps_per_trial: Timesteps por trial
            timeout: Timeout em segundos
            show_progress: Se True, mostra barra de progresso

        Returns:
            OptimizationResult com melhores parâmetros
        """
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.evaluation import evaluate_policy
        except ImportError:
            raise ImportError("Stable-Baselines3 necessário para otimização de RL")

        from engine.ml.rl_environment import make_crash_env

        def objective(trial: optuna.Trial) -> float:
            # Sugere hiperparâmetros
            learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
            gamma = trial.suggest_float("gamma", 0.9, 0.999)
            gae_lambda = trial.suggest_float("gae_lambda", 0.8, 0.99)
            clip_range = trial.suggest_float("clip_range", 0.1, 0.4)
            ent_coef = trial.suggest_float("ent_coef", 0.0, 0.1)
            n_steps = trial.suggest_categorical("n_steps", [256, 512, 1024, 2048])
            batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])

            # Cria ambiente
            env_config = {
                "initial_balance": 1000.0,
                "base_bet": 10.0,
                "history_size": 20,
                "max_rounds": 200,
            }

            if explosions_data:
                env_config["real_data"] = explosions_data
                env_config["use_real_data"] = True

            env = make_crash_env(**env_config)
            eval_env = make_crash_env(**env_config)

            try:
                # Cria modelo
                model = PPO(
                    "MlpPolicy",
                    env,
                    learning_rate=learning_rate,
                    gamma=gamma,
                    gae_lambda=gae_lambda,
                    clip_range=clip_range,
                    ent_coef=ent_coef,
                    n_steps=n_steps,
                    batch_size=batch_size,
                    verbose=0,
                )

                # Treina
                model.learn(total_timesteps=timesteps_per_trial)

                # Avalia
                mean_reward, _ = evaluate_policy(
                    model,
                    eval_env,
                    n_eval_episodes=20,
                    deterministic=True,
                )

                return mean_reward

            finally:
                env.close()
                eval_env.close()

        # Cria estudo
        study_name = (
            f"{self._study_name_prefix}_rl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        study = optuna.create_study(
            study_name=study_name,
            storage=self._storage,
            direction="maximize",
            sampler=TPESampler(seed=42),
        )

        # Otimiza
        start_time = datetime.now()

        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=show_progress,
        )

        optimization_time = (datetime.now() - start_time).total_seconds()

        # Resultado
        result = OptimizationResult(
            target=OptimizationTarget.RL_AGENT,
            best_params=study.best_params,
            best_value=study.best_value,
            n_trials=len(study.trials),
            optimization_time=optimization_time,
            all_trials=[
                {"params": t.params, "value": t.value}
                for t in study.trials
                if t.value is not None
            ],
        )

        self._results.append(result)

        logger.info(f"Otimização RL concluída: reward={result.best_value:.2f}")
        logger.info(f"Melhores parâmetros: {result.best_params}")

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_results(self) -> List[OptimizationResult]:
        """Retorna histórico de otimizações."""
        return self._results

    def save_results(self, filepath: str) -> bool:
        """Salva resultados em JSON."""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            data = {
                "results": [r.to_dict() for r in self._results],
                "saved_at": datetime.now().isoformat(),
            }

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Resultados salvos em: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {e}")
            return False

    def apply_best_params(
        self,
        result: OptimizationResult,
    ) -> Dict[str, Any]:
        """
        Retorna configuração para aplicar os melhores parâmetros.

        Args:
            result: Resultado da otimização

        Returns:
            Dicionário de configuração
        """
        params = result.best_params.copy()

        if result.target == OptimizationTarget.STRATEGY:
            return {
                "trigger": {
                    "threshold": params.get("threshold", 2.0),
                    "lows_needed": params.get("lows_needed", 8),
                },
                "betting": {
                    "target": params.get("target", 1.85),
                    "base_bet_divisor": params.get("base_bet_divisor", 15),
                    "max_dobra": params.get("max_dobra", 4),
                },
            }

        elif result.target == OptimizationTarget.LSTM:
            return {
                "model": {
                    "hidden_size": params.get("hidden_size", 64),
                    "num_layers": params.get("num_layers", 2),
                    "dropout": params.get("dropout", 0.2),
                },
                "training": {
                    "learning_rate": params.get("learning_rate", 0.001),
                    "batch_size": params.get("batch_size", 32),
                },
            }

        elif result.target == OptimizationTarget.RL_AGENT:
            return {
                "model": {
                    "learning_rate": params.get("learning_rate", 3e-4),
                    "gamma": params.get("gamma", 0.99),
                    "gae_lambda": params.get("gae_lambda", 0.95),
                    "clip_range": params.get("clip_range", 0.2),
                    "ent_coef": params.get("ent_coef", 0.01),
                    "n_steps": params.get("n_steps", 2048),
                    "batch_size": params.get("batch_size", 64),
                },
            }

        return params


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_optimizer: Optional[HyperOptimizer] = None
_optimizer_lock = threading.Lock()


def get_optimizer(**kwargs) -> HyperOptimizer:
    """
    Retorna a instância singleton do HyperOptimizer.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _optimizer

    if _optimizer is None:
        with _optimizer_lock:
            if _optimizer is None:
                _optimizer = HyperOptimizer(**kwargs)

    return _optimizer


def reset_optimizer() -> None:
    """Reseta o otimizador (útil para testes)."""
    global _optimizer
    with _optimizer_lock:
        _optimizer = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO HYPER OPTIMIZER - CrashBot v3.0")
    print("=" * 60)

    if not HAS_OPTUNA:
        print("❌ Optuna não instalado!")
        exit(1)

    print(f"\n✅ Optuna disponível")

    # Gera dados sintéticos
    print(f"\n--- Gerando Dados Sintéticos ---")
    import random

    explosions = []
    for _ in range(5000):
        if random.random() < 0.6:
            explosions.append(round(random.uniform(1.0, 1.99), 2))
        else:
            explosions.append(round(random.uniform(2.0, 10.0), 2))

    print(f"   {len(explosions)} explosões geradas")

    # Cria otimizador
    optimizer = HyperOptimizer()
    print(f"\n✅ HyperOptimizer criado")

    # Otimiza estratégia
    print(f"\n--- Otimização de Estratégia ---")

    result = optimizer.optimize_strategy(
        explosions_data=explosions,
        initial_balance=1000.0,
        n_trials=20,  # Reduzido para teste
        show_progress=True,
    )

    print(f"\n   Resultado:")
    print(f"      Melhor ROI: {result.best_value:.2f}%")
    print(f"      Trials: {result.n_trials}")
    print(f"      Tempo: {result.optimization_time:.1f}s")
    print(f"\n   Melhores parâmetros:")
    for key, value in result.best_params.items():
        print(f"      {key}: {value}")

    # Aplica parâmetros
    print(f"\n--- Aplicando Parâmetros ---")
    config = optimizer.apply_best_params(result)
    print(f"   Configuração gerada:")
    print(json.dumps(config, indent=4))

    # Salva
    print(f"\n--- Salvando Resultados ---")
    if optimizer.save_results("data/optimization_results.json"):
        print(f"   ✅ Resultados salvos")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
