#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - ENGINE ML MODULE

Sistema de Machine Learning e Inteligência Artificial.

Módulos:
- data_collector: Coleta e preparação de dados
- predictor_lstm: Rede neural LSTM para previsão
- rl_environment: Ambiente Gymnasium para RL
- rl_agent: Agente de Reinforcement Learning
- optimizer: Otimização de hiperparâmetros com Optuna
- decision_engine: Motor de decisão que combina todos os sinais

Uso Básico:
    from engine.ml import get_decision_engine, get_collector

    # Coleta dados
    collector = get_collector()
    collector.add_explosion(1.45)

    # Obtém decisão
    engine = get_decision_engine()
    decision = engine.get_decision(explosions=collector.get_recent_explosions(20))

    if decision.should_bet:
        print(f"Apostar R$ {decision.bet_info.amount}")

Uso Avançado (com treinamento):
    from engine.ml import (
        get_collector,
        get_predictor,
        get_agent,
        get_optimizer,
        get_decision_engine,
    )

    # 1. Coleta dados
    collector = get_collector()
    collector.import_from_csv("historico.csv")

    # 2. Treina LSTM
    X, y = collector.get_training_data_with_features(sequence_length=20)
    predictor = get_predictor()
    predictor.train(X, y, epochs=100)

    # 3. Treina RL Agent
    agent = get_agent()
    agent.train(total_timesteps=100000)

    # 4. Otimiza parâmetros
    optimizer = get_optimizer()
    result = optimizer.optimize_strategy(collector.get_explosions_array().tolist())

    # 5. Configura Decision Engine
    engine = get_decision_engine()
    engine.load_optimized_params(optimizer.apply_best_params(result))
    engine.configure_weights(rules=0.3, lstm=0.35, rl=0.35)
"""

# ═══════════════════════════════════════════════════════════════════════════════
# DATA COLLECTOR
# ═══════════════════════════════════════════════════════════════════════════════

from engine.ml.data_collector import (
    BetRecord,
    DataCollector,
    ExplosionRecord,
    SessionStats,
    get_collector,
    reset_collector,
)

# ═══════════════════════════════════════════════════════════════════════════════
# LSTM PREDICTOR
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from engine.ml.predictor_lstm import (
        AttentionLSTMModel,
        LSTMModel,
        LSTMPredictor,
        Prediction,
        PredictionMode,
        TrainingMetrics,
        get_predictor,
        reset_predictor,
    )

    HAS_LSTM = True
except ImportError:
    HAS_LSTM = False
    LSTMPredictor = None
    get_predictor = None

# ═══════════════════════════════════════════════════════════════════════════════
# RL ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from engine.ml.rl_environment import (
        ActionType,
        BetResult,
        CrashGameEnv,
        GamePhase,
        NormalizedCrashEnv,
        make_crash_env,
        make_vectorized_env,
    )

    HAS_RL_ENV = True
except ImportError:
    HAS_RL_ENV = False
    CrashGameEnv = None
    make_crash_env = None

# ═══════════════════════════════════════════════════════════════════════════════
# RL AGENT
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from engine.ml.rl_agent import (
        PredictionResult,
        RLAgent,
        RLAlgorithm,
        TrainingConfig,
        get_agent,
        reset_agent,
    )

    HAS_RL_AGENT = True
except ImportError:
    HAS_RL_AGENT = False
    RLAgent = None
    get_agent = None

# ═══════════════════════════════════════════════════════════════════════════════
# OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from engine.ml.optimizer import (
        HyperOptimizer,
        OptimizationResult,
        OptimizationTarget,
        StrategyParams,
        StrategySimulator,
        get_optimizer,
        reset_optimizer,
    )

    HAS_OPTIMIZER = True
except ImportError:
    HAS_OPTIMIZER = False
    HyperOptimizer = None
    get_optimizer = None

# ═══════════════════════════════════════════════════════════════════════════════
# DECISION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

from engine.ml.decision_engine import (
    ActionDecision,
    DecisionEngine,
    DecisionSource,
    EngineConfig,
    FinalDecision,
    SignalVote,
    get_decision_engine,
    reset_decision_engine,
)

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Flags de disponibilidade
    "HAS_LSTM",
    "HAS_RL_ENV",
    "HAS_RL_AGENT",
    "HAS_OPTIMIZER",
    # Data Collector
    "DataCollector",
    "ExplosionRecord",
    "BetRecord",
    "SessionStats",
    "get_collector",
    "reset_collector",
    # LSTM Predictor
    "LSTMPredictor",
    "LSTMModel",
    "AttentionLSTMModel",
    "PredictionMode",
    "Prediction",
    "TrainingMetrics",
    "get_predictor",
    "reset_predictor",
    # RL Environment
    "CrashGameEnv",
    "NormalizedCrashEnv",
    "GamePhase",
    "ActionType",
    "BetResult",
    "make_crash_env",
    "make_vectorized_env",
    # RL Agent
    "RLAgent",
    "RLAlgorithm",
    "TrainingConfig",
    "PredictionResult",
    "get_agent",
    "reset_agent",
    # Optimizer
    "HyperOptimizer",
    "OptimizationTarget",
    "OptimizationResult",
    "StrategyParams",
    "StrategySimulator",
    "get_optimizer",
    "reset_optimizer",
    # Decision Engine
    "DecisionEngine",
    "DecisionSource",
    "ActionDecision",
    "SignalVote",
    "FinalDecision",
    "EngineConfig",
    "get_decision_engine",
    "reset_decision_engine",
]


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO DE DEPENDÊNCIAS
# ═══════════════════════════════════════════════════════════════════════════════


def check_dependencies() -> dict:
    """
    Verifica quais dependências de ML estão disponíveis.

    Returns:
        Dicionário com status de cada dependência
    """
    deps = {}

    # NumPy (obrigatório)
    try:
        import numpy

        deps["numpy"] = {"available": True, "version": numpy.__version__}
    except ImportError:
        deps["numpy"] = {"available": False}

    # PyTorch
    try:
        import torch

        deps["torch"] = {
            "available": True,
            "version": torch.__version__,
            "cuda": torch.cuda.is_available(),
        }
    except ImportError:
        deps["torch"] = {"available": False}

    # Gymnasium
    try:
        import gymnasium

        deps["gymnasium"] = {"available": True, "version": gymnasium.__version__}
    except ImportError:
        deps["gymnasium"] = {"available": False}

    # Stable-Baselines3
    try:
        import stable_baselines3

        deps["stable_baselines3"] = {
            "available": True,
            "version": stable_baselines3.__version__,
        }
    except ImportError:
        deps["stable_baselines3"] = {"available": False}

    # Optuna
    try:
        import optuna

        deps["optuna"] = {"available": True, "version": optuna.__version__}
    except ImportError:
        deps["optuna"] = {"available": False}

    # Pandas
    try:
        import pandas

        deps["pandas"] = {"available": True, "version": pandas.__version__}
    except ImportError:
        deps["pandas"] = {"available": False}

    return deps


def get_ml_status() -> dict:
    """
    Retorna status geral do módulo ML.

    Returns:
        Dicionário com status dos componentes
    """
    return {
        "lstm_available": HAS_LSTM,
        "rl_env_available": HAS_RL_ENV,
        "rl_agent_available": HAS_RL_AGENT,
        "optimizer_available": HAS_OPTIMIZER,
        "dependencies": check_dependencies(),
    }
