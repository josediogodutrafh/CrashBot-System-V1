#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - AMBIENTE DE REINFORCEMENT LEARNING

Ambiente Gymnasium para treinar agentes de RL.
Simula o jogo Crash para o agente aprender estratégias.

Uso:
    from engine.ml.rl_environment import CrashGameEnv

    env = CrashGameEnv(initial_balance=1000.0)

    # Loop de treinamento
    state, info = env.reset()

    while True:
        action = agent.select_action(state)
        next_state, reward, terminated, truncated, info = env.step(action)

        if terminated or truncated:
            break

        state = next_state
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# Gymnasium
try:
    import gymnasium as gym
    from gymnasium import spaces

    HAS_GYM = True
except ImportError:
    HAS_GYM = False
    gym = None
    spaces = None

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════


class GamePhase(Enum):
    """Fases do jogo."""

    BETTING = "betting"  # Janela de apostas aberta
    RUNNING = "running"  # Rodada em andamento
    CRASHED = "crashed"  # Explodiu


class ActionType(Enum):
    """Tipos de ação do agente."""

    SKIP = 0  # Não apostar
    BET_LOW = 1  # Apostar com alvo baixo (1.5x)
    BET_MEDIUM = 2  # Apostar com alvo médio (2.0x)
    BET_HIGH = 3  # Apostar com alvo alto (3.0x)


# Configurações padrão
DEFAULT_TARGETS = {
    ActionType.BET_LOW: 1.50,
    ActionType.BET_MEDIUM: 2.00,
    ActionType.BET_HIGH: 3.00,
}

