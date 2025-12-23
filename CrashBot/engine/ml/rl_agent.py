#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - AGENTE DE REINFORCEMENT LEARNING

Agente que aprende a jogar usando Stable-Baselines3.
Suporta múltiplos algoritmos: PPO, A2C, DQN.

Uso:
    from engine.ml.rl_agent import RLAgent, get_agent

    agent = get_agent()

    # Treina
    agent.train(total_timesteps=100000)

    # Usa em tempo real
    action = agent.predict(current_state)

    # Salva/Carrega
    agent.save("models/rl_agent_v1")
    agent.load("models/rl_agent_v1")
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

# Stable-Baselines3
try:
    from stable_baselines3 import A2C, DQN, PPO
    from stable_baselines3.common.callbacks import (
        BaseCallback,
        CallbackList,
        CheckpointCallback,
        EvalCallback,
    )
    from stable_baselines3.common.evaluation import evaluate_policy
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False
    PPO = A2C = DQN = None

# Gymnasium
try:
    import gymnasium as gym

    HAS_GYM = True
except ImportError:
    HAS_GYM = False

# Core imports
from core.events import BotEvent, emit

# Local imports
from engine.ml.rl_environment import CrashGameEnv, make_crash_env

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════


class RLAlgorithm(Enum):
    """Algoritmos de RL disponíveis."""

    PPO = "ppo"  # Proximal Policy Optimization
    A2C = "a2c"  # Advantage Actor-Critic
    DQN = "dqn"  # Deep Q-Network


