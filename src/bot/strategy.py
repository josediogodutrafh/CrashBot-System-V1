#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRATEGY ENGINE - Motor de Estratégia Multi-Setup
==================================================

Orquestra qualquer setup (1/2, 1/2/4, 1/2/4/8, Inteligente)
com hot-swap thread-safe entre ciclos.

- Target randômico: 1.90x a 2.05x (anti-detecção)
- Gatilho: 6 baixas consecutivas (fixo)
- Quebra: quando esgota todas as dobras do setup ativo
"""

import logging
import random
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pytz

from src.config import LOGS_DIR
from src.bot.setups import BaseSetup, Setup124, SETUP_LIST, get_setup
from src.notifications.telegram import (
    send_telegram_alert,
    notify_trick,
    notify_hit,
    notify_miss,
    notify_break,
    notify_setup_change,
)

# ==============================================================================
# CONFIGURAÇÃO DO LOGGER
# ==============================================================================
log_path = LOGS_DIR / "strategy_engine.log"

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


# Fuso horário de Brasília
BRASILIA_TZ = pytz.timezone("America/Sao_Paulo")


# ==============================================================================
# ESTRUTURAS DE DADOS
# ==============================================================================
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
class SessionStats:
    """Estatísticas da sessão (genéricas para qualquer setup)."""
    total_sequences: int = 0
    wins_by_dobra: Dict[int, int] = field(default_factory=dict)
    total_breaks: int = 0
    total_profit: float = 0.0
    current_dobra: int = 0

    @property
    def total_wins(self) -> int:
        return sum(self.wins_by_dobra.values())


# ==============================================================================
# POLÍTICA MARTINGALE GENÉRICA
# ==============================================================================
class MartingalePolicy:
    """
    Estratégia Martingale genérica para qualquer setup.

    Fluxo:
    1. Aguarda 6 baixas consecutivas (gatilho)
    2. Entra na dobra 1
    3. Se perder, avança até max_dobras
    4. Se ganhar em qualquer dobra, ciclo concluído com lucro
    5. Se esgotar todas as dobras, quebra total
    """

    def __init__(self, setup: BaseSetup, banca: float):
        self.setup = setup
        self.banca = banca

        # Estado
        self.is_active = False
        self.dobra_atual = 0  # 0 = inativo, 1..max_dobras = ativo
        self.target_ativo = 0.0
        self.threshold = 2.0

        # Gatilho fixo: 6 baixas
        self.lows_needed = 6

        # Alertas
        self.alerta_trick_enviado = False

        # Estatísticas
        self.stats = SessionStats()

        # Acumulador de prejuízo no ciclo atual
        self._cycle_loss = 0.0

        logger.info(
            f"MartingalePolicy iniciada - Setup: {setup.name} | "
            f"Banca: R${banca:.2f} | Max dobras: {setup.max_dobras}"
        )
        logger.info(f"Valores por dobra: {setup.get_all_bets(banca)}")

    def _sortear_target(self) -> float:
        """Sorteia target entre 1.90x e 2.05x (anti-detecção)."""
        return round(random.uniform(1.90, 2.05), 2)

    def _count_consecutive_lows(self, history: deque) -> int:
        """Conta baixas consecutivas no final do histórico."""
        count = 0
        for value in reversed(history):
            if value < self.threshold:
                count += 1
            else:
                break
        return count

    def check_trigger(self, history: deque) -> bool:
        """Verifica se deve ativar a estratégia."""
        if self.is_active:
            return False

        lows_count = self._count_consecutive_lows(history)

        try:
            if lows_count == 6 and not self.alerta_trick_enviado:
                notify_trick(lows_count, self.setup.name)
                self.alerta_trick_enviado = True
            elif lows_count < 6:
                self.alerta_trick_enviado = False
        except Exception as e:
            logger.error(f"Erro ao enviar alerta: {e}")

        if lows_count >= self.lows_needed:
            self._activate()
            return True

        return False

    def _activate(self):
        """Ativa a estratégia."""
        self.is_active = True
        self.dobra_atual = 1
        self._cycle_loss = 0.0
        self.stats.total_sequences += 1
        self.stats.current_dobra = 1
        logger.info(
            f"🎯 ATIVANDO {self.setup.name} - Dobra 1/{self.setup.max_dobras}"
        )

    def get_bet_recommendation(self, balance: float) -> Optional[BetRecommendation]:
        """Retorna recomendação de aposta."""
        if not self.is_active:
            return None

        bet = self.setup.get_bet(self.dobra_atual - 1, self.banca)
        target = self._sortear_target()
        self.target_ativo = target

        return BetRecommendation(
            strategy_name=f"{self.setup.name} | Dobra {self.dobra_atual}/{self.setup.max_dobras}",
            bet_1=bet,
            target_1=target,
            bet_2=0,
            target_2=0,
            justification=(
                f"Dobra {self.dobra_atual}/{self.setup.max_dobras} - "
                f"Target {target}x - Aposta R${bet:.2f}"
            ),
            confidence=1.0,
            ready=True,
        )

    def process_result(self, explosion: float, current_balance: float) -> bool:
        """
        Processa resultado da rodada.
        Retorna True se precisa preparar nova aposta (continua ativo).
        """
        if not self.is_active:
            return False

        target = self.target_ativo
        bet_value = self.setup.get_bet(self.dobra_atual - 1, self.banca)

        if explosion < target:
            # PERDEU
            self._cycle_loss += bet_value
            logger.warning(
                f"❌ PERDEU dobra {self.dobra_atual}/{self.setup.max_dobras} "
                f"(explosão {explosion:.2f}x < target {target:.2f}x)"
            )

            if self.dobra_atual >= self.setup.max_dobras:
                # QUEBRA - esgotou todas as dobras
                self.stats.total_breaks += 1
                loss = self._cycle_loss
                self.stats.total_profit -= loss
                logger.error(
                    f"💀 QUEBRA! {self.setup.name} esgotou {self.setup.max_dobras} dobras "
                    f"| Prejuízo: -R${loss:.2f}"
                )
                notify_break(self.setup.name, loss)
                self._reset()
                return False
            else:
                # Avança para próxima dobra
                self.dobra_atual += 1
                self.stats.current_dobra = self.dobra_atual
                next_bet = self.setup.get_bet(self.dobra_atual - 1, self.banca)
                notify_miss(
                    self.dobra_atual - 1,
                    self.setup.max_dobras,
                    next_bet,
                )
                logger.info(
                    f"Continuando - Próxima dobra: {self.dobra_atual}/{self.setup.max_dobras}"
                )
                return True

        else:
            # GANHOU
            gross_win = bet_value * (explosion - 1)  # lucro bruto da aposta
            net_profit = gross_win - self._cycle_loss
            self.stats.total_profit += net_profit

            dobra = self.dobra_atual
            self.stats.wins_by_dobra[dobra] = self.stats.wins_by_dobra.get(dobra, 0) + 1

            notify_hit(dobra, net_profit, current_balance + net_profit)
            logger.info(
                f"✅ GANHO na dobra {dobra} ({explosion:.2f}x) "
                f"| Lucro ciclo: R${net_profit:+.2f}"
            )
            self._reset()
            return False

    def _reset(self):
        """Reseta o ciclo."""
        self.is_active = False
        self.dobra_atual = 0
        self.target_ativo = 0.0
        self._cycle_loss = 0.0
        self.stats.current_dobra = 0

    def get_stats(self) -> SessionStats:
        """Retorna estatísticas da sessão."""
        return self.stats


# ==============================================================================
# STRATEGY ENGINE
# ==============================================================================
class StrategyEngine:
    """Motor de estratégias genérico com hot-swap."""

    def __init__(self):
        self.explosion_history: deque = deque(maxlen=260)
        self.policy: Optional[MartingalePolicy] = None
        self.banca: float = 0.0

        # Hot-swap
        self._pending_setup: Optional[BaseSetup] = None
        self._swap_lock = threading.Lock()

        self.aposta_preparada: Optional[BetRecommendation] = None
        self.strategy_stats: Dict[str, Dict] = {}

    def iniciar_sessao(self, banca: float, setup: Optional[BaseSetup] = None):
        """Inicia a sessão com a banca e setup escolhidos."""
        self.banca = banca
        if setup is None:
            setup = Setup124()

        self.policy = MartingalePolicy(setup, banca)

        self.strategy_stats[setup.name] = {
            "total_recommendations": 0,
            "total_hits": 0,
            "total_misses": 0,
            "hit_rate": 0.0,
            "profit_loss": 0.0,
        }

        logger.info("=== SESSÃO INICIADA ===")
        logger.info(f"Banca: R$ {banca:.2f}")
        logger.info(f"Setup: {setup.get_description()}")
        logger.info(f"Gatilho: 6 baixas consecutivas")
        logger.info(f"Target: 1.90x - 2.05x (randômico)")

    # ── Hot-Swap ──────────────────────────────────────────────────────

    def request_swap(self, new_setup: BaseSetup):
        """
        Solicita troca de setup.
        Se não está em ciclo ativo, troca imediatamente.
        Se está, enfileira para trocar ao final do ciclo.
        """
        with self._swap_lock:
            if self.policy and self.policy.is_active:
                self._pending_setup = new_setup
                logger.info(
                    f"🔄 Troca pendente: {self.policy.setup.name} → {new_setup.name} "
                    f"(aguardando fim do ciclo)"
                )
            else:
                self._apply_swap(new_setup)

    def _apply_swap(self, new_setup: BaseSetup):
        """Aplica a troca de setup imediatamente."""
        old_name = self.policy.setup.name if self.policy else "nenhum"
        self.policy = MartingalePolicy(new_setup, self.banca)

        if new_setup.name not in self.strategy_stats:
            self.strategy_stats[new_setup.name] = {
                "total_recommendations": 0,
                "total_hits": 0,
                "total_misses": 0,
                "hit_rate": 0.0,
                "profit_loss": 0.0,
            }

        notify_setup_change(old_name, new_setup.name)
        logger.info(f"✅ Setup alterado: {old_name} → {new_setup.name}")

    def _check_pending_swap(self):
        """Verifica e aplica swap pendente (chamado entre ciclos)."""
        with self._swap_lock:
            if self._pending_setup is not None:
                self._apply_swap(self._pending_setup)
                self._pending_setup = None

    def has_pending_swap(self) -> bool:
        """Retorna se há troca pendente."""
        with self._swap_lock:
            return self._pending_setup is not None

    def get_pending_setup_name(self) -> Optional[str]:
        """Nome do setup pendente, se houver."""
        with self._swap_lock:
            if self._pending_setup:
                return self._pending_setup.name
            return None

    # ── Processamento ──────────────────────────────────────────────────

    def add_explosion_value(
        self, value: float
    ) -> Tuple[bool, Optional[BetRecommendation], Optional[str]]:
        """Processa cada explosão."""
        self.explosion_history.append(value)

        if self.policy is None:
            return False, None, "Sessão não iniciada"

        needs_bet = False
        if self.policy.is_active:
            needs_bet = self.policy.process_result(value, self.banca)

            # Se ciclo terminou, verifica swap pendente
            if not self.policy.is_active:
                self._check_pending_swap()

        triggered = False
        if not self.policy.is_active:
            triggered = self.policy.check_trigger(self.explosion_history)

        if needs_bet or triggered:
            triggered = True

        lows = self.policy._count_consecutive_lows(self.explosion_history)
        setup_name = self.policy.setup.name
        max_d = self.policy.setup.max_dobras
        msg = f"Baixas: {lows}/6 | Setup: {setup_name} | Aguardando..."

        if self.policy.is_active:
            msg = f"🎯 ATIVO | {setup_name} | Dobra {self.policy.dobra_atual}/{max_d}"

        if self.has_pending_swap():
            msg += f" | ⏳ Troca pendente → {self.get_pending_setup_name()}"

        return triggered, None, msg

    def prepare_bets_for_balance(
        self, balance: float
    ) -> Optional[BetRecommendation]:
        """Prepara aposta para o saldo atual."""
        if self.policy and self.policy.is_active:
            rec = self.policy.get_bet_recommendation(balance)
            if rec:
                self.aposta_preparada = rec
                setup_name = self.policy.setup.name
                if setup_name not in self.strategy_stats:
                    self.strategy_stats[setup_name] = {
                        "total_recommendations": 0,
                        "total_hits": 0,
                        "total_misses": 0,
                        "hit_rate": 0.0,
                        "profit_loss": 0.0,
                    }
                self.strategy_stats[setup_name]["total_recommendations"] += 1
                return rec

        self.aposta_preparada = None
        return None

    def get_prepared_bets(self) -> Optional[BetRecommendation]:
        """Retorna aposta preparada."""
        return self.aposta_preparada

    def reset_prepared_bets(self):
        """Reseta aposta preparada."""
        self.aposta_preparada = None

    def get_current_analysis(self) -> Dict:
        """Retorna análise atual para a UI."""
        if not self.policy:
            return {
                "history_size": len(self.explosion_history),
                "prepared_bets_ready": False,
                "status": "Aguardando",
                "martingale_active": False,
                "dobra_atual": 0,
                "max_dobras": 0,
                "baixos_consecutivos": "0/6",
                "strategy_name": "N/A",
                "setup_name": "N/A",
                "total_sequences": 0,
                "wins_by_dobra": {},
                "total_wins": 0,
                "total_breaks": 0,
                "total_profit": 0.0,
                "pending_swap": None,
            }

        active = self.policy.is_active
        dobra = self.policy.dobra_atual
        max_d = self.policy.setup.max_dobras
        lows = self.policy._count_consecutive_lows(self.explosion_history)
        setup_name = self.policy.setup.name

        # Info de ciclo
        cycle_info = None
        if active and dobra > 0:
            cycle_info = self.policy.setup.get_position_info(dobra - 1)
            ci = cycle_info["cycle"]
            tc = cycle_info["total_cycles"]
            status = (
                f"{setup_name} - Ciclo {ci}/{tc} | "
                f"Dobra {dobra}/{max_d}"
            )
        elif active:
            status = f"{setup_name} - Dobra {dobra}/{max_d}"
        else:
            status = "Aguardando gatilho..."

        stats = self.policy.get_stats()

        return {
            "history_size": len(self.explosion_history),
            "prepared_bets_ready": self.aposta_preparada is not None,
            "status": status,
            "martingale_active": active,
            "dobra_atual": dobra,
            "max_dobras": max_d,
            "baixos_consecutivos": f"{lows}/6",
            "strategy_name": setup_name,
            "setup_name": setup_name,
            "total_sequences": stats.total_sequences,
            "wins_by_dobra": dict(stats.wins_by_dobra),
            "total_wins": stats.total_wins,
            "total_breaks": stats.total_breaks,
            "total_profit": stats.total_profit,
            "pending_swap": self.get_pending_setup_name(),
            "bet_table": self.policy.setup.get_all_bets(self.banca),
            "cycle_info": cycle_info,
            "n_cycles": self.policy.setup.n_cycles,
            "bets_by_cycle": self.policy.setup.get_bets_by_cycle(self.banca),
        }

    def get_strategies_stats(self) -> List[Dict]:
        """Retorna estatísticas."""
        if not self.policy:
            return []

        setup_name = self.policy.setup.name
        stats = self.strategy_stats.get(setup_name, {})

        if stats.get("total_recommendations", 0) > 0:
            stats["hit_rate"] = (
                stats["total_hits"] / stats["total_recommendations"]
            ) * 100

        policy_stats = self.policy.get_stats()

        return [{
            "name": f"Martingale {setup_name}",
            "total_recommendations": stats.get("total_recommendations", 0),
            "total_hits": stats.get("total_hits", 0),
            "total_misses": stats.get("total_misses", 0),
            "total_hit_rate": stats.get("hit_rate", 0.0),
            "profit_loss": policy_stats.total_profit,
            "total_wins": policy_stats.total_wins,
            "total_breaks": policy_stats.total_breaks,
        }]

    def evaluate_executed_bet(
        self, explosion: float, executed_bet: Dict
    ) -> Dict:
        """Avalia resultado de aposta executada."""
        target = executed_bet.get("target_1", 0)
        hit = explosion >= target if target > 0 else False

        setup_name = self.policy.setup.name if self.policy else "N/A"
        if setup_name in self.strategy_stats:
            stats = self.strategy_stats[setup_name]
            if hit:
                stats["total_hits"] += 1
            else:
                stats["total_misses"] += 1

        return {
            "explosion_value": explosion,
            "recommendation_hit": hit,
            "target_1": target,
            "bet_1": executed_bet.get("bet_1", 0),
            "strategy": executed_bet.get("strategy", ""),
            "phase": "N/A",
        }

    def get_setup(self) -> Optional[BaseSetup]:
        """Retorna o setup ativo."""
        if self.policy:
            return self.policy.setup
        return None