# Distribuição realista de explosões (baseada em dados reais)
# ~60% abaixo de 2x, ~25% entre 2x-5x, ~15% acima de 5x
EXPLOSION_DISTRIBUTION = {
    "low_prob": 0.60,  # Probabilidade de explosão baixa (< 2x)
    "low_range": (1.00, 1.99),
    "medium_prob": 0.25,  # Probabilidade de explosão média (2x - 5x)
    "medium_range": (2.00, 4.99),
    "high_prob": 0.15,  # Probabilidade de explosão alta (> 5x)
    "high_range": (5.00, 50.00),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BetResult:
    """Resultado de uma aposta."""

    action: ActionType
    bet_amount: float
    target: float
    explosion_value: float
    won: bool
    profit: float
    balance_before: float
    balance_after: float


# ═══════════════════════════════════════════════════════════════════════════════
# CRASH GAME ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════

if HAS_GYM:

    class CrashGameEnv(gym.Env):
        """
        Ambiente Gymnasium para o jogo Crash.

        Observação (State):
            - Últimas N explosões normalizadas
            - Saldo atual normalizado
            - Dobra atual (martingale)
            - Streak de baixas consecutivas
            - Média móvel das explosões
            - Volatilidade (std)

        Ações:
            0: SKIP - Não apostar
            1: BET_LOW - Apostar alvo 1.5x
            2: BET_MEDIUM - Apostar alvo 2.0x
            3: BET_HIGH - Apostar alvo 3.0x

        Recompensa:
            - WIN: +lucro normalizado
            - LOSS: -perda normalizada
            - SKIP em sequência de baixas: pequena penalidade
            - SKIP em alta: pequena recompensa
            - Bônus por manter saldo positivo

        Exemplo:
            env = CrashGameEnv(initial_balance=1000.0)
            state, _ = env.reset()

            for _ in range(1000):
                action = env.action_space.sample()  # ou do agente
                state, reward, done, truncated, info = env.step(action)

                if done:
                    state, _ = env.reset()
        """

        metadata = {"render_modes": ["human", "ansi"]}

        def __init__(
            self,
            initial_balance: float = 1000.0,
            base_bet: float = 10.0,
            max_dobra: int = 4,
            history_size: int = 20,
            max_rounds: int = 1000,
            use_real_data: bool = False,
            real_data: Optional[List[float]] = None,
            render_mode: Optional[str] = None,
        ):
            """
            Inicializa o ambiente.

            Args:
                initial_balance: Saldo inicial
                base_bet: Aposta base
                max_dobra: Máximo de dobras (martingale)
                history_size: Tamanho do histórico no estado
                max_rounds: Máximo de rodadas por episódio
                use_real_data: Se True, usa dados reais
                real_data: Lista de explosões reais
                render_mode: Modo de renderização
            """
            super().__init__()

            # Configurações
            self._initial_balance = initial_balance
            self._base_bet = base_bet
            self._max_dobra = max_dobra
            self._history_size = history_size
            self._max_rounds = max_rounds
            self._render_mode = render_mode

            # Dados reais (opcional)
            self._use_real_data = use_real_data
            self._real_data = real_data or []
            self._real_data_index = 0

            # Multipliers do martingale
            self._martingale_multipliers = {1: 1, 2: 2, 3: 4, 4: 8}

            # Targets para cada ação
            self._targets = DEFAULT_TARGETS.copy()

            # ═══════════════════════════════════════════════════════════════════
            # ESPAÇOS DE AÇÃO E OBSERVAÇÃO
            # ═══════════════════════════════════════════════════════════════════

            # Ações: 0=SKIP, 1=BET_LOW, 2=BET_MEDIUM, 3=BET_HIGH
            self.action_space = spaces.Discrete(4)

            # Observação:
            # - history_size valores de explosões (normalizados 0-1)
            # - saldo normalizado (0-2, onde 1 = inicial)
            # - dobra atual normalizada (0-1)
            # - streak de baixas normalizado (0-1)
            # - média móvel normalizada (0-1)
            # - volatilidade normalizada (0-1)
            obs_size = history_size + 5

            self.observation_space = spaces.Box(
                low=0.0,
                high=2.0,
                shape=(obs_size,),
                dtype=np.float32,
            )

            # Estado interno
            self._reset_state()

            logger.debug(
                f"CrashGameEnv inicializado: balance={initial_balance}, history={history_size}"
            )

        def _reset_state(self) -> None:
            """Reseta estado interno."""
            self._balance = self._initial_balance
            self._dobra = 1
            self._round = 0
            self._history: List[float] = []
            self._streak = 0
            self._total_profit = 0.0
            self._wins = 0
            self._losses = 0
            self._skips = 0
            self._last_result: Optional[BetResult] = None

        def reset(
            self,
            seed: Optional[int] = None,
            options: Optional[Dict] = None,
        ) -> Tuple[np.ndarray, Dict]:
            """
            Reseta o ambiente para um novo episódio.

            Returns:
                Tupla (observação_inicial, info)
            """
            super().reset(seed=seed)

            self._reset_state()

            # Preenche histórico inicial com valores aleatórios
            for _ in range(self._history_size):
                self._history.append(self._generate_explosion())

            # Reset índice de dados reais
            if self._use_real_data and self._real_data:
                self._real_data_index = random.randint(
                    0, max(0, len(self._real_data) - self._max_rounds)
                )

            return self._get_observation(), self._get_info()

        def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
            """
            Executa uma ação no ambiente.

            Args:
                action: Ação a executar (0-3)

            Returns:
                Tupla (observação, recompensa, terminado, truncado, info)
            """
            self._round += 1

            # Gera explosão desta rodada
            explosion = self._generate_explosion()
            self._history.append(explosion)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size :]

            # Atualiza streak
            if explosion < 2.0:
                self._streak += 1
            else:
                self._streak = 0

            # Processa ação
            action_type = ActionType(action)
            reward = 0.0

            if action_type == ActionType.SKIP:
                # Não apostou
                self._skips += 1

                # Pequena penalidade se pulou em sequência de baixas (oportunidade perdida)
                if self._streak >= 6:
                    reward = -0.01  # Penalidade leve
                elif explosion >= 2.0:
                    reward = 0.01  # Pequena recompensa por evitar alta

                self._last_result = None

            else:
                # Apostou
                target = self._targets[action_type]
                bet_amount = self._get_bet_amount()

                balance_before = self._balance

                if explosion >= target:
                    # WIN
                    profit = bet_amount * (target - 1)
                    self._balance += profit
                    self._wins += 1
                    self._total_profit += profit

                    # Recompensa proporcional ao lucro
                    reward = profit / self._initial_balance

                    # Reseta martingale
                    self._dobra = 1

                    won = True
                else:
                    # LOSS
                    self._balance -= bet_amount
                    self._losses += 1
                    self._total_profit -= bet_amount

                    # Penalidade proporcional à perda
                    reward = -bet_amount / self._initial_balance

                    # Avança martingale
                    if self._dobra < self._max_dobra:
                        self._dobra += 1
                    else:
                        # Resetou martingale por atingir máximo
                        self._dobra = 1
                        reward -= 0.1  # Penalidade extra por perder ciclo completo

                    won = False

                self._last_result = BetResult(
                    action=action_type,
                    bet_amount=bet_amount,
                    target=target,
                    explosion_value=explosion,
                    won=won,
                    profit=profit if won else -bet_amount,
                    balance_before=balance_before,
                    balance_after=self._balance,
                )

            # Bônus por manter saldo positivo
            if self._balance > self._initial_balance:
                reward += 0.001

            # Verifica condições de término
            terminated = False
            truncated = False

            # Faliu
            if self._balance < self._base_bet:
                terminated = True
                reward -= 1.0  # Grande penalidade por falir

            # Atingiu máximo de rodadas
            if self._round >= self._max_rounds:
                truncated = True
                # Bônus por sobreviver o episódio todo
                if self._balance > self._initial_balance:
                    reward += 0.5

            return (
                self._get_observation(),
                reward,
                terminated,
                truncated,
                self._get_info(),
            )

        def _generate_explosion(self) -> float:
            """Gera um valor de explosão."""
            if self._use_real_data and self._real_data:
                # Usa dados reais
                if self._real_data_index < len(self._real_data):
                    value = self._real_data[self._real_data_index]
                    self._real_data_index += 1
                    return value

            # Gera valor sintético com distribuição realista
            rand = random.random()

            if rand < EXPLOSION_DISTRIBUTION["low_prob"]:
                # Baixa
                return random.uniform(*EXPLOSION_DISTRIBUTION["low_range"])
            elif (
                rand
                < EXPLOSION_DISTRIBUTION["low_prob"]
                + EXPLOSION_DISTRIBUTION["medium_prob"]
            ):
                # Média
                return random.uniform(*EXPLOSION_DISTRIBUTION["medium_range"])
            else:
                # Alta
                return random.uniform(*EXPLOSION_DISTRIBUTION["high_range"])

        def _get_bet_amount(self) -> float:
            """Calcula valor da aposta atual."""
            multiplier = self._martingale_multipliers.get(self._dobra, 1)
            return self._base_bet * multiplier

        def _get_observation(self) -> np.ndarray:
            """Constrói o vetor de observação."""
            # Normaliza histórico (divide por 10 para manter em range razoável)
            history_norm = (
                np.array(self._history[-self._history_size :], dtype=np.float32) / 10.0
            )

            # Pad se necessário
            if len(history_norm) < self._history_size:
                padding = np.zeros(
                    self._history_size - len(history_norm), dtype=np.float32
                )
                history_norm = np.concatenate([padding, history_norm])

            # Features adicionais
            balance_norm = self._balance / self._initial_balance
            dobra_norm = self._dobra / self._max_dobra
            streak_norm = min(self._streak, 15) / 15.0

            # Média e std das últimas explosões
            if self._history:
                mean_norm = np.mean(self._history) / 10.0
                std_norm = np.std(self._history) / 5.0
            else:
                mean_norm = 0.0
                std_norm = 0.0

            # Concatena tudo
            obs = np.concatenate(
                [
                    history_norm,
                    [balance_norm, dobra_norm, streak_norm, mean_norm, std_norm],
                ]
            ).astype(np.float32)

            # Clipa para garantir que está no range
            obs = np.clip(obs, 0.0, 2.0)

            return obs

        def _get_info(self) -> Dict[str, Any]:
            """Retorna informações adicionais."""
            return {
                "round": self._round,
                "balance": self._balance,
                "dobra": self._dobra,
                "streak": self._streak,
                "wins": self._wins,
                "losses": self._losses,
                "skips": self._skips,
                "total_profit": self._total_profit,
                "win_rate": self._wins / max(1, self._wins + self._losses),
                "last_result": self._last_result,
            }

        def render(self) -> Optional[str]:
            """Renderiza o estado atual."""
            if self._render_mode == "ansi" or self._render_mode == "human":
                info = self._get_info()

                lines = [
                    f"\n{'='*50}",
                    f"Round: {info['round']} | Balance: R$ {info['balance']:.2f}",
                    f"Dobra: {info['dobra']} | Streak: {info['streak']}",
                    f"Wins: {info['wins']} | Losses: {info['losses']} | Skips: {info['skips']}",
                    f"Profit: R$ {info['total_profit']:.2f} | Win Rate: {info['win_rate']:.1%}",
                ]

                if self._last_result:
                    r = self._last_result
                    result_str = "WIN" if r.won else "LOSS"
                    lines.append(
                        f"Last: {r.action.name} @ {r.target}x -> {r.explosion_value:.2f}x = {result_str}"
                    )

                lines.append(f"Last 5: {[f'{v:.2f}' for v in self._history[-5:]]}")
                lines.append(f"{'='*50}")

                output = "\n".join(lines)

                if self._render_mode == "human":
                    print(output)

                return output

            return None

        def set_real_data(self, data: List[float]) -> None:
            """Define dados reais para usar."""
            self._real_data = data
            self._use_real_data = True
            logger.info(f"Dados reais configurados: {len(data)} explosões")

        def get_action_meanings(self) -> List[str]:
            """Retorna significado das ações."""
            return ["SKIP", "BET_1.5x", "BET_2.0x", "BET_3.0x"]


