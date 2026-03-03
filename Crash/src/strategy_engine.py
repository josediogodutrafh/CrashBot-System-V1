#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRATEGY ENGINE v9.0 - Motor de Estratégias com Configuração Flexível

Novidades v9.0:
- 4 estratégias de dobras: 1-2, 1-2-1-2, 1-2-4, 1-2-4-1-2-4
- Banca definida pelo usuário (não mais pelo perfil)
- Perfil de entrada controla APENAS o gatilho (5, 6 ou 7)
- Target randômico entre 1.90x e 1.99x
- Renovação automática: se ganhar com mult < 2.0x, volta para dobra 1
- ML como informativo de risco (sem veto)
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import stats

# Importações opcionais (podem não existir em todos os ambientes)
try:
    import notification_manager
except ImportError:
    notification_manager = None

try:
    from learning_engine import REQUIRED_HISTORY_FOR_PREDICTION, LearningEngine
except ImportError:
    REQUIRED_HISTORY_FOR_PREDICTION = 250
    LearningEngine = None

# --- CONFIGURAÇÃO DO LOGGER ---
project_root = Path(__file__).parent.parent
log_path = project_root / "logs" / "strategy_engine.log"

log_path.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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


# =============================================================================
# ENUMS E CONFIGURAÇÕES
# =============================================================================


class PerfilEntrada(Enum):
    """Perfil de entrada - controla APENAS o gatilho."""

    CONSERVADOR = 1
    MODERADO = 2
    AGRESSIVO = 3


class EstrategiaDobras(Enum):
    """Estratégias de dobras disponíveis."""

    DOBRAS_1_2 = "1-2"
    DOBRAS_1_2_1_2 = "1-2-1-2"
    DOBRAS_1_2_4 = "1-2-4"
    DOBRAS_1_2_4_1_2_4 = "1-2-4-1-2-4"


# Configuração dos perfis de entrada (apenas gatilho)
PERFIL_ENTRADA_CONFIG = {
    PerfilEntrada.CONSERVADOR: {
        "gatilho": 7,
        "descricao": "Entra após 7 baixas consecutivas",
        "caracteristica": "Menos entradas, mais seletivo",
        "emoji": "🟢",
    },
    PerfilEntrada.MODERADO: {
        "gatilho": 6,
        "descricao": "Entra após 6 baixas consecutivas (padrão)",
        "caracteristica": "Equilíbrio entre oportunidades e segurança",
        "emoji": "🟡",
    },
    PerfilEntrada.AGRESSIVO: {
        "gatilho": 5,
        "descricao": "Entra após 5 baixas consecutivas",
        "caracteristica": "Mais entradas, mais exposição ao risco",
        "emoji": "🔴",
    },
}


# Configuração das estratégias de dobras
ESTRATEGIA_DOBRAS_CONFIG = {
    EstrategiaDobras.DOBRAS_1_2: {
        "nome": "1-2 (2 dobras)",
        "dobras": [1, 2],
        "total_partes": 3,
        "risco": "ALTO",
        "lucro_esperado": "MÁXIMO",
        "descricao": "Maior lucro por entrada, quebra com 8+ baixas (gatilho 6)",
        "cor": "#9b59b6",
        "emoji": "🟣",
    },
    EstrategiaDobras.DOBRAS_1_2_1_2: {
        "nome": "1-2-1-2 (4 dobras)",
        "dobras": [1, 2, 1, 2],
        "total_partes": 6,
        "risco": "MÉDIO-ALTO",
        "lucro_esperado": "ALTO",
        "descricao": "Dois ciclos de 1-2, equilibra lucro e proteção",
        "cor": "#3498db",
        "emoji": "🔵",
    },
    EstrategiaDobras.DOBRAS_1_2_4: {
        "nome": "1-2-4 (3 dobras)",
        "dobras": [1, 2, 4],
        "total_partes": 7,
        "risco": "MÉDIO",
        "lucro_esperado": "ALTO",
        "descricao": "Martingale clássico, bom equilíbrio",
        "cor": "#2ecc71",
        "emoji": "🟢",
    },
    EstrategiaDobras.DOBRAS_1_2_4_1_2_4: {
        "nome": "1-2-4-1-2-4 (6 dobras)",
        "dobras": [1, 2, 4, 1, 2, 4],
        "total_partes": 14,
        "risco": "BAIXO",
        "lucro_esperado": "MODERADO",
        "descricao": "Mais seguro, 99.5% de taxa de vitória",
        "cor": "#e74c3c",
        "emoji": "🔴",
    },
}


