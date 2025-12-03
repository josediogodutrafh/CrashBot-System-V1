#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""STRATEGY ENGINE - Motor de estratégias com Modos de Risco Comerciais"""

import logging
import random
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import notification_manager
import numpy as np
from learning_engine import REQUIRED_HISTORY_FOR_PREDICTION, LearningEngine

# --- CONFIGURAÇÃO DO LOGGER ---
project_root = Path(__file__).parent.parent
log_path = project_root / "logs" / "strategy_engine.log"

# Garante que o diretório de logs exista
log_path.parent.mkdir(parents=True, exist_ok=True)

# Define o logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Evita duplicidade de handlers se o módulo for recarregado
if not logger.handlers:
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
# --- FIM DO BLOCO DO LOGGER ---


class RiskMode(Enum):
    """Enum para os modos de risco comerciais."""

    CONSERVADOR = 1
    MODERADO = 2
    AGRESSIVO = 3


# Configurações de cada modo de risco
RISK_MODE_CONFIG = {
    RiskMode.CONSERVADOR: {
        "banca_percent": 0.33,  # Usa 33% da banca real
        "gatilho_opcoes": [8],  # Sempre 8 velas
        "meta_min": 0.25,  # Meta entre 25% e 40%
        "meta_max": 0.40,
    },
    RiskMode.MODERADO: {
        "banca_percent": 0.50,  # Usa 50% da banca real
        "gatilho_opcoes": [7, 8],  # Sorteia entre 7 ou 8
        "meta_min": 0.30,  # Meta entre 30% e 45%
        "meta_max": 0.45,
    },
    RiskMode.AGRESSIVO: {
        "banca_percent": 1.00,  # Usa 100% da banca real
        "gatilho_opcoes": [6, 7],  # Sorteia entre 6 ou 7
        "meta_min": 0.35,  # Meta entre 35% e 55%
        "meta_max": 0.55,
    },
}

# Tempo de suspensão fixo (4 horas em segundos)
TEMPO_SUSPENSAO_FIXO = 4 * 3600


@dataclass
class BetRecommendation:
    """Estrutura para recomendações de apostas"""

    strategy_name: str
    bet_1: float
    target_1: float
    bet_2: float
    target_2: float
    justification: str
    confidence: float
    ready: bool = False