# Mapeamento de algoritmos
ALGORITHM_MAP = (
    {
        RLAlgorithm.PPO: PPO,
        RLAlgorithm.A2C: A2C,
        RLAlgorithm.DQN: DQN,
    }
    if HAS_SB3
    else {}
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TrainingConfig:
    """Configuração de treinamento."""

    algorithm: RLAlgorithm = RLAlgorithm.PPO
    total_timesteps: int = 100000
    learning_rate: float = 3e-4
    batch_size: int = 64
    n_steps: int = 2048  # Para PPO/A2C
    gamma: float = 0.99  # Discount factor
    gae_lambda: float = 0.95  # GAE lambda
    clip_range: float = 0.2  # Para PPO
    ent_coef: float = 0.01  # Entropy coefficient
    n_epochs: int = 10  # Para PPO
    num_envs: int = 4  # Ambientes paralelos
    eval_freq: int = 10000  # Frequência de avaliação
    save_freq: int = 25000  # Frequência de checkpoint
    verbose: int = 1


@dataclass
class PredictionResult:
    """Resultado de uma predição do agente."""

    action: int
    action_name: str
    confidence: float
    q_values: Optional[np.ndarray] = None

    @property
    def should_bet(self) -> bool:
        """Retorna True se a ação é apostar."""
        return self.action > 0


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACKS CUSTOMIZADOS
# ═══════════════════════════════════════════════════════════════════════════════

if HAS_SB3:

    class TrainingProgressCallback(BaseCallback):
        """
        Callback para monitorar progresso do treinamento.
        """

        def __init__(
            self,
            check_freq: int = 1000,
            verbose: int = 1,
            on_progress: Optional[Callable[[Dict], None]] = None,
        ):
            super().__init__(verbose)
            self.check_freq = check_freq
            self.on_progress = on_progress
            self.episode_rewards: List[float] = []
            self.episode_lengths: List[int] = []
            self.best_mean_reward = -np.inf

        def _on_step(self) -> bool:
            # Coleta métricas dos episódios
            if len(self.model.ep_info_buffer) > 0:
                for info in self.model.ep_info_buffer:
                    if "r" in info:
                        self.episode_rewards.append(info["r"])
                    if "l" in info:
                        self.episode_lengths.append(info["l"])

            # Log periódico
            if self.n_calls % self.check_freq == 0:
                if len(self.episode_rewards) > 0:
                    mean_reward = np.mean(self.episode_rewards[-100:])
                    mean_length = np.mean(self.episode_lengths[-100:])

                    if mean_reward > self.best_mean_reward:
                        self.best_mean_reward = mean_reward

                    metrics = {
                        "timesteps": self.num_timesteps,
                        "episodes": len(self.episode_rewards),
                        "mean_reward": mean_reward,
                        "best_reward": self.best_mean_reward,
                        "mean_length": mean_length,
                    }

                    if self.verbose > 0:
                        logger.info(
                            f"Step {self.num_timesteps}: "
                            f"reward={mean_reward:.2f}, "
                            f"best={self.best_mean_reward:.2f}"
                        )

                    if self.on_progress:
                        self.on_progress(metrics)

            return True


# ═══════════════════════════════════════════════════════════════════════════════
# RL AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class RLAgent:
    """
    Agente de Reinforcement Learning.

    Encapsula Stable-Baselines3 para facilitar uso no CrashBot.

    Features:
        - Suporta PPO, A2C, DQN
        - Treinamento com callbacks
        - Avaliação periódica
        - Checkpoints automáticos
        - Integração com dados reais

    Exemplo:
        agent = RLAgent(algorithm=RLAlgorithm.PPO)

        # Treina
        agent.train(total_timesteps=100000)

        # Prediz
        state = get_current_state()
        result = agent.predict(state)

        if result.should_bet:
            print(f"Apostar com alvo: {result.action_name}")
    """

    def __init__(
        self,
        algorithm: RLAlgorithm = RLAlgorithm.PPO,
        env_config: Optional[Dict[str, Any]] = None,
        model_config: Optional[Dict[str, Any]] = None,
        device: str = "auto",
    ):
        """
        Inicializa o agente.

        Args:
            algorithm: Algoritmo de RL a usar
            env_config: Configuração do ambiente
            model_config: Configuração do modelo
            device: Device ("auto", "cpu", "cuda")
        """
        if not HAS_SB3:
            raise ImportError(
                "Stable-Baselines3 não encontrado. Instale com: pip install stable-baselines3"
            )

        if not HAS_GYM:
            raise ImportError(
                "Gymnasium não encontrado. Instale com: pip install gymnasium"
            )

        self._lock = threading.Lock()

        # Configurações
        self._algorithm = algorithm
        self._env_config = env_config or {}
        self._model_config = model_config or {}
        self._device = device

        # Ambiente e modelo
        self._env: Optional[gym.Env] = None
        self._eval_env: Optional[gym.Env] = None
        self._model = None

        # Estado
        self._is_trained = False
        self._training_history: List[Dict] = []

        # Action names
        self._action_names = ["SKIP", "BET_1.5x", "BET_2.0x", "BET_3.0x"]

        logger.info(
            f"RLAgent inicializado: algorithm={algorithm.value}, device={device}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # SETUP
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_env(self, num_envs: int = 1, for_eval: bool = False) -> gym.Env:
        """Cria ambiente(s) para treinamento ou avaliação."""
        env_config = self._env_config.copy()

        if for_eval:
            env_config["max_rounds"] = 500  # Episódios mais curtos para avaliação

        if num_envs == 1:
            env = make_crash_env(**env_config)
            env = Monitor(env)
        else:

            def make_env():
                e = make_crash_env(**env_config)
                e = Monitor(e)
                return e

            env = DummyVecEnv([make_env for _ in range(num_envs)])

        return env

    def _create_model(self, env: gym.Env, config: TrainingConfig) -> Any:
        """Cria o modelo de RL."""
        AlgorithmClass = ALGORITHM_MAP[self._algorithm]

        # Configuração base
        model_kwargs = {
            "policy": "MlpPolicy",
            "env": env,
            "learning_rate": config.learning_rate,
            "gamma": config.gamma,
            "verbose": config.verbose,
            "device": self._device,
        }

        # Configurações específicas por algoritmo
        if self._algorithm == RLAlgorithm.PPO:
            model_kwargs.update(
                {
                    "n_steps": config.n_steps,
                    "batch_size": config.batch_size,
                    "n_epochs": config.n_epochs,
                    "gae_lambda": config.gae_lambda,
                    "clip_range": config.clip_range,
                    "ent_coef": config.ent_coef,
                }
            )

        elif self._algorithm == RLAlgorithm.A2C:
            model_kwargs.update(
                {
                    "n_steps": config.n_steps,
                    "gae_lambda": config.gae_lambda,
                    "ent_coef": config.ent_coef,
                }
            )

        elif self._algorithm == RLAlgorithm.DQN:
            model_kwargs.update(
                {
                    "batch_size": config.batch_size,
                    "buffer_size": 100000,
                    "learning_starts": 1000,
                    "target_update_interval": 500,
                    "exploration_fraction": 0.1,
                    "exploration_final_eps": 0.02,
                }
            )

        # Override com config customizada
        model_kwargs.update(self._model_config)

        return AlgorithmClass(**model_kwargs)

    # ═══════════════════════════════════════════════════════════════════════════
    # TREINAMENTO
    # ═══════════════════════════════════════════════════════════════════════════

    def train(
        self,
        config: Optional[TrainingConfig] = None,
        real_data: Optional[List[float]] = None,
        save_path: Optional[str] = None,
        on_progress: Optional[Callable[[Dict], None]] = None,
    ) -> Dict[str, Any]:
        """
        Treina o agente.

        Args:
            config: Configuração de treinamento
            real_data: Dados reais para o ambiente
            save_path: Caminho para salvar checkpoints
            on_progress: Callback de progresso

        Returns:
            Dicionário com métricas de treinamento
        """
        config = config or TrainingConfig()

        with self._lock:
            # Configura dados reais se fornecidos
            if real_data:
                self._env_config["real_data"] = real_data
                self._env_config["use_real_data"] = True

            # Cria ambientes
            logger.info(f"Criando {config.num_envs} ambientes de treinamento...")
            self._env = self._create_env(num_envs=config.num_envs)
            self._eval_env = self._create_env(num_envs=1, for_eval=True)

            # Cria modelo
            logger.info(f"Criando modelo {self._algorithm.value}...")
            self._model = self._create_model(self._env, config)

            # Callbacks
            callbacks = []

            # Callback de progresso
            progress_callback = TrainingProgressCallback(
                check_freq=1000,
                verbose=config.verbose,
                on_progress=on_progress,
            )
            callbacks.append(progress_callback)

            # Callback de avaliação
            if self._eval_env:
                eval_callback = EvalCallback(
                    self._eval_env,
                    best_model_save_path=save_path,
                    log_path=save_path,
                    eval_freq=config.eval_freq,
                    n_eval_episodes=10,
                    deterministic=True,
                    verbose=config.verbose,
                )
                callbacks.append(eval_callback)

            # Callback de checkpoint
            if save_path:
                Path(save_path).mkdir(parents=True, exist_ok=True)
                checkpoint_callback = CheckpointCallback(
                    save_freq=config.save_freq,
                    save_path=save_path,
                    name_prefix="rl_agent",
                    verbose=config.verbose,
                )
                callbacks.append(checkpoint_callback)

            # Treina
            logger.info(f"Iniciando treinamento: {config.total_timesteps} timesteps...")

            start_time = datetime.now()

            self._model.learn(
                total_timesteps=config.total_timesteps,
                callback=CallbackList(callbacks),
                progress_bar=True,
            )

            training_time = (datetime.now() - start_time).total_seconds()

            self._is_trained = True

            # Métricas finais
            metrics = {
                "algorithm": self._algorithm.value,
                "total_timesteps": config.total_timesteps,
                "training_time_seconds": training_time,
                "episodes": len(progress_callback.episode_rewards),
                "mean_reward": (
                    np.mean(progress_callback.episode_rewards[-100:])
                    if progress_callback.episode_rewards
                    else 0
                ),
                "best_reward": progress_callback.best_mean_reward,
            }

            logger.info(f"Treinamento concluído em {training_time:.1f}s")
            logger.info(f"Melhor reward: {metrics['best_reward']:.2f}")

            return metrics

    def continue_training(
        self,
        additional_timesteps: int = 50000,
        on_progress: Optional[Callable[[Dict], None]] = None,
    ) -> Dict[str, Any]:
        """
        Continua treinamento de um modelo existente.

        Args:
            additional_timesteps: Timesteps adicionais
            on_progress: Callback de progresso

        Returns:
            Métricas do treinamento adicional
        """
        if self._model is None:
            raise ValueError("Nenhum modelo carregado para continuar treinamento")

        with self._lock:
            progress_callback = TrainingProgressCallback(
                check_freq=1000,
                on_progress=on_progress,
            )

            logger.info(
                f"Continuando treinamento: +{additional_timesteps} timesteps..."
            )

            self._model.learn(
                total_timesteps=additional_timesteps,
                callback=progress_callback,
                reset_num_timesteps=False,
                progress_bar=True,
            )

            return {
                "additional_timesteps": additional_timesteps,
                "mean_reward": (
                    np.mean(progress_callback.episode_rewards[-100:])
                    if progress_callback.episode_rewards
                    else 0
                ),
            }

    # ═══════════════════════════════════════════════════════════════════════════
    # PREDIÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def predict(
        self,
        state: np.ndarray,
        deterministic: bool = True,
    ) -> PredictionResult:
        """
        Faz predição para um estado.

        Args:
            state: Estado atual (observação do ambiente)
            deterministic: Se True, escolhe ação determinística

        Returns:
            PredictionResult com ação e informações
        """
        if self._model is None:
            raise ValueError("Modelo não treinado ou carregado")

        with self._lock:
            # Garante shape correto
            if state.ndim == 1:
                state = state.reshape(1, -1)

            # Predição
            action, _states = self._model.predict(state, deterministic=deterministic)
            action = int(action[0]) if isinstance(action, np.ndarray) else int(action)

            # Calcula confiança (aproximada)
            # Para PPO/A2C, podemos usar a distribuição de ações
            confidence = 0.5  # Default
            q_values = None

            if self._algorithm == RLAlgorithm.DQN:
                # DQN tem Q-values
                q_values = self._model.q_net(self._model.policy.obs_to_tensor(state)[0])
                q_values = q_values.detach().cpu().numpy()[0]

                # Softmax para probabilidades
                exp_q = np.exp(q_values - np.max(q_values))
                probs = exp_q / exp_q.sum()
                confidence = float(probs[action])

            return PredictionResult(
                action=action,
                action_name=self._action_names[action],
                confidence=confidence,
                q_values=q_values,
            )

    def predict_batch(
        self,
        states: np.ndarray,
        deterministic: bool = True,
    ) -> List[PredictionResult]:
        """
        Faz predições para múltiplos estados.

        Args:
            states: Array de estados (batch_size, state_dim)
            deterministic: Se True, ações determinísticas

        Returns:
            Lista de PredictionResults
        """
        results = []
        for i in range(len(states)):
            result = self.predict(states[i], deterministic)
            results.append(result)
        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # AVALIAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def evaluate(
        self,
        n_episodes: int = 100,
        real_data: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Avalia o agente.

        Args:
            n_episodes: Número de episódios para avaliação
            real_data: Dados reais para o ambiente

        Returns:
            Métricas de avaliação
        """
        if self._model is None:
            raise ValueError("Modelo não treinado ou carregado")

        with self._lock:
            # Cria ambiente de avaliação
            env_config = self._env_config.copy()
            if real_data:
                env_config["real_data"] = real_data
                env_config["use_real_data"] = True

            eval_env = make_crash_env(**env_config)

            # Avalia
            mean_reward, std_reward = evaluate_policy(
                self._model,
                eval_env,
                n_eval_episodes=n_episodes,
                deterministic=True,
            )

            # Métricas detalhadas
            episode_rewards = []
            episode_profits = []
            episode_win_rates = []

            for _ in range(n_episodes):
                state, info = eval_env.reset()
                total_reward = 0

                while True:
                    action, _ = self._model.predict(state, deterministic=True)
                    state, reward, terminated, truncated, info = eval_env.step(action)
                    total_reward += reward

                    if terminated or truncated:
                        episode_rewards.append(total_reward)
                        episode_profits.append(info.get("total_profit", 0))
                        episode_win_rates.append(info.get("win_rate", 0))
                        break

            eval_env.close()

            return {
                "n_episodes": n_episodes,
                "mean_reward": mean_reward,
                "std_reward": std_reward,
                "mean_profit": np.mean(episode_profits),
                "std_profit": np.std(episode_profits),
                "mean_win_rate": np.mean(episode_win_rates),
                "profitable_episodes": sum(1 for p in episode_profits if p > 0)
                / n_episodes,
            }

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTÊNCIA
    # ═══════════════════════════════════════════════════════════════════════════

    def save(self, filepath: str) -> bool:
        """
        Salva o modelo.

        Args:
            filepath: Caminho do arquivo (sem extensão)

        Returns:
            True se salvou com sucesso
        """
        if self._model is None:
            logger.warning("Nenhum modelo para salvar")
            return False

        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            self._model.save(filepath)

            # Salva metadados
            import json

            metadata = {
                "algorithm": self._algorithm.value,
                "env_config": self._env_config,
                "is_trained": self._is_trained,
                "saved_at": datetime.now().isoformat(),
            }
            with open(f"{filepath}_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Modelo salvo em: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
            return False

    def load(self, filepath: str) -> bool:
        """
        Carrega um modelo salvo.

        Args:
            filepath: Caminho do arquivo (sem extensão)

        Returns:
            True se carregou com sucesso
        """
        try:
            AlgorithmClass = ALGORITHM_MAP[self._algorithm]

            # Cria ambiente dummy para carregar
            self._env = self._create_env(num_envs=1)

            self._model = AlgorithmClass.load(
                filepath, env=self._env, device=self._device
            )
            self._is_trained = True

            logger.info(f"Modelo carregado de: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erro ao carregar: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def is_trained(self) -> bool:
        """Verifica se o agente está treinado."""
        return self._is_trained

    def get_info(self) -> Dict[str, Any]:
        """Retorna informações do agente."""
        return {
            "algorithm": self._algorithm.value,
            "is_trained": self._is_trained,
            "device": self._device,
            "env_config": self._env_config,
            "action_names": self._action_names,
        }

    def close(self) -> None:
        """Libera recursos."""
        if self._env:
            self._env.close()
        if self._eval_env:
            self._eval_env.close()


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_rl_agent: Optional[RLAgent] = None
_agent_lock = threading.Lock()


def get_agent(**kwargs) -> RLAgent:
    """
    Retorna a instância singleton do RLAgent.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _rl_agent

    if _rl_agent is None:
        with _agent_lock:
            if _rl_agent is None:
                _rl_agent = RLAgent(**kwargs)

    return _rl_agent


def reset_agent() -> None:
    """Reseta o agente (útil para testes)."""
    global _rl_agent
    with _agent_lock:
        if _rl_agent:
            _rl_agent.close()
        _rl_agent = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO RL AGENT - CrashBot v3.0")
    print("=" * 60)

    if not HAS_SB3:
        print("❌ Stable-Baselines3 não instalado!")
        exit(1)

    if not HAS_GYM:
        print("❌ Gymnasium não instalado!")
        exit(1)

    print(f"\n✅ Dependências disponíveis")

    # Configuração de ambiente
    env_config = {
        "initial_balance": 1000.0,
        "base_bet": 10.0,
        "history_size": 20,
        "max_rounds": 500,
    }

    # Cria agente
    agent = RLAgent(
        algorithm=RLAlgorithm.PPO,
        env_config=env_config,
        device="auto",
    )

    print(f"\n✅ RLAgent criado")
    info = agent.get_info()
    for key, value in info.items():
        print(f"   {key}: {value}")

    # Treina (poucas iterações para teste)
    print(f"\n--- Treinamento (teste rápido) ---")

    config = TrainingConfig(
        total_timesteps=5000,  # Reduzido para teste
        num_envs=2,
        verbose=1,
    )

    def on_progress(metrics):
        print(f"   Progress: {metrics}")

    try:
        metrics = agent.train(
            config=config,
            save_path="models/test_rl",
            on_progress=on_progress,
        )

        print(f"\n--- Métricas de Treinamento ---")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.4f}")
            else:
                print(f"   {key}: {value}")

        # Teste de predição
        print(f"\n--- Teste de Predição ---")

        # Cria estado de teste
        test_state = np.random.rand(25).astype(np.float32)  # 20 + 5 features

        result = agent.predict(test_state)
        print(f"   Ação: {result.action} ({result.action_name})")
        print(f"   Confiança: {result.confidence:.2%}")
        print(f"   Deve apostar: {result.should_bet}")

        # Avaliação
        print(f"\n--- Avaliação ---")
        eval_metrics = agent.evaluate(n_episodes=10)
        for key, value in eval_metrics.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.4f}")
            else:
                print(f"   {key}: {value}")

        # Salva modelo
        print(f"\n--- Persistência ---")
        if agent.save("models/test_rl/final_model"):
            print(f"   ✅ Modelo salvo")

    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback

        traceback.print_exc()

    finally:
        agent.close()

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