# ═══════════════════════════════════════════════════════════════════════════════
# WRAPPER PARA AMBIENTE (Normalização, etc)
# ═══════════════════════════════════════════════════════════════════════════════

if HAS_GYM:

    class NormalizedCrashEnv(gym.Wrapper):
        """
        Wrapper que normaliza recompensas e adiciona estatísticas.
        """

        def __init__(self, env: CrashGameEnv, clip_reward: float = 10.0):
            super().__init__(env)
            self._clip_reward = clip_reward
            self._episode_rewards: List[float] = []
            self._episode_lengths: List[int] = []
            self._current_episode_reward = 0.0
            self._current_episode_length = 0

        def reset(self, **kwargs):
            # Salva estatísticas do episódio anterior
            if self._current_episode_length > 0:
                self._episode_rewards.append(self._current_episode_reward)
                self._episode_lengths.append(self._current_episode_length)

            self._current_episode_reward = 0.0
            self._current_episode_length = 0

            return self.env.reset(**kwargs)

        def step(self, action):
            obs, reward, terminated, truncated, info = self.env.step(action)

            # Clipa recompensa
            reward = np.clip(reward, -self._clip_reward, self._clip_reward)

            # Atualiza estatísticas
            self._current_episode_reward += reward
            self._current_episode_length += 1

            # Adiciona estatísticas ao info
            info["episode_reward"] = self._current_episode_reward
            info["episode_length"] = self._current_episode_length

            return obs, reward, terminated, truncated, info

        def get_episode_stats(self) -> Dict[str, float]:
            """Retorna estatísticas dos episódios."""
            if not self._episode_rewards:
                return {"mean_reward": 0, "mean_length": 0}

            return {
                "mean_reward": np.mean(self._episode_rewards[-100:]),
                "std_reward": np.std(self._episode_rewards[-100:]),
                "mean_length": np.mean(self._episode_lengths[-100:]),
                "total_episodes": len(self._episode_rewards),
            }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def make_crash_env(
    initial_balance: float = 1000.0,
    base_bet: float = 10.0,
    history_size: int = 20,
    max_rounds: int = 1000,
    normalize: bool = True,
    real_data: Optional[List[float]] = None,
) -> gym.Env:
    """
    Factory para criar ambiente Crash.

    Args:
        initial_balance: Saldo inicial
        base_bet: Aposta base
        history_size: Tamanho do histórico
        max_rounds: Máximo de rodadas
        normalize: Se True, aplica wrapper de normalização
        real_data: Dados reais (opcional)

    Returns:
        Ambiente Gymnasium
    """
    if not HAS_GYM:
        raise ImportError(
            "Gymnasium não encontrado. Instale com: pip install gymnasium"
        )

    env = CrashGameEnv(
        initial_balance=initial_balance,
        base_bet=base_bet,
        history_size=history_size,
        max_rounds=max_rounds,
        use_real_data=real_data is not None,
        real_data=real_data,
    )

    if normalize:
        env = NormalizedCrashEnv(env)

    return env


