#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""STRATEGY ENGINE - Motor de estratégias Implementa ML"""

import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import notification_manager
from learning_engine import REQUIRED_HISTORY_FOR_PREDICTION, LearningEngine

# --- CONFIGURAÇÃO DO LOGGER (RESTAURAR ESTE BLOCO) ---
project_root = Path(__file__).parent.parent
log_path = project_root / "logs" / "strategy_engine.log"

# Garante que o diretório de logs exista
log_path.parent.mkdir(parents=True, exist_ok=True)

# Define o logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Nível mais baixo para capturar tudo

# Evita duplicidade de handlers se o módulo for recarregado
if not logger.handlers:
    # Handler para o arquivo (com encoding para R$)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Salva tudo (DEBUG) no arquivo

    # Handler para o console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Mostra apenas INFO no console

    # Formatação
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Adiciona os handlers ao logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
# --- FIM DO BLOCO DO LOGGER ---


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
        self.is_active = False  # Cada estratégia controla se está ativa!

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


class Martingale8LowPolicy(StrategyPolicy):
    """
    Estratégia 'Martingale 8 Baixos' completa.
    Esta classe agora detém seu próprio estado.
    """

    def __init__(
        self, banca_inicial: float, learning_engine: Optional[LearningEngine] = None
    ):
        super().__init__(banca_inicial, learning_engine)

        # O ESTADO FOI MOVIDO PARA CÁ
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        self.modo_continuo = False
        self.target_ativo = 1.84  # Definido aqui

        # Lógica do Trigger (8 baixos)
        self.lows_needed = 8
        self.threshold = 2.0

        # Lógica de Sizing (1/15)
        self.sizing_policy = Martingale15(banca_inicial)
        self.alerta_6_lows_enviado = False

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
        logger.info("ATIVANDO Martingale8LowPolicy")

    def check_trigger(self, history: deque) -> bool:
        """
        Verifica o gatilho de 8 baixos (Orquestrador).
        """
        if self.is_active:
            return False

        lows_count = self._count_consecutive_lows(history)

        # Logs de status
        logger.debug("--- [MARTINGALE] Verificando Gatilho ---")
        logger.debug(f"Histórico recente (últimos 10): {list(history)[-10:]}")
        logger.debug(
            f"Contagem de 'lows' consecutivos: {lows_count}/{self.lows_needed}"
        )

        # (Este bloco usa o 'notification_manager' e corrige o F401)
        try:
            if lows_count == 6 and not self.alerta_6_lows_enviado:
                msg = (
                    f"⚠️ ALERTA: 6 'lows' (< {self.threshold}x) consecutivos detectados."
                )
                notification_manager.send_telegram_alert(msg)
                self.alerta_6_lows_enviado = True
            elif lows_count < 6 and self.alerta_6_lows_enviado:
                # Reseta a flag se a sequência quebrar
                self.alerta_6_lows_enviado = False
        except Exception as e:
            logger.error(f"Falha ao enviar alerta de 6 lows: {e}")

        # Delega toda a lógica de decisão para a nova função
        return self._handle_trigger_condition(lows_count, history)

    def _handle_trigger_condition(self, lows_count: int, history: deque) -> bool:
        """
        Processa a lógica de decisão após a contagem de 'lows'.
        Esta função é chamada por check_trigger.
        Retorna True se a estratégia for ativada, False caso contrário.
        """
        # --- 1. CONDIÇÃO DE GATILHO ---
        if lows_count >= self.lows_needed:  # self.lows_needed é 8

            # --- 2. VERIFICAÇÃO DE SEGURANÇA ---
            logger.debug(
                "Gatilho (8 lows) ATINGIDO. Verificando condições de segurança..."
            )

            resultado_seguranca = self._check_safety_conditions(history)
            logger.debug(
                f"Resultado da verificação de segurança: {resultado_seguranca}"
            )

            if not resultado_seguranca:
                # O próprio método _check_safety_conditions já logou o aviso
                logger.warning(
                    "[MARTINGALE] DECISÃO: Veto de segurança INTERNO. Não apostar."
                )
                return False  # Aborta a ativação devido ao risco

            # --- 3. ATIVAÇÃO (Seguro para prosseguir) ---
            logger.info("Gatilho de 8 baixos validado. Stats de segurança OK.")
            logger.debug("[MARTINGALE] DECISÃO: Seguro para APOSTAR.")
            self._activate_strategy()
            return True

        # --- Gatilho Não Atingido ---
        logger.debug(
            "[MARTINGALE] DECISÃO: Gatilho (8 lows) NÃO ATINGIDO. Não apostar."
        )
        return False

    def _check_safety_conditions(self, history: deque) -> bool:
        """
        Verifica se as condições atuais do jogo são seguras para ativar,
        evitando a "Fase Arrecadatória".
        Retorna True se for seguro, False se for perigoso.
        """
        # --- VERIFICAÇÃO DE SEGURANÇA ---
        # Usamos as features que o Jupyter provou serem importantes.

        # Precisamos de pelo menos 20 de histórico (para rolling_std_20)
        if len(history) < 20:
            logger.warning(
                "Gatilho de 8 baixos detectado, mas histórico < 20. Abortando por segurança."
            )
            return False  # Não é seguro

        # Pega os últimos 20 multiplicadores
        recent_history = list(history)[-20:]

        # Calcula as features de perigo que descobrimos
        current_std_20 = np.std(recent_history)
        current_mean_20 = np.mean(recent_history)

        # --- Definição dos Limiares de Perigo ---
        # (Baseado na Célula 3: Super-Streak teve std=1.31, mean=1.93)
        # Vamos ser conservadores:
        DANGER_STD_THRESHOLD = 2.3  # Se a volatilidade for QUASE NENHUMA
        DANGER_MEAN_THRESHOLD = 2.5  # Se a média estiver MUITO BAIXA

        if (current_std_20 < DANGER_STD_THRESHOLD) or (
            current_mean_20 < DANGER_MEAN_THRESHOLD
        ):
            logger.warning(
                "[SEGURANÇA] Gatilho de 8 baixos IGNORADO. "
                "Risco de 'Fase Arrecadatória' detectado!"
            )
            logger.warning(
                f"[SEGURANÇA] Stats: Média(20)={current_mean_20:.2f} (Limite: {DANGER_MEAN_THRESHOLD:.2f}), "
                f"Std(20)={current_std_20:.2f} (Limite: {DANGER_STD_THRESHOLD:.2f})"
            )
            return False  # Perigoso! Não ative.

        # Se passou por todas as verificações, é seguro
        return True

    def get_bet_recommendation(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        if not self.is_active:
            return None

        bet_1 = self.sizing_policy.get_bet(self.dobra_atual, current_balance)
        target_1 = self.sizing_policy.get_target(self.dobra_atual)
        self.target_ativo = target_1  # Salva o target para o process_result

        return BetRecommendation(
            strategy_name=f"Martingale 8 Baixos - Dobra {self.dobra_atual}",
            bet_1=bet_1,
            target_1=target_1,
            bet_2=0,
            target_2=0,
            justification=f"Dobra {self.dobra_atual}-{self.lows_needed} >2.0x",
            confidence=1.0,
            ready=True,
        )

    def process_result(self, explosion_value: float):
        if not self.is_active:
            return

        # A LÓGICA DE '_process_martingale_result_automatic' VEM PARA CÁ
        target = self.target_ativo

        if explosion_value < target:
            logger.warning(f"Martingale8LowPolicy: PERDEU (< {target:.2f}x)")
            self.perdas_consecutivas += 1
            if self.dobra_atual >= 4:
                self._reset_cycle()  # Atingiu 4 dobras
            else:
                self.dobra_atual += 1

        elif target <= explosion_value <= 1.99:
            logger.info("Martingale8LowPolicy: GANHO (volta para dobra 2)")
            self.dobra_atual = 2
            self.perdas_consecutivas = 0
            self.modo_continuo = True

        else:  # Ganho >= 2.00
            logger.info("Martingale8LowPolicy: GANHO TOTAL (Ciclo concluído)")
            self._reset_cycle()

    def _reset_cycle(self):
        """Função helper interna para resetar."""
        self.is_active = False
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        self.modo_continuo = False
        self.target_ativo = 0.0


class StrategyEngine:
    def __init__(self, learning_engine: LearningEngine):
        self.explosion_history = deque(maxlen=260)
        self.learning_engine = learning_engine
        self.policies: Sequence[StrategyPolicy] = []

        # Estado do Motor.
        self.banca_inicial: Optional[float] = None
        self.suspenso_ate: Optional[float] = None
        self.meta_lucro_percentual = 1.4
        self.tempo_suspensao_horas = 4

        # Aposta preparada (agora é um atributo global do motor)
        self.aposta_preparada: Optional[BetRecommendation] = None

        # Estatísticas
        self.strategy_stats: Dict[str, Dict] = {}

        self.modo_ciclo: str = "reinvestir"
        self.banca_original_sessao: Optional[float] = None

    def iniciar_sessao(
        self,
        banca_inicial: float,
        meta_pct: float,
        tempo_suspensao: int,
        modo_ciclo: str,
    ):
        """
        Inicia a sessão com as configurações recebidas do bot_controller.
        """

        # 1. Define os valores recebidos
        self.banca_inicial = banca_inicial
        self.banca_original_sessao = banca_inicial
        self.meta_lucro_percentual = 1.0 if meta_pct == 100.0 else (meta_pct / 100.0)
        self.tempo_suspensao_horas = tempo_suspensao
        self.modo_ciclo = modo_ciclo

        # 2. Loga as configurações
        meta_valor_abs = self.banca_inicial * (1 + self.meta_lucro_percentual)
        logger.info(f"Sessão iniciada com banca: R$ {self.banca_inicial:.2f}")
        logger.info(
            f"Meta de lucro definida: {meta_pct:.0f}% (Atingir R$ {meta_valor_abs:.2f})"
        )
        logger.info(f"Suspensão após meta: {self.tempo_suspensao_horas} horas")
        logger.info(f"Modo de Ciclo definido: {self.modo_ciclo}")

        # 3. Inicia as políticas
        self.policies = [
            Martingale8LowPolicy(self.banca_inicial, self.learning_engine),
            MLHighConfidencePolicy(self.banca_inicial, self.learning_engine),
        ]

        # 4. Prepara o dict de estatísticas
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
        Reinicia a 'banca_inicial' com base no modo selecionado,
        para que o bot possa calcular uma nova meta e voltar a operar.
        """

        if self.modo_ciclo == "reinvestir":
            self.banca_inicial = saldo_atual
            logger.info(
                f"MODO REINVESTIR: Próximo ciclo iniciado com nova banca de R$ {saldo_atual:.2f}"
            )
        else:
            # Modo "preservar"
            self.banca_inicial = self.banca_original_sessao
            logger.info(
                f"MODO PRESERVAR: Próximo ciclo iniciado com banca original de R$ {self.banca_original_sessao:.2f}"
            )

        # Garantimos que, mesmo se self.banca_inicial for None (o que não
        # deve acontecer aqui), não passaremos 'None' para as políticas.
        if self.banca_inicial is None:
            logger.error(
                "Falha na definição da banca_inicial no reinício do ciclo. Usando 0.0 como fallback."
            )
            banca_para_politica = 0.0
        else:
            banca_para_politica = self.banca_inicial
        # --- FIM DA CORREÇÃO ---

        # CRÍTICO: Recria as políticas com a nova banca_inicial
        # (Agora usando a variável 'banca_para_politica' verificada)
        self.policies = [
            Martingale8LowPolicy(banca_para_politica, self.learning_engine),
            MLHighConfidencePolicy(banca_para_politica, self.learning_engine),
        ]
        logger.info("Políticas de estratégia foram reiniciadas com a nova banca.")

    def add_explosion_value(
        self, value: float
    ) -> Tuple[bool, Optional[BetRecommendation], Optional[str]]:
        """
        Método 'coração' refatorado.
        (SIMPLIFICADO: Sem o Veto TCS de volatilidade)
        """
        self.explosion_history.append(value)
        veto_message: Optional[str] = None

        # 1. Processar resultados das estratégias que JÁ ESTAVAM ativas
        for policy in self.policies:
            if policy.is_active:
                policy.process_result(value)

        # 2. Verificar gatilhos de estratégias INATIVAS
        strategy_activated = False
        if not self.esta_suspenso():

            for policy in self.policies:
                if not policy.is_active:

                    # Chama o check_trigger (código original)
                    # A Martingale8LowPolicy agora é checada toda vez.
                    triggered = policy.check_trigger(self.explosion_history)

                    if triggered:
                        strategy_activated = True

                    # --- LÓGICA DE MENSAGEM SIMPLIFICADA ---
                    elif isinstance(policy, MLHighConfidencePolicy):
                        prob = policy.last_calculated_prob
                        thresh = policy.confidence_threshold

                        # --- REMOVIDO: if tcs_veto_active: ... ---

                        if 0 < prob < thresh:
                            # Veto normal do ML (não precisamos mais dizer "Vol Segura")
                            veto_message = f"ML Veto: {prob:.1%} < {thresh:.0%}"
                        elif not strategy_activated:
                            # Nenhuma condição
                            veto_message = "Aguardando gatilhos..."

        return strategy_activated, None, veto_message

    def prepare_bets_for_balance(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:

        # Pergunta a TODAS as políticas por uma aposta
        for policy in self.policies:
            if policy.is_active:
                # Retorna a recomendação da PRIMEIRA política ativa
                if recommendation := policy.get_bet_recommendation(current_balance):
                    self.aposta_preparada = recommendation
                    # Atualiza estatísticas (simples)
                    if stats := self.strategy_stats.get(policy.__class__.__name__):
                        stats["total_recommendations"] += 1

                    return recommendation

        # Nenhuma política ativa quis apostar
        self.reset_prepared_bets()
        return None

    def check_suspension_ended(self, saldo_atual: float) -> bool:
        """
        Verifica se a suspensão terminou AGORA.
        Se sim, reinicia o ciclo com a nova banca antes de retornar.
        """
        if self.suspenso_ate is None:
            return False  # Não estava suspenso

        if time.time() >= self.suspenso_ate:
            self.suspenso_ate = None  # Reseta a suspensão

            # --- ADIÇÃO CRÍTICA ---
            # Chama o reset ANTES de liberar o bot para operar
            self._reiniciar_ciclo_pos_meta(saldo_atual)
            # --- FIM DA ADIÇÃO ---

            logger.info("Período de suspensão encerrado. Operações retomadas!")
            return True  # Retorna TRUE para o controller enviar o alerta

        return False  # Ainda está suspenso

    def esta_suspenso(self) -> bool:
        """Verifica se está no período de suspensão"""
        return False if self.suspenso_ate is None else (time.time() < self.suspenso_ate)

    def checar_meta_lucro(self, saldo_atual: float) -> bool:
        """Verifica se atingiu meta de lucro e suspende operações"""
        if not self.banca_inicial or saldo_atual is None:
            return False

        meta = self.banca_inicial * (1 + self.meta_lucro_percentual)
        if saldo_atual >= meta:
            if not self.esta_suspenso():
                self.suspenso_ate = time.time() + self.tempo_suspensao_horas * 3600
                logger.info(f"META - Horas Suspensão: {self.tempo_suspensao_horas}.")
            return True
        return False

    def reset_prepared_bets(self):
        """Reseta a aposta preparada no estado"""
        self.aposta_preparada = None

    def get_prepared_bets(self) -> Optional[BetRecommendation]:
        """Retorna apostas preparadas do estado"""
        return self.aposta_preparada

    def get_current_analysis(self) -> Dict:
        """Retorna análise atual do estado (para a UI)"""
        prepared = self.aposta_preparada is not None

        # Tenta obter o status da política Martingale
        martingale_policy = next(
            (p for p in self.policies if isinstance(p, Martingale8LowPolicy)), None
        )

        # --- MUDANÇA: Definir valores padrão primeiro ---
        martingale_active = False
        dobra_atual = 1
        status_msg = "Aguardando gatilhos"
        baixos_consecutivos_str = "0/8"  # Texto padrão
        # --- FIM DA MUDANÇA ---

        if martingale_policy:
            if martingale_policy.is_active:
                # --- MUDANÇA: Atualiza os valores se estiver ativo ---
                status_msg = f"Martingale Ativo (Dobra {martingale_policy.dobra_atual})"
                martingale_active = True
                dobra_atual = martingale_policy.dobra_atual

            # --- MUDANÇA: Calcula os baixos consecutivos (mesmo inativo) ---
            try:
                # Chama o método que conta os baixos
                current_lows = martingale_policy._count_consecutive_lows(
                    self.explosion_history
                )
                baixos_consecutivos_str = (
                    f"{current_lows}/{martingale_policy.lows_needed}"
                )
            except Exception:
                baixos_consecutivos_str = "Erro/8"
            # --- FIM DA MUDANÇA ---

        # --- MUDANÇA: Lógica para calcular a confiança do ML ---
        ml_confidence = 0.0  # Padrão é 0%
        try:
            # Verifica se o LE existe e se o histórico é suficiente (250)
            if (
                self.learning_engine
                and len(self.explosion_history) >= REQUIRED_HISTORY_FOR_PREDICTION
            ):
                recent_history = list(self.explosion_history)
                # Pede a previsão ao cérebro do ML
                probability = self.learning_engine.predict(recent_history)
                if probability is not None:
                    ml_confidence = probability
        except Exception as e:
            logger.error(f"Erro ao calcular confiança do ML: {e}")
            ml_confidence = -1.0  # -1.0 indicará um erro na UI
        # --- FIM DA MUDANÇA ---

        return {
            "history_size": len(self.explosion_history),
            "prepared_bets_ready": prepared,
            "status": status_msg,
            # --- MUDANÇA: Adiciona os novos dados para a UI ---
            "martingale_active": martingale_active,
            "dobra_atual": dobra_atual,
            "ml_confidence": ml_confidence,
            "baixos_consecutivos": baixos_consecutivos_str,
            # --- FIM DA MUDANÇA ---
        }

    def get_strategies_stats(self) -> List[Dict]:
        """Retorna estatísticas das estratégias"""
        stats_list = []
        for strategy_name, data in self.strategy_stats.items():
            # Cálculo do Hit Rate
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
        """Avalia resultado de aposta executada (Adaptado)"""
        target_1 = executed_bet.get("target_1", 0)
        hit_1 = explosion_value >= target_1 if target_1 > 0 else False
        strategy_name = executed_bet.get("strategy", "Desconhecida")

        # Atualiza estatísticas de Hit/Miss
        # Encontra o nome da classe da política
        policy_name = (
            strategy_name.split(" - ")[0].replace(" ", "").replace("Baixos", "Low")
        )

        # Tenta encontrar a estatística correta
        if policy_stats := next(
            (
                stats_dict
                for key, stats_dict in self.strategy_stats.items()
                if policy_name in key
            ),
            None,
        ):
            if hit_1:
                policy_stats["total_hits"] += 1
            else:
                policy_stats["total_misses"] += 1

        return {
            "explosion_value": explosion_value,
            "recommendation_hit": hit_1,
            "target_1": target_1,
            "bet_1": executed_bet.get("bet_1", 0),
            "strategy": strategy_name,
            "phase": "N/A",
        }


class MLHighConfidencePolicy(StrategyPolicy):
    """
    Uma estratégia que faz uma APOSTA ÚNICA quando o ML está
    com alta confiança.
    """

    def __init__(
        self, banca_inicial: float, learning_engine: Optional[LearningEngine] = None
    ):
        super().__init__(banca_inicial, learning_engine)
        self.confidence_threshold = 0.80  # Ex: 80% de confiança
        self.bet_size_percent = 0.01  # Ex: 1% da banca
        self.last_calculated_prob: float = 0.0

    def check_trigger(self, history: deque) -> bool:
        if self.is_active or not self.le:
            return False

        # Prepara o histórico para o modelo
        recent_history = list(history)[-REQUIRED_HISTORY_FOR_PREDICTION:]
        if len(recent_history) < REQUIRED_HISTORY_FOR_PREDICTION:
            self.last_calculated_prob = 0.0  # Não temos histórico suficiente
            return False

        # PERGUNTA AO ML
        probability = self.le.predict(recent_history)

        if probability is None:
            self.last_calculated_prob = 0.0
            return False

        # --- MUDANÇA: Salva a probabilidade ANTES de decidir ---
        self.last_calculated_prob = probability
        # --- FIM DA MUDANÇA ---

        if probability >= self.confidence_threshold:
            logger.info(
                f"ATIVANDO MLHighConfidencePolicy (" f"Confiança: {probability:.2%}"
            )
            self.is_active = True
            return True

        # Se chegamos aqui, foi um veto (prob < threshold). A prob está salva.
        return False

    def get_bet_recommendation(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        if not self.is_active:
            return None

        bet_1 = max(1.0, current_balance * self.bet_size_percent)

        return BetRecommendation(
            strategy_name="ML High Confidence",
            bet_1=bet_1,
            target_1=2.0,  # Alvo fixo de 2.0x
            bet_2=0,
            target_2=0,
            justification=(f"Confiança do modelo > {self.confidence_threshold:.0%}"),
            confidence=self.confidence_threshold,
            ready=True,
        )

    def process_result(self, explosion_value: float):
        # Esta estratégia é de aposta única.
        # Após processar o resultado, ela se desativa.
        if self.is_active:
            if explosion_value >= 2.0:
                logger.info("MLHighConfidencePolicy: HIT")
            else:
                logger.warning("MLHighConfidencePolicy: MISS")

            # Reseta para a próxima oportunidade
            self.is_active = False

    def evaluate_executed_bet(self, explosion_value: float, executed_bet: Dict) -> Dict:
        """Avalia resultado de aposta executada (Transplantado)"""
        # Nota: 'executed_bet' deve ser o dicionário da BetRecommendation
        target_1 = executed_bet.get("target_1", 0)
        hit_1 = explosion_value >= target_1 if target_1 > 0 else False

        return {
            "explosion_value": explosion_value,
            "recommendation_hit": hit_1,
            "target_1": target_1,
            "bet_1": executed_bet.get("bet_1", 0),
            "strategy": executed_bet.get("strategy", ""),
            "phase": "N/A",  # Este campo não parecia ser usado
        }


class SizingPolicy(ABC):
    @abstractmethod
    def __init__(self, banca_inicial: float):
        """
        Construtor abstrato para garantir que todas as políticas
        de dimensionamento aceitem a banca inicial.
        """
        # Nota: Não precisa ser "pass". Podemos até guardar.
        self.banca_inicial_base = banca_inicial

    @abstractmethod
    def get_bet(self, dobra_atual: int, banca_atual: float) -> float:
        """Calcula o valor da aposta."""
        pass

    @abstractmethod
    def get_target(self, dobra_atual: int) -> float:
        """Retorna o multiplicador alvo."""
        pass


class Martingale15(SizingPolicy):
    def __init__(self, banca_inicial: float):
        self.valores_fixos = self._definir_valores(banca_inicial)

    def _definir_valores(self, banca_inicial: float):
        multipliers = {1: 1, 2: 2, 3: 4, 4: 8}
        return {
            dobra: max(1.0, round((banca_inicial / 15) * mult, 2))
            for dobra, mult in multipliers.items()
        }

    def get_bet(self, dobra_atual: int, banca_atual: float) -> float:
        # A lógica de 'banca_atual' pode ser usada para preservar lucros, etc.
        return self.valores_fixos.get(dobra_atual, self.valores_fixos[1])

    def get_target(self, dobra_atual: int) -> float:
        # O alvo está "hard-coded" nesta política específica
        return 1.84