# Configuração dos indicadores ML (informativo)
INDICADORES_ML_CONFIG = {
    "j20_seq_count": {
        "nome": "Fragmentação Curto Prazo",
        "threshold": 5,
        "alerta_se": ">=",
        "descricao": "Muitas sequências curtas nas últimas 20 rodadas",
    },
    "j20_seq_4plus": {
        "nome": "Sequências Longas Recentes",
        "threshold": 0,
        "alerta_se": "==",
        "descricao": "Nenhuma sequência 4+ nas últimas 20 rodadas",
    },
    "j20_seq_media": {
        "nome": "Média de Sequências",
        "threshold": 2.0,
        "alerta_se": "<",
        "descricao": "Sequências muito curtas em média",
    },
    "j250_seq_5plus": {
        "nome": "Sequências Longas (250)",
        "threshold": 4,
        "alerta_se": "<=",
        "descricao": "Poucas sequências longas na janela",
    },
    "j250_pct_altas_5x": {
        "nome": "Altas Recentes (5x+)",
        "threshold": 26,
        "alerta_se": ">",
        "descricao": "Muitas altas boas (respiro do jogo)",
    },
    "j250_pct_altas_10x": {
        "nome": "Altas Grandes (10x+)",
        "threshold": 5.5,
        "alerta_se": ">",
        "descricao": "Muitas altas grandes recentes",
    },
    "j250_slope": {
        "nome": "Tendência",
        "threshold": -0.005,
        "alerta_se": "<",
        "descricao": "Tendência de queda nos multiplicadores",
    },
    "j250_delta_media": {
        "nome": "Delta Média",
        "threshold": -1.0,
        "alerta_se": "<",
        "descricao": "Fim da janela pior que o início",
    },
}


# Tempo de suspensão fixo (4 horas em segundos)
TEMPO_SUSPENSAO_FIXO = 4 * 3600


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class BetRecommendation:
    """Estrutura para recomendações de apostas."""

    strategy_name: str
    bet_1: float
    target_1: float
    bet_2: float
    target_2: float
    justification: str
    confidence: float
    ready: bool = False


@dataclass
class RiskAnalysisResult:
    """Resultado da análise de risco ML (informativo)."""

    score: float  # 0-100
    alertas_ativos: int
    total_alertas: int
    detalhes: Dict[str, Dict]  # indicador -> {valor, threshold, alerta}

    @property
    def nivel_risco(self) -> str:
        """Retorna o nível de risco como texto."""
        if self.score >= 75:
            return "ALTO"
        elif self.score >= 50:
            return "MÉDIO"
        elif self.score >= 25:
            return "BAIXO"
        return "MÍNIMO"

    @property
    def emoji(self) -> str:
        """Retorna emoji baseado no nível de risco."""
        if self.score >= 75:
            return "🔴"
        elif self.score >= 50:
            return "🟡"
        elif self.score >= 25:
            return "🟢"
        return "⚪"


# =============================================================================
# ANALISADOR DE RISCO ML (INFORMATIVO)
# =============================================================================