def make_vectorized_env(
    num_envs: int = 4,
    **env_kwargs,
) -> gym.vector.VectorEnv:
    """
    Cria ambientes vetorizados para treino paralelo.

    Args:
        num_envs: Número de ambientes paralelos
        **env_kwargs: Argumentos para CrashGameEnv

    Returns:
        VectorEnv com múltiplos ambientes
    """
    if not HAS_GYM:
        raise ImportError("Gymnasium não encontrado")

    def make_env():
        return make_crash_env(**env_kwargs)

    return gym.vector.SyncVectorEnv([make_env for _ in range(num_envs)])


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO CRASH GAME ENVIRONMENT - CrashBot v3.0")
    print("=" * 60)

    if not HAS_GYM:
        print("❌ Gymnasium não instalado!")
        exit(1)

    print(f"\n✅ Gymnasium disponível")

    # Cria ambiente
    env = make_crash_env(
        initial_balance=1000.0,
        base_bet=10.0,
        history_size=20,
        max_rounds=100,
        normalize=True,
    )

    print(f"\n✅ Ambiente criado")
    print(f"   Action space: {env.action_space}")
    print(f"   Observation space: {env.observation_space}")
    print(f"   Actions: {env.unwrapped.get_action_meanings()}")

    # Simula alguns episódios
    print(f"\n--- Simulação ---")

    num_episodes = 3

    for episode in range(num_episodes):
        state, info = env.reset()
        total_reward = 0
        steps = 0

        while True:
            # Ação aleatória (substitua pelo agente)
            action = env.action_space.sample()

            next_state, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1

            if terminated or truncated:
                break

            state = next_state

        print(f"\n   Episódio {episode + 1}:")
        print(f"      Steps: {steps}")
        print(f"      Reward total: {total_reward:.2f}")
        print(f"      Balance final: R$ {info['balance']:.2f}")
        print(f"      Win rate: {info['win_rate']:.1%}")
        print(f"      Profit: R$ {info['total_profit']:.2f}")

    # Estatísticas
    if hasattr(env, "get_episode_stats"):
        print(f"\n--- Estatísticas ---")
        stats = env.get_episode_stats()
        for key, value in stats.items():
            print(f"   {key}: {value:.2f}")

    env.close()

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