class StrategyPolicy(ABC):
    """
    Uma interface para uma estratégia completa, que gerencia
    seu próprio gatilho, dimensionamento e estado interno.
    """

    def __init__(
        self, banca_inicial: float, learning_engine: Optional[LearningEngine] = None
    ):
        self.banca_inicial = banca_inicial
        self.le = learning_engine
        self.is_active = False

    @abstractmethod
    def check_trigger(self, history: deque) -> bool:
        """Verifica se a estratégia deve ser ativada (se não estiver ativa)."""
        pass

    @abstractmethod
    def get_bet_recommendation(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        """Se estiver ativa, retorna a aposta."""
        pass

    @abstractmethod
    def process_result(self, explosion_value: float):
        """Processa o resultado rodada (se estava ativa) e atualiza interno."""
        pass


class CommercialMartingalePolicy(StrategyPolicy):
    """
    Estratégia Martingale Comercial com 3 Modos de Risco.
    Substitui a antiga Martingale8LowPolicy.
    """

    def __init__(
        self,
        banca_inicial: float,
        risk_mode: RiskMode,
        learning_engine: Optional[LearningEngine] = None,
    ):
        super().__init__(banca_inicial, learning_engine)

        # Configuração do modo de risco
        self.risk_mode = risk_mode
        self.config = RISK_MODE_CONFIG[risk_mode]

        # Calcula a banca operacional baseada no modo
        self.banca_operacional = banca_inicial * self.config["banca_percent"]

        # Estado do Martingale
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        self.modo_continuo = False
        self.target_ativo = 0.0

        # Gatilho - sorteia no início do ciclo
        self.lows_needed = self._sortear_gatilho()
        self.threshold = 2.0

        # Política de sizing baseada na banca operacional
        self.sizing_policy = CommercialMartingale15(self.banca_operacional)

        # Alerta de 6 lows
        self.alerta_6_lows_enviado = False

        logger.info(
            f"CommercialMartingalePolicy iniciada - Modo: {risk_mode.name}, "
            f"Banca Op.: R${self.banca_operacional:.2f}, "
            f"Gatilho: {self.lows_needed} velas"
        )

    def _sortear_gatilho(self) -> int:
        """Sorteia o número de velas baixas necessárias baseado no modo."""
        opcoes = self.config["gatilho_opcoes"]
        gatilho = random.choice(opcoes)
        logger.debug(f"Gatilho sorteado: {gatilho} velas (opções: {opcoes})")
        return gatilho

    def _sortear_target(self) -> float:
        """Sorteia o target de saída entre 1.81x e 1.95x."""
        target = round(random.uniform(1.81, 1.95), 2)
        logger.debug(f"Target sorteado: {target}x")
        return target

    def _count_consecutive_lows(self, history: deque) -> int:
        """Conta os valores baixos consecutivos no final do histórico."""
        count = 0
        for value in reversed(history):
            if value < self.threshold:
                count += 1
            else:
                break
        return count

    def _activate_strategy(self):
        """Define o estado interno para ativar a estratégia."""
        self.is_active = True
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        self.modo_continuo = False
        logger.info(f"ATIVANDO CommercialMartingalePolicy - Modo {self.risk_mode.name}")

    def check_trigger(self, history: deque) -> bool:
        """Verifica o gatilho de velas baixas."""
        if self.is_active:
            return False

        lows_count = self._count_consecutive_lows(history)

        logger.debug("--- [MARTINGALE COMERCIAL] Verificando Gatilho ---")
        logger.debug(f"Histórico recente (últimos 10): {list(history)[-10:]}")
        logger.debug(
            f"Contagem de 'lows' consecutivos: {lows_count}/{self.lows_needed}"
        )

        # Alerta de 6 lows via Telegram
        try:
            if lows_count == 6 and not self.alerta_6_lows_enviado:
                msg = (
                    f"⚠️ ALERTA: 6 'lows' (< {self.threshold}x) consecutivos. "
                    f"Modo: {self.risk_mode.name}"
                )
                notification_manager.send_telegram_alert(msg)
                self.alerta_6_lows_enviado = True
            elif lows_count < 6 and self.alerta_6_lows_enviado:
                self.alerta_6_lows_enviado = False
        except Exception as e:
            logger.error(f"Falha ao enviar alerta de 6 lows: {e}")

        return self._handle_trigger_condition(lows_count, history)

    def _handle_trigger_condition(self, lows_count: int, history: deque) -> bool:
        """Processa a lógica de decisão após a contagem de 'lows'."""
        if lows_count >= self.lows_needed:
            logger.debug(
                f"Gatilho ({self.lows_needed} lows) ATINGIDO. "
                "Verificando condições de segurança..."
            )

            resultado_seguranca = self._check_safety_conditions(history)
            logger.debug(
                f"Resultado da verificação de segurança: {resultado_seguranca}"
            )

            if not resultado_seguranca:
                logger.warning(
                    "[MARTINGALE COMERCIAL] DECISÃO: Veto de segurança. Não apostar."
                )
                return False

            logger.info(
                f"Gatilho de {self.lows_needed} baixos validado. "
                "Stats de segurança OK."
            )
            logger.debug("[MARTINGALE COMERCIAL] DECISÃO: Seguro para APOSTAR.")
            self._activate_strategy()
            return True

        logger.debug(
            f"[MARTINGALE COMERCIAL] DECISÃO: Gatilho ({self.lows_needed} lows) "
            "NÃO ATINGIDO. Não apostar."
        )
        return False

    def _check_safety_conditions(self, history: deque) -> bool:
        """
        Verifica se as condições atuais do jogo são seguras para ativar,
        evitando a "Fase Arrecadatória".
        """
        if len(history) < 20:
            logger.warning(
                f"Gatilho de {self.lows_needed} baixos detectado, "
                "mas histórico < 20. Abortando por segurança."
            )
            return False

        recent_history = list(history)[-20:]
        current_std_20 = np.std(recent_history)
        current_mean_20 = np.mean(recent_history)

        DANGER_STD_THRESHOLD = 2.3
        DANGER_MEAN_THRESHOLD = 2.5

        if (current_std_20 < DANGER_STD_THRESHOLD) or (
            current_mean_20 < DANGER_MEAN_THRESHOLD
        ):
            logger.warning(
                "[SEGURANÇA] Gatilho IGNORADO. "
                "Risco de 'Fase Arrecadatória' detectado!"
            )
            logger.warning(
                f"[SEGURANÇA] Stats: Média(20)={current_mean_20:.2f} "
                f"(Limite: {DANGER_MEAN_THRESHOLD:.2f}), "
                f"Std(20)={current_std_20:.2f} (Limite: {DANGER_STD_THRESHOLD:.2f})"
            )
            return False

        return True

    def get_bet_recommendation(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        if not self.is_active:
            return None

        bet_1 = self.sizing_policy.get_bet(self.dobra_atual, current_balance)
        # Target randomizado a cada aposta (anti-detecção)
        target_1 = self._sortear_target()
        self.target_ativo = target_1

        return BetRecommendation(
            strategy_name=f"Martingale {self.risk_mode.name} - Dobra {self.dobra_atual}",
            bet_1=bet_1,
            target_1=target_1,
            bet_2=0,
            target_2=0,
            justification=f"Dobra {self.dobra_atual}/{self.lows_needed} - Target {target_1}x",
            confidence=1.0,
            ready=True,
        )

    def process_result(self, explosion_value: float):
        if not self.is_active:
            return

        target = self.target_ativo

        if explosion_value < target:
            logger.warning(f"CommercialMartingalePolicy: PERDEU (< {target:.2f}x)")
            self.perdas_consecutivas += 1
            if self.dobra_atual >= 4:
                self._reset_cycle()
            else:
                self.dobra_atual += 1

        elif target <= explosion_value <= 1.99:
            logger.info("CommercialMartingalePolicy: GANHO (volta para dobra 2)")
            self.dobra_atual = 2
            self.perdas_consecutivas = 0
            self.modo_continuo = True

        else:  # Ganho >= 2.00
            logger.info("CommercialMartingalePolicy: GANHO TOTAL (Ciclo concluído)")
            self._reset_cycle()

    def _reset_cycle(self):
        """Reseta o ciclo e sorteia novo gatilho para o próximo ciclo."""
        self.is_active = False
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        self.modo_continuo = False
        self.target_ativo = 0.0
        # Sorteia novo gatilho para o próximo ciclo
        self.lows_needed = self._sortear_gatilho()


class CommercialMartingale15(ABC):
    """Política de sizing para o Martingale Comercial (banca/15)."""

    def __init__(self, banca_operacional: float):
        self.valores_fixos = self._definir_valores(banca_operacional)

    def _definir_valores(self, banca_operacional: float):
        multipliers = {1: 1, 2: 2, 3: 4, 4: 8}
        return {
            dobra: max(1.0, round((banca_operacional / 15) * mult, 2))
            for dobra, mult in multipliers.items()
        }

    def get_bet(self, dobra_atual: int, banca_atual: float) -> float:
        return self.valores_fixos.get(dobra_atual, self.valores_fixos[1])

    def get_target(self, dobra_atual: int) -> float:
        # Este método não é mais usado (target é randomizado)
        return 1.84


class MLHighConfidencePolicy(StrategyPolicy):
    """
    Uma estratégia que faz uma APOSTA ÚNICA quando o ML está
    com alta confiança. (Sniper - Roda em paralelo)
    """

    def __init__(
        self, banca_inicial: float, learning_engine: Optional[LearningEngine] = None
    ):
        super().__init__(banca_inicial, learning_engine)
        self.confidence_threshold = 0.80
        self.bet_size_percent = 0.01
        self.last_calculated_prob: float = 0.0

    def check_trigger(self, history: deque) -> bool:
        if self.is_active or not self.le:
            return False

        recent_history = list(history)[-REQUIRED_HISTORY_FOR_PREDICTION:]
        if len(recent_history) < REQUIRED_HISTORY_FOR_PREDICTION:
            self.last_calculated_prob = 0.0
            return False

        probability = self.le.predict(recent_history)

        if probability is None:
            self.last_calculated_prob = 0.0
            return False

        self.last_calculated_prob = probability

        if probability >= self.confidence_threshold:
            logger.info(
                f"ATIVANDO MLHighConfidencePolicy (Confiança: {probability:.2%})"
            )
            self.is_active = True
            return True

        return False

    def get_bet_recommendation(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        if not self.is_active:
            return None

        bet_1 = max(1.0, current_balance * self.bet_size_percent)

        return BetRecommendation(
            strategy_name="ML High Confidence (Sniper)",
            bet_1=bet_1,
            target_1=2.0,
            bet_2=0,
            target_2=0,
            justification=f"Confiança do modelo > {self.confidence_threshold:.0%}",
            confidence=self.confidence_threshold,
            ready=True,
        )

    def process_result(self, explosion_value: float):
        if self.is_active:
            if explosion_value >= 2.0:
                logger.info("MLHighConfidencePolicy: HIT")
            else:
                logger.warning("MLHighConfidencePolicy: MISS")
            self.is_active = False

    def evaluate_executed_bet(self, explosion_value: float, executed_bet: Dict) -> Dict:
        """Avalia resultado de aposta executada."""
        target_1 = executed_bet.get("target_1", 0)
        hit_1 = explosion_value >= target_1 if target_1 > 0 else False

        return {
            "explosion_value": explosion_value,
            "recommendation_hit": hit_1,
            "target_1": target_1,
            "bet_1": executed_bet.get("bet_1", 0),
            "strategy": executed_bet.get("strategy", ""),
            "phase": "N/A",
        }


class StrategyEngine:
    """Motor de estratégias com suporte a Modos de Risco Comerciais."""

    def __init__(self, learning_engine: LearningEngine):
        self.explosion_history = deque(maxlen=260)
        self.learning_engine = learning_engine
        self.policies: Sequence[StrategyPolicy] = []

        # Estado do Motor
        self.banca_inicial: Optional[float] = None
        self.banca_real: Optional[float] = None
        self.suspenso_ate: Optional[float] = None
        self.meta_lucro_percentual: Optional[float] = None
        self.tempo_suspensao_horas = 4  # Fixo em 4 horas

        # Modo de risco atual
        self.risk_mode: Optional[RiskMode] = None

        # Aposta preparada
        self.aposta_preparada: Optional[BetRecommendation] = None

        # Estatísticas
        self.strategy_stats: Dict[str, Dict] = {}

    def iniciar_sessao(self, banca_inicial: float, risk_mode: RiskMode):
        """
        Inicia a sessão com o modo de risco escolhido.
        Calcula automaticamente a meta baseada no modo.
        """
        self.banca_real = banca_inicial
        self.risk_mode = risk_mode

        # Pega a configuração do modo
        config = RISK_MODE_CONFIG[risk_mode]

        # Calcula a banca operacional
        self.banca_operacional = banca_inicial * config["banca_percent"]

        self.banca_inicial = banca_inicial

        # Sorteia a meta de lucro dentro do range do modo
        self.meta_lucro_percentual = random.uniform(
            config["meta_min"], config["meta_max"]
        )

        # Loga as configurações
        meta_valor_abs = self.banca_inicial * (1 + self.meta_lucro_percentual)
        logger.info(f"=== SESSÃO INICIADA - MODO {risk_mode.name} ===")
        logger.info(f"Banca Real: R$ {banca_inicial:.2f}")
        logger.info(
            f"Banca Operacional ({config['banca_percent']:.0%}): "
            f"R$ {self.banca_operacional:.2f}"
        )
        logger.info(
            f"Meta de Lucro Sorteada: {self.meta_lucro_percentual:.1%} "
            f"(Atingir R$ {meta_valor_abs:.2f})"
        )
        logger.info(f"Suspensão após meta: {self.tempo_suspensao_horas} horas (fixo)")

        # Inicia as políticas
        self.policies = [
            CommercialMartingalePolicy(banca_inicial, risk_mode, self.learning_engine),
            MLHighConfidencePolicy(banca_inicial, self.learning_engine),
        ]

        # Prepara o dict de estatísticas
        for policy in self.policies:
            policy_name = policy.__class__.__name__
            if policy_name not in self.strategy_stats:
                self.strategy_stats[policy_name] = {
                    "total_recommendations": 0,
                    "total_hits": 0,
                    "total_misses": 0,
                    "total_profit_loss": 0.0,
                    "hit_rate": 0.0,
                    "profit_loss": 0.0,
                }

    def _reiniciar_ciclo_pos_meta(self, saldo_atual: float):
        """
        Reinicia o ciclo após a suspensão terminar.
        Sempre usa o saldo atual como nova banca (modo reinvestir).
        """
        if self.risk_mode is None:
            logger.error("Risk mode não definido. Não é possível reiniciar.")
            return

        config = RISK_MODE_CONFIG[self.risk_mode]

        self.banca_real = saldo_atual
        self.banca_inicial = saldo_atual * config["banca_percent"]

        # Sorteia nova meta
        self.meta_lucro_percentual = random.uniform(
            config["meta_min"], config["meta_max"]
        )

        logger.info(
            f"CICLO REINICIADO - Modo {self.risk_mode.name} | "
            f"Nova Banca Op.: R$ {self.banca_inicial:.2f} | "
            f"Nova Meta: {self.meta_lucro_percentual:.1%}"
        )

        # Recria as políticas com a nova banca
        self.policies = [
            CommercialMartingalePolicy(
                saldo_atual, self.risk_mode, self.learning_engine
            ),
            MLHighConfidencePolicy(saldo_atual, self.learning_engine),
        ]

    def add_explosion_value(
        self, value: float
    ) -> Tuple[bool, Optional[BetRecommendation], Optional[str]]:
        """Método principal que processa cada explosão."""
        self.explosion_history.append(value)
        veto_message: Optional[str] = None

        # 1. Processar resultados das estratégias ativas
        for policy in self.policies:
            if policy.is_active:
                policy.process_result(value)

        # 2. Verificar gatilhos de estratégias inativas
        strategy_activated = False
        if not self.esta_suspenso():
            for policy in self.policies:
                if not policy.is_active:
                    triggered = policy.check_trigger(self.explosion_history)

                    if triggered:
                        strategy_activated = True

                    elif isinstance(policy, MLHighConfidencePolicy):
                        prob = policy.last_calculated_prob
                        thresh = policy.confidence_threshold

                        if 0 < prob < thresh:
                            veto_message = f"ML Veto: {prob:.1%} < {thresh:.0%}"
                        elif not strategy_activated:
                            veto_message = "Aguardando gatilhos..."

        return strategy_activated, None, veto_message

    def prepare_bets_for_balance(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        """Prepara apostas para o saldo atual."""
        for policy in self.policies:
            if policy.is_active:
                if recommendation := policy.get_bet_recommendation(current_balance):
                    self.aposta_preparada = recommendation
                    if stats := self.strategy_stats.get(policy.__class__.__name__):
                        stats["total_recommendations"] += 1
                    return recommendation

        self.reset_prepared_bets()
        return None

    def check_suspension_ended(self, saldo_atual: float) -> bool:
        """Verifica se a suspensão terminou."""
        if self.suspenso_ate is None:
            return False

        if time.time() >= self.suspenso_ate:
            self.suspenso_ate = None
            self._reiniciar_ciclo_pos_meta(saldo_atual)
            logger.info("Período de suspensão encerrado. Operações retomadas!")
            return True

        return False

    def esta_suspenso(self) -> bool:
        """Verifica se está no período de suspensão."""
        return self.suspenso_ate is not None and time.time() < self.suspenso_ate

    def get_tempo_restante_suspensao(self) -> int:
        """Retorna o tempo restante de suspensão em segundos."""
        if self.suspenso_ate is None:
            return 0
        restante = self.suspenso_ate - time.time()
        return max(0, int(restante))

    def checar_meta_lucro(self, saldo_atual: float) -> bool:
        """Verifica se atingiu meta de lucro e suspende operações."""
        if not self.banca_inicial or saldo_atual is None:
            return False

        if self.meta_lucro_percentual is None:
            return False

        meta = self.banca_inicial * (1 + self.meta_lucro_percentual)
        if saldo_atual >= meta:
            if not self.esta_suspenso():
                self.suspenso_ate = time.time() + TEMPO_SUSPENSAO_FIXO
                logger.info(
                    f"META ATINGIDA! Suspensão de {self.tempo_suspensao_horas} horas."
                )
            return True
        return False

    def reset_prepared_bets(self):
        """Reseta a aposta preparada."""
        self.aposta_preparada = None

    def get_prepared_bets(self) -> Optional[BetRecommendation]:
        """Retorna apostas preparadas."""
        return self.aposta_preparada

    def get_current_analysis(self) -> Dict:
        """Retorna análise atual do estado (para a UI)."""
        prepared = self.aposta_preparada is not None

        # Tenta obter o status da política Martingale Comercial
        martingale_policy = next(
            (p for p in self.policies if isinstance(p, CommercialMartingalePolicy)),
            None,
        )

        martingale_active = False
        dobra_atual = 1
        status_msg = "Aguardando gatilhos"
        baixos_consecutivos_str = "0/8"

        if martingale_policy:
            if martingale_policy.is_active:
                status_msg = f"Martingale Ativo (Dobra {martingale_policy.dobra_atual})"
                martingale_active = True
                dobra_atual = martingale_policy.dobra_atual

            try:
                current_lows = martingale_policy._count_consecutive_lows(
                    self.explosion_history
                )
                baixos_consecutivos_str = (
                    f"{current_lows}/{martingale_policy.lows_needed}"
                )
            except Exception:
                baixos_consecutivos_str = "Erro/8"

        # Confiança do ML
        ml_confidence = 0.0
        try:
            if (
                self.learning_engine
                and len(self.explosion_history) >= REQUIRED_HISTORY_FOR_PREDICTION
            ):
                recent_history = list(self.explosion_history)
                probability = self.learning_engine.predict(recent_history)
                if probability is not None:
                    ml_confidence = probability
        except Exception as e:
            logger.error(f"Erro ao calcular confiança do ML: {e}")
            ml_confidence = -1.0

        return {
            "history_size": len(self.explosion_history),
            "prepared_bets_ready": prepared,
            "status": status_msg,
            "martingale_active": martingale_active,
            "dobra_atual": dobra_atual,
            "ml_confidence": ml_confidence,
            "baixos_consecutivos": baixos_consecutivos_str,
            "risk_mode": self.risk_mode.name if self.risk_mode else "N/A",
            "suspenso": self.esta_suspenso(),
            "tempo_restante_suspensao": self.get_tempo_restante_suspensao(),
        }

    def get_strategies_stats(self) -> List[Dict]:
        """Retorna estatísticas das estratégias."""
        stats_list = []
        for strategy_name, data in self.strategy_stats.items():
            if data["total_recommendations"] > 0:
                data["hit_rate"] = (
                    data["total_hits"] / data["total_recommendations"]
                ) * 100

            stats_list.append(
                {
                    "name": strategy_name,
                    "total_recommendations": data["total_recommendations"],
                    "total_hits": data["total_hits"],
                    "total_misses": data["total_misses"],
                    "total_hit_rate": data["hit_rate"],
                    "profit_loss": data["profit_loss"],
                }
            )
        return stats_list

    def evaluate_executed_bet(self, explosion_value: float, executed_bet: Dict) -> Dict:
        """Avalia resultado de aposta executada."""
        target_1 = executed_bet.get("target_1", 0)
        bet_1 = executed_bet.get("bet_1", 0)
        hit_1 = explosion_value >= target_1 if target_1 > 0 else False
        strategy_name = executed_bet.get("strategy", "Desconhecida")

        # ✅ CALCULAR O LUCRO/PREJUÍZO (Versão Otimizada)
        profit_loss = (bet_1 * target_1) - bet_1 if hit_1 else -bet_1

        # Atualiza estatísticas
        policy_name = (
            strategy_name.split(" - ")[0]
            .replace(" ", "")
            .replace("Baixos", "Low")
            .replace("CONSERVADOR", "")
            .replace("MODERADO", "")
            .replace("AGRESSIVO", "")
        )

        if policy_stats := next(
            (
                stats_dict
                for key, stats_dict in self.strategy_stats.items()
                if policy_name in key or "Commercial" in key or "Martingale" in key
            ),
            None,
        ):
            if hit_1:
                policy_stats["total_hits"] += 1
            else:
                policy_stats["total_misses"] += 1

            # ✅ ATUALIZAR ESTATÍSTICAS DE LUCRO
            policy_stats["total_profit_loss"] += profit_loss

        return {
            "explosion_value": explosion_value,
            "recommendation_hit": hit_1,
            "target_1": target_1,
            "bet_1": bet_1,
            "strategy": strategy_name,
            "phase": "N/A",
            "profit_loss": profit_loss,  # ✅ ADICIONAR ESTE CAMPO!
        }


# Mantém compatibilidade com imports antigos
Martingale8LowPolicy = CommercialMartingalePolicy