class RiskAnalyzer:
    """
    Analisador de risco baseado em ML.
    INFORMATIVO APENAS - não veta entradas.
    """

    def __init__(self):
        self.ultimo_resultado: Optional[RiskAnalysisResult] = None

    def _contar_sequencias(
        self, valores: List[float], limite: float = 2.0
    ) -> List[int]:
        """Conta sequências de baixas e retorna lista de tamanhos."""
        seqs = []
        seq_atual = 0

        for v in valores:
            if v < limite:
                seq_atual += 1
            else:
                if seq_atual > 0:
                    seqs.append(seq_atual)
                seq_atual = 0

        if seq_atual > 0:
            seqs.append(seq_atual)

        return seqs

    def _calcular_indicador(self, nome: str, valor: float) -> Tuple[bool, Dict]:
        """Verifica se um indicador está em alerta."""
        config = INDICADORES_ML_CONFIG.get(nome)
        if not config:
            return False, {}

        threshold = config["threshold"]
        operador = config["alerta_se"]

        alerta = False
        if operador == ">=":
            alerta = valor >= threshold
        elif operador == "<=":
            alerta = valor <= threshold
        elif operador == "<":
            alerta = valor < threshold
        elif operador == ">":
            alerta = valor > threshold
        elif operador == "==":
            alerta = valor == threshold

        return alerta, {
            "valor": valor,
            "threshold": threshold,
            "alerta": alerta,
            "nome": config["nome"],
            "descricao": config["descricao"],
        }

    def analisar(self, history: deque) -> RiskAnalysisResult:
        """
        Analisa o histórico e retorna score de risco.
        Baseado nos 8 indicadores descobertos na análise.
        """
        detalhes = {}
        alertas_ativos = 0

        history_list = list(history)

        # --- JANELA DE 20 RODADAS ---
        if len(history_list) >= 20:
            j20 = history_list[-20:]
            seqs_20 = self._contar_sequencias(j20)

            # Indicador 1: Quantidade de sequências (fragmentação)
            j20_seq_count = len(seqs_20)
            alerta, info = self._calcular_indicador("j20_seq_count", j20_seq_count)
            detalhes["j20_seq_count"] = info
            if alerta:
                alertas_ativos += 1

            # Indicador 2: Sequências 4+
            j20_seq_4plus = sum(1 for s in seqs_20 if s >= 4)
            alerta, info = self._calcular_indicador("j20_seq_4plus", j20_seq_4plus)
            detalhes["j20_seq_4plus"] = info
            if alerta:
                alertas_ativos += 1

            # Indicador 3: Média das sequências
            j20_seq_media = np.mean(seqs_20) if seqs_20 else 0
            alerta, info = self._calcular_indicador("j20_seq_media", j20_seq_media)
            detalhes["j20_seq_media"] = info
            if alerta:
                alertas_ativos += 1

        # --- JANELA DE 250 RODADAS ---
        if len(history_list) >= 250:
            j250 = history_list[-250:]
            seqs_250 = self._contar_sequencias(j250)

            # Indicador 4: Sequências 5+
            j250_seq_5plus = sum(1 for s in seqs_250 if s >= 5)
            alerta, info = self._calcular_indicador("j250_seq_5plus", j250_seq_5plus)
            detalhes["j250_seq_5plus"] = info
            if alerta:
                alertas_ativos += 1

            # Indicador 5: % de altas >= 5x
            j250_pct_altas_5x = np.sum(np.array(j250) >= 5.0) / len(j250) * 100
            alerta, info = self._calcular_indicador(
                "j250_pct_altas_5x", j250_pct_altas_5x
            )
            detalhes["j250_pct_altas_5x"] = info
            if alerta:
                alertas_ativos += 1

            # Indicador 6: % de altas >= 10x
            j250_pct_altas_10x = np.sum(np.array(j250) >= 10.0) / len(j250) * 100
            alerta, info = self._calcular_indicador(
                "j250_pct_altas_10x", j250_pct_altas_10x
            )
            detalhes["j250_pct_altas_10x"] = info
            if alerta:
                alertas_ativos += 1

            # Indicador 7: Tendência (slope)
            x = np.arange(len(j250))
            slope, _, _, _, _ = stats.linregress(x, j250)
            alerta, info = self._calcular_indicador("j250_slope", slope)
            detalhes["j250_slope"] = info
            if alerta:
                alertas_ativos += 1

            # Indicador 8: Delta média (fim vs início)
            primeira_metade = j250[:125]
            segunda_metade = j250[125:]
            delta_media = np.mean(segunda_metade) - np.mean(primeira_metade)
            alerta, info = self._calcular_indicador("j250_delta_media", delta_media)
            detalhes["j250_delta_media"] = info
            if alerta:
                alertas_ativos += 1

        # Calcular score
        total_alertas = 8
        score = (alertas_ativos / total_alertas) * 100 if total_alertas > 0 else 0

        resultado = RiskAnalysisResult(
            score=score,
            alertas_ativos=alertas_ativos,
            total_alertas=total_alertas,
            detalhes=detalhes,
        )

        self.ultimo_resultado = resultado
        return resultado


# =============================================================================
# POLÍTICA DE SIZING FLEXÍVEL
# =============================================================================


class FlexibleSizingPolicy:
    """Política de sizing flexível para qualquer estratégia de dobras."""

    def __init__(self, banca: float, estrategia: EstrategiaDobras):
        self.banca = banca
        self.estrategia = estrategia
        self.config = ESTRATEGIA_DOBRAS_CONFIG[estrategia]
        self.valores_dobras = self._calcular_valores()

    def _calcular_valores(self) -> Dict[int, float]:
        """Calcula o valor de cada dobra baseado na banca e estratégia."""
        dobras = self.config["dobras"]
        total_partes = self.config["total_partes"]
        parte = self.banca / total_partes

        valores = {}
        for i, proporcao in enumerate(dobras, 1):
            valores[i] = max(1.0, round(parte * proporcao, 2))

        return valores

    def get_bet(self, dobra_atual: int) -> float:
        """Retorna o valor da aposta para a dobra atual."""
        return self.valores_dobras.get(dobra_atual, self.valores_dobras.get(1, 1.0))

    def get_total_dobras(self) -> int:
        """Retorna o número total de dobras."""
        return len(self.config["dobras"])

    def get_info(self) -> Dict:
        """Retorna informações sobre a configuração."""
        return {
            "estrategia": self.estrategia.value,
            "nome": self.config["nome"],
            "dobras": self.config["dobras"],
            "valores": self.valores_dobras,
            "banca": self.banca,
            "risco": self.config["risco"],
        }


# =============================================================================
# POLÍTICA BASE DE ESTRATÉGIA
# =============================================================================


class StrategyPolicy(ABC):
    """Interface base para estratégias."""

    def __init__(self, banca: float, learning_engine=None):
        self.banca = banca
        self.le = learning_engine
        self.is_active = False

    @abstractmethod
    def check_trigger(self, history: deque) -> Tuple[bool, str]:
        """Verifica se a estratégia deve ser ativada."""
        pass

    @abstractmethod
    def get_bet_recommendation(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        """Retorna recomendação de aposta se ativa."""
        pass

    @abstractmethod
    def process_result(self, explosion_value: float):
        """Processa o resultado da rodada."""
        pass


# =============================================================================
# POLÍTICA MARTINGALE FLEXÍVEL v9.0
# =============================================================================


class FlexibleMartingalePolicy(StrategyPolicy):
    """
    Estratégia Martingale Flexível v9.0.

    Suporta:
    - 4 estratégias de dobras (1-2, 1-2-1-2, 1-2-4, 1-2-4-1-2-4)
    - Banca definida pelo usuário
    - Gatilho baseado no perfil de entrada
    - Target randômico entre 1.90x e 1.99x
    - Renovação: se ganhar com mult < 2.0x, volta para dobra 1
    - ML informativo (sem veto)
    """

    def __init__(
        self,
        banca: float,
        estrategia: EstrategiaDobras,
        perfil: PerfilEntrada,
        learning_engine=None,
        risk_analyzer: Optional[RiskAnalyzer] = None,
    ):
        super().__init__(banca, learning_engine)

        # Configurações
        self.estrategia = estrategia
        self.perfil = perfil
        self.estrategia_config = ESTRATEGIA_DOBRAS_CONFIG[estrategia]
        self.perfil_config = PERFIL_ENTRADA_CONFIG[perfil]

        # Gatilho fixo baseado no perfil
        self.gatilho = self.perfil_config["gatilho"]
        self.threshold = 2.0

        # Política de sizing
        self.sizing_policy = FlexibleSizingPolicy(banca, estrategia)
        self.total_dobras = self.sizing_policy.get_total_dobras()

        # Calcula quando quebra: gatilho + número de dobras
        self.quebra_se = self.gatilho + self.total_dobras

        # Estado do Martingale
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        self.target_ativo = 0.0

        # Flag anti-retrigger: após quebra, exige reset das baixas consecutivas
        self._aguardando_reset = False

        # Analisador de risco ML (informativo)
        self.risk_analyzer = risk_analyzer or RiskAnalyzer()
        self.ultimo_risco: Optional[RiskAnalysisResult] = None

        # Alerta de gatilho-1 enviado
        self.alerta_pre_gatilho_enviado = False

        # UI
        self.ultima_decisao: str = "⏳ Aguardando primeira rodada..."
        self.ultima_decisao_tipo: str = "aguardando"

        logger.info(
            f"FlexibleMartingalePolicy iniciada - "
            f"Estratégia: {estrategia.value}, "
            f"Perfil: {perfil.name}, "
            f"Gatilho: {self.gatilho}, "
            f"Banca: R${banca:.2f}, "
            f"Quebra se: {self.quebra_se}+ baixas"
        )

    def _set_decision(
        self, mensagem: str, tipo: str, resultado: bool
    ) -> Tuple[bool, str]:
        """Define a decisão atual."""
        self.ultima_decisao = mensagem
        self.ultima_decisao_tipo = tipo
        return resultado, mensagem

    def _sortear_target(self) -> float:
        """Sorteia target entre 1.90x e 1.99x."""
        target = round(random.uniform(1.90, 1.99), 2)
        logger.debug(f"Target sorteado: {target}x")
        return target

    def _count_consecutive_lows(self, history: deque) -> int:
        """Conta baixas consecutivas no final do histórico."""
        count = 0
        for value in reversed(history):
            if value < self.threshold:
                count += 1
            else:
                break
        return count

    def _activate_strategy(self):
        """Ativa a estratégia."""
        self.is_active = True
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        logger.info(
            f"ATIVANDO FlexibleMartingalePolicy - "
            f"Estratégia {self.estrategia.value}, Perfil {self.perfil.name}"
        )

    def check_trigger(self, history: deque) -> Tuple[bool, str]:
        """Verifica gatilho e retorna decisão."""
        if self.is_active:
            return False, self.ultima_decisao

        lows_count = self._count_consecutive_lows(history)

        # Anti-retrigger: após quebra, espera baixas zerarem
        if self._aguardando_reset:
            if lows_count == 0:
                self._aguardando_reset = False
                logger.info("Reset detectado - pronto para novo ciclo")
            else:
                return self._set_decision(
                    f"⏸️ PAUSA PÓS-QUEBRA: {lows_count} baixas"
                    " (aguardando reset)",
                    "aguardando",
                    False,
                )

        # Log de debug
        logger.debug(
            f"[MARTINGALE FLEX] Verificando: "
            f"{lows_count}/{self.gatilho} baixas"
        )

        # Alerta de pré-gatilho (1 antes)
        try:
            if lows_count == self.gatilho - 1 and not self.alerta_pre_gatilho_enviado:
                if notification_manager:
                    msg = (
                        f"⚠️ ALERTA: {lows_count} baixas consecutivas. "
                        f"Gatilho em {self.gatilho}. "
                        f"Estratégia: {self.estrategia.value}"
                    )
                    notification_manager.send_telegram_alert(msg)
                self.alerta_pre_gatilho_enviado = True
            elif lows_count < self.gatilho - 1:
                self.alerta_pre_gatilho_enviado = False
        except Exception as e:
            logger.error(f"Falha ao enviar alerta pré-gatilho: {e}")

        # Verifica se atingiu gatilho
        if lows_count >= self.gatilho:
            # Calcula análise de risco ML (INFORMATIVO)
            self.ultimo_risco = self.risk_analyzer.analisar(history)

            logger.info(
                f"Gatilho {self.gatilho} atingido! "
                f"Score de risco ML: {self.ultimo_risco.score:.0f}% "
                f"(INFORMATIVO - não veta)"
            )

            self._activate_strategy()

            risco_info = f" | Risco ML: {self.ultimo_risco.score:.0f}%"
            return self._set_decision(
                f"✅ APOSTANDO: {lows_count}/{self.gatilho} baixas{risco_info}",
                "apostando",
                True,
            )

        faltam = self.gatilho - lows_count
        return self._set_decision(
            f"⏸️ AGUARDANDO: {lows_count}/{self.gatilho} baixas (faltam {faltam})",
            "aguardando",
            False,
        )

    def get_bet_recommendation(
        self, current_balance: float
    ) -> Optional[BetRecommendation]:
        """Retorna recomendação de aposta."""
        if not self.is_active:
            return None

        bet = self.sizing_policy.get_bet(self.dobra_atual)
        target = self._sortear_target()
        self.target_ativo = target

        # Info de risco para exibição
        risco_str = ""
        if self.ultimo_risco:
            risco_str = (
                f" | Risco: {self.ultimo_risco.emoji} {self.ultimo_risco.score:.0f}%"
            )

        self.ultima_decisao = (
            f"✅ APOSTANDO: Dobra {self.dobra_atual}/{self.total_dobras} - "
            f"R${bet:.2f} @ {target}x{risco_str}"
        )
        self.ultima_decisao_tipo = "apostando"

        return BetRecommendation(
            strategy_name=f"Martingale {self.estrategia.value} - Dobra {self.dobra_atual}",
            bet_1=bet,
            target_1=target,
            bet_2=0,
            target_2=0,
            justification=(
                f"Dobra {self.dobra_atual}/{self.total_dobras} - "
                f"Target {target}x - {self.perfil.name}"
            ),
            confidence=1.0,
            ready=True,
        )

    def process_result(self, explosion_value: float):
        """
        Processa resultado da rodada.

        Lógica de renovação:
        - Se perdeu (< target): avança para próxima dobra
        - Se ganhou (>= target) e multiplicador >= 2.0x: ciclo completo, reseta
        - Se ganhou (>= target) e multiplicador < 2.0x: RENOVA (volta para dobra 1)
        """
        if not self.is_active:
            return

        target = self.target_ativo

        if explosion_value < target:
            # PERDEU
            logger.warning(
                f"FlexibleMartingalePolicy: PERDEU "
                f"({explosion_value:.2f}x < {target}x)"
            )
            self.perdas_consecutivas += 1

            if self.dobra_atual >= self.total_dobras:
                # Atingiu máximo de dobras = QUEBRA
                logger.error(
                    f"QUEBRA! {self.total_dobras} dobras esgotadas. "
                    f"Estratégia: {self.estrategia.value}"
                )
                self._reset_cycle(quebra=True)
            else:
                # Avança para próxima dobra
                self.dobra_atual += 1
                logger.info(f"Avançando para dobra {self.dobra_atual}")

        elif target <= explosion_value < 2.0:
            # GANHOU mas multiplicador < 2.0x = RENOVAÇÃO
            logger.info(
                f"FlexibleMartingalePolicy: GANHO com renovação "
                f"({explosion_value:.2f}x >= {target}x mas < 2.0x)"
            )
            logger.info("RENOVANDO: Voltando para dobra 1 (multiplicador < 2.0x)")
            self.dobra_atual = 1
            self.perdas_consecutivas = 0
            # NÃO desativa - continua ativo para próxima rodada

        else:
            # GANHOU com multiplicador >= 2.0x = CICLO COMPLETO
            logger.info(
                f"FlexibleMartingalePolicy: GANHO TOTAL "
                f"({explosion_value:.2f}x >= 2.0x)"
            )
            self._reset_cycle()

    def _reset_cycle(self, quebra: bool = False):
        """Reseta o ciclo completamente."""
        self.is_active = False
        self.dobra_atual = 1
        self.perdas_consecutivas = 0
        self.target_ativo = 0.0
        self.ultimo_risco = None
        if quebra:
            self._aguardando_reset = True
            self.ultima_decisao = (
                "⛔ QUEBRA! Aguardando reset para novo ciclo..."
            )
            logger.warning("Ciclo quebrou - aguardando reset")
        else:
            self.ultima_decisao = (
                "⏳ Ciclo resetado. Aguardando novo gatilho..."
            )
            logger.info("Ciclo resetado")
        self.ultima_decisao_tipo = "aguardando"

    def get_risk_analysis(self) -> Optional[RiskAnalysisResult]:
        """Retorna última análise de risco."""
        return self.ultimo_risco

    def get_status(self) -> Dict:
        """Retorna status atual da estratégia."""
        return {
            "estrategia": self.estrategia.value,
            "perfil": self.perfil.name,
            "gatilho": self.gatilho,
            "dobra_atual": self.dobra_atual,
            "total_dobras": self.total_dobras,
            "quebra_se": self.quebra_se,
            "is_active": self.is_active,
            "banca": self.banca,
            "valores_dobras": self.sizing_policy.valores_dobras,
            "risco_ml": self.ultimo_risco.score if self.ultimo_risco else None,
        }


# =============================================================================
# ENGINE PRINCIPAL v9.0
# =============================================================================


class StrategyEngine:
    """
    Motor de Estratégias v9.0.

    Gerencia a execução das estratégias com configuração flexível.
    """

    def __init__(self, learning_engine=None):
        self.explosion_history = deque(maxlen=260)
        self.learning_engine = learning_engine
        self.policies: List[StrategyPolicy] = []

        # Configurações da sessão
        self.banca: Optional[float] = None
        self.estrategia: Optional[EstrategiaDobras] = None
        self.perfil: Optional[PerfilEntrada] = None

        # Compatibilidade: banca_inicial é alias para banca
        self.banca_inicial: Optional[float] = None

        # Analisador de risco
        self.risk_analyzer = RiskAnalyzer()

        # Estado
        self.suspenso_ate: Optional[float] = None
        self.meta_lucro_percentual: float = 0.40  # 40% padrão
        self.tempo_suspensao_horas = 4

        # Aposta preparada
        self.aposta_preparada: Optional[BetRecommendation] = None

        # UI
        self.ultima_decisao: str = "⏳ Aguardando inicialização..."
        self.ultima_decisao_tipo: str = "aguardando"

        # Estatísticas
        self.strategy_stats: Dict[str, Dict] = {}

    def iniciar_sessao(
        self,
        banca: float,
        estrategia: EstrategiaDobras,
        perfil: PerfilEntrada,
        meta_lucro_percentual: float = 0.40,
    ):
        """
        Inicia a sessão com as configurações escolhidas pelo usuário.

        Args:
            banca: Valor da banca definido pelo usuário
            estrategia: Estratégia de dobras escolhida
            perfil: Perfil de entrada (controla gatilho)
            meta_lucro_percentual: Meta de lucro (padrão 40%)
        """
        self.banca = banca
        self.banca_inicial = banca  # Alias para compatibilidade
        self.estrategia = estrategia
        self.perfil = perfil
        self.meta_lucro_percentual = meta_lucro_percentual

        # Configurações
        estrategia_config = ESTRATEGIA_DOBRAS_CONFIG[estrategia]
        perfil_config = PERFIL_ENTRADA_CONFIG[perfil]

        # Log de início
        logger.info("=" * 60)
        logger.info("SESSÃO INICIADA - CrashBot v9.0")
        logger.info("=" * 60)
        logger.info(f"Banca: R$ {banca:.2f}")
        logger.info(f"Estratégia: {estrategia_config['nome']}")
        logger.info(
            f"Perfil: {perfil.name} (Gatilho: {perfil_config['gatilho']} baixas)"
        )
        logger.info(f"Risco: {estrategia_config['risco']}")
        logger.info(f"Meta de Lucro: {meta_lucro_percentual:.0%}")
        logger.info("=" * 60)

        # Cria as políticas
        self.policies = [
            FlexibleMartingalePolicy(
                banca=banca,
                estrategia=estrategia,
                perfil=perfil,
                learning_engine=self.learning_engine,
                risk_analyzer=self.risk_analyzer,
            )
        ]

        # Inicializa estatísticas
        for policy in self.policies:
            policy_name = policy.__class__.__name__
            self.strategy_stats[policy_name] = {
                "total_recommendations": 0,
                "total_hits": 0,
                "total_misses": 0,
                "total_profit_loss": 0.0,
                "hit_rate": 0.0,
            }

        self.ultima_decisao = (
            f"⏳ Sessão iniciada - {estrategia_config['nome']} | "
            f"Perfil {perfil.name}"
        )
        self.ultima_decisao_tipo = "aguardando"

    def add_explosion_value(
        self, value: float
    ) -> Tuple[bool, Optional[BetRecommendation], Optional[str]]:
        """Processa cada explosão."""
        self.explosion_history.append(value)
        veto_message: Optional[str] = None

        # 1. Processar resultados das estratégias ativas
        for policy in self.policies:
            if policy.is_active:
                policy.process_result(value)

        # 2. Verificar gatilhos
        strategy_activated = False
        if not self.esta_suspenso():
            for policy in self.policies:
                if not policy.is_active:
                    triggered, decisao_msg = policy.check_trigger(
                        self.explosion_history
                    )

                    if triggered:
                        strategy_activated = True
                        self.ultima_decisao = decisao_msg
                        self.ultima_decisao_tipo = "apostando"
                    else:
                        if isinstance(policy, FlexibleMartingalePolicy):
                            self.ultima_decisao = policy.ultima_decisao
                            self.ultima_decisao_tipo = policy.ultima_decisao_tipo

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

                    if isinstance(policy, FlexibleMartingalePolicy):
                        self.ultima_decisao = policy.ultima_decisao
                        self.ultima_decisao_tipo = policy.ultima_decisao_tipo

                    return recommendation

        self.reset_prepared_bets()
        return None

    def trocar_modo(self, novo_perfil: PerfilEntrada, saldo_atual: float):
        """Troca o perfil de entrada durante a execução."""
        if not self.estrategia:
            return
        logger.info(
            f"TROCA DE MODO: {self.perfil} -> {novo_perfil}"
        )
        self.strategy_stats = {}
        self.suspenso_ate = None
        self.iniciar_sessao(
            banca=saldo_atual,
            estrategia=self.estrategia,
            perfil=novo_perfil,
        )

    def esta_suspenso(self) -> bool:
        """Verifica se está suspenso."""
        return self.suspenso_ate is not None and time.time() < self.suspenso_ate

    def get_tempo_restante_suspensao(self) -> int:
        """Retorna tempo restante de suspensão."""
        if self.suspenso_ate is None:
            return 0
        restante = self.suspenso_ate - time.time()
        return max(0, int(restante))

    def check_suspension_ended(self, current_balance: float) -> bool:
        """Verifica se a suspensão terminou. Retorna True se acabou agora."""
        if self.suspenso_ate is not None and time.time() >= self.suspenso_ate:
            self.suspenso_ate = None
            logger.info(
                f"Suspensão encerrada. Saldo: R${current_balance:.2f}"
            )
            self.ultima_decisao = "✅ Suspensão encerrada - operações retomadas"
            self.ultima_decisao_tipo = "aguardando"
            return True
        return False

    def checar_meta_lucro(self, saldo_atual: float) -> bool:
        """Verifica se atingiu meta de lucro."""
        if not self.banca or saldo_atual is None:
            return False

        meta = self.banca * (1 + self.meta_lucro_percentual)
        if saldo_atual >= meta:
            if not self.esta_suspenso():
                self.suspenso_ate = time.time() + TEMPO_SUSPENSAO_FIXO
                logger.info(
                    f"META ATINGIDA! Saldo: R${saldo_atual:.2f} >= "
                    f"Meta: R${meta:.2f}. Suspensão de 4 horas."
                )
                self.ultima_decisao = "🏆 META ATINGIDA! Suspensão de 4 horas"
                self.ultima_decisao_tipo = "aguardando"
            return True
        return False

    def reset_prepared_bets(self):
        """Reseta aposta preparada."""
        self.aposta_preparada = None

    def get_prepared_bets(self) -> Optional[BetRecommendation]:
        """Retorna apostas preparadas."""
        return self.aposta_preparada

    def get_ultima_decisao(self) -> Tuple[str, str]:
        """Retorna última decisão para UI."""
        return self.ultima_decisao, self.ultima_decisao_tipo

    def get_risk_analysis(self) -> Optional[RiskAnalysisResult]:
        """Retorna última análise de risco ML."""
        for policy in self.policies:
            if isinstance(policy, FlexibleMartingalePolicy):
                return policy.get_risk_analysis()
        return self.risk_analyzer.ultimo_resultado

    def get_current_analysis(self) -> Dict:
        """Retorna análise atual para UI."""
        martingale_policy = next(
            (p for p in self.policies if isinstance(p, FlexibleMartingalePolicy)), None
        )

        martingale_active = False
        dobra_atual = 1
        total_dobras = 6
        status_msg = "Aguardando gatilhos"
        baixos_consecutivos_str = "0/6"
        risco_ml = None

        if martingale_policy:
            status = martingale_policy.get_status()
            martingale_active = status["is_active"]
            dobra_atual = status["dobra_atual"]
            total_dobras = status["total_dobras"]
            risco_ml = status.get("risco_ml")

            if martingale_active:
                status_msg = f"Martingale Ativo (Dobra {dobra_atual}/{total_dobras})"

            try:
                current_lows = martingale_policy._count_consecutive_lows(
                    self.explosion_history
                )
                baixos_consecutivos_str = f"{current_lows}/{martingale_policy.gatilho}"
            except Exception:
                baixos_consecutivos_str = "Erro"

        # Converter score ML para float de confiança (compatibilidade)
        ml_confidence = 0.0
        if risco_ml is not None:
            ml_confidence = max(0.0, 1.0 - (risco_ml / 100.0))

        perfil_name = self.perfil.name if self.perfil else "N/A"

        return {
            "history_size": len(self.explosion_history),
            "prepared_bets_ready": self.aposta_preparada is not None,
            "status": status_msg,
            "martingale_active": martingale_active,
            "dobra_atual": dobra_atual,
            "total_dobras": total_dobras,
            "baixos_consecutivos": baixos_consecutivos_str,
            "estrategia": self.estrategia.value if self.estrategia else "N/A",
            "perfil": perfil_name,
            "risk_mode": perfil_name,  # Alias para compatibilidade
            "suspenso": self.esta_suspenso(),
            "tempo_restante_suspensao": self.get_tempo_restante_suspensao(),
            "ultima_decisao": self.ultima_decisao,
            "ultima_decisao_tipo": self.ultima_decisao_tipo,
            "risco_ml": risco_ml,
            "ml_confidence": ml_confidence,  # Alias para compatibilidade
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
                    "profit_loss": data.get("total_profit_loss", 0),
                }
            )
        return stats_list

    def evaluate_executed_bet(self, explosion_value: float, executed_bet: Dict) -> Dict:
        """Avalia resultado de aposta executada."""
        target_1 = executed_bet.get("target_1", 0)
        bet_1 = executed_bet.get("bet_1", 0)
        hit_1 = explosion_value >= target_1 if target_1 > 0 else False
        strategy_name = executed_bet.get("strategy", "Desconhecida")

        profit_loss = (bet_1 * target_1) - bet_1 if hit_1 else -bet_1

        # Atualiza estatísticas
        for key, stats_dict in self.strategy_stats.items():
            if "Martingale" in key or "Flexible" in key:
                if hit_1:
                    stats_dict["total_hits"] += 1
                else:
                    stats_dict["total_misses"] += 1
                stats_dict["total_profit_loss"] += profit_loss
                break

        return {
            "explosion_value": explosion_value,
            "recommendation_hit": hit_1,
            "target_1": target_1,
            "bet_1": bet_1,
            "strategy": strategy_name,
            "profit_loss": profit_loss,
        }


# =============================================================================
# COMPATIBILIDADE COM VERSÕES ANTERIORES
# =============================================================================

# Alias para manter compatibilidade
RiskMode = PerfilEntrada
CommercialMartingalePolicy = FlexibleMartingalePolicy

# Configuração antiga para compatibilidade
RISK_MODE_CONFIG = {
    PerfilEntrada.CONSERVADOR: {
        "banca_percent": 1.0,
        "gatilho_opcoes": [7],
        "meta_min": 0.35,
        "meta_max": 0.45,
    },
    PerfilEntrada.MODERADO: {
        "banca_percent": 1.0,
        "gatilho_opcoes": [6],
        "meta_min": 0.35,
        "meta_max": 0.45,
    },
    PerfilEntrada.AGRESSIVO: {
        "banca_percent": 1.0,
        "gatilho_opcoes": [5],
        "meta_min": 0.35,
        "meta_max": 0.45,
    },
}


# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================


def get_estrategias_disponiveis() -> List[Dict]:
    """Retorna lista de estratégias disponíveis para UI."""
    estrategias = []
    for estrategia in EstrategiaDobras:
        config = ESTRATEGIA_DOBRAS_CONFIG[estrategia]
        estrategias.append(
            {
                "id": estrategia.value,
                "nome": config["nome"],
                "dobras": config["dobras"],
                "risco": config["risco"],
                "lucro_esperado": config["lucro_esperado"],
                "descricao": config["descricao"],
                "cor": config["cor"],
                "emoji": config["emoji"],
            }
        )
    return estrategias


def get_perfis_disponiveis() -> List[Dict]:
    """Retorna lista de perfis disponíveis para UI."""
    perfis = []
    for perfil in PerfilEntrada:
        config = PERFIL_ENTRADA_CONFIG[perfil]
        perfis.append(
            {
                "id": perfil.name,
                "nome": perfil.name,
                "gatilho": config["gatilho"],
                "descricao": config["descricao"],
                "caracteristica": config["caracteristica"],
                "emoji": config["emoji"],
            }
        )
    return perfis


def calcular_preview_apostas(banca: float, estrategia: EstrategiaDobras) -> Dict:
    """Calcula preview das apostas para UI."""
    config = ESTRATEGIA_DOBRAS_CONFIG[estrategia]
    dobras = config["dobras"]
    total_partes = config["total_partes"]
    parte = banca / total_partes

    preview = {
        "estrategia": estrategia.value,
        "nome": config["nome"],
        "banca": banca,
        "apostas": [],
    }

    for i, proporcao in enumerate(dobras, 1):
        valor = max(1.0, round(parte * proporcao, 2))
        preview["apostas"].append({"dobra": i, "valor": valor, "proporcao": proporcao})

    return preview


if __name__ == "__main__":
    # Teste básico
    print("=" * 60)
    print("STRATEGY ENGINE v9.0 - Teste")
    print("=" * 60)

    print("\n📊 Estratégias Disponíveis:")
    for e in get_estrategias_disponiveis():
        print(f"  {e['emoji']} {e['nome']} - Risco: {e['risco']}")

    print("\n📊 Perfis Disponíveis:")
    for p in get_perfis_disponiveis():
        print(f"  {p['emoji']} {p['nome']} - Gatilho: {p['gatilho']} baixas")

    print("\n📊 Preview de Apostas (Banca R$ 500):")
    for estrategia in EstrategiaDobras:
        preview = calcular_preview_apostas(500, estrategia)
        print(f"\n  {preview['nome']}:")
        for aposta in preview["apostas"]:
            print(f"    Dobra {aposta['dobra']}: R$ {aposta['valor']:.2f}")

    print("\n✅ Teste concluído!")
