#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRATEGY ENGINE - Martingale Classico
======================================

Banca fixa, 3 modos (agressivo/moderado/conservador).
- Target randomico: 1.98x a 2.00x (anti-deteccao)
- Gatilho: 6 baixas consecutivas (< 2.0x)
- Progressao: 1x, 2x, 4x, 8x (depende do modo)
"""

import logging
import random
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.config import LOGS_DIR
from src.bot.setups import BaseSetup, SetupModerado
from src.notifications.telegram import (
    notify_trick,
    notify_hit,
    notify_miss,
    notify_break,
    notify_setup_change,
)

# ============================================================
# LOGGER
# ============================================================
log_path = LOGS_DIR / "strategy_engine.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    )
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)


# ============================================================
# ESTRUTURAS DE DADOS
# ============================================================

@dataclass
class BetRecommendation:
    """Recomendacao de aposta."""
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
    """Estatisticas da sessao."""
    total_sequences: int = 0
    wins_by_dobra: Dict[int, int] = field(
        default_factory=dict
    )
    total_breaks: int = 0
    total_profit: float = 0.0
    current_dobra: int = 0

    @property
    def total_wins(self) -> int:
        return sum(self.wins_by_dobra.values())


# ============================================================
# MARTINGALE POLICY
# ============================================================

class MartingalePolicy:
    """
    Martingale classico com banca fixa.

    Fluxo:
    1. Aguarda 6 LOWs consecutivos
    2. Bet 1: unit base (banca/divisor)
    3. Perdeu → Bet 2: 2x unit
    4. Perdeu → Bet 3: 4x unit (se modo permite)
    5. Perdeu → Bet 4: 8x unit (se modo permite)
    6. Ganhou em qualquer → ciclo fecha
    7. Perdeu todos → BREAK
    """

    def __init__(self, setup: BaseSetup, banca: float):
        self.setup = setup
        self.banca = banca  # FIXA, nao muda

        # Estado
        self.is_active = False
        self.dobra_atual = 0
        self.target_ativo = 0.0
        self.threshold = setup.threshold
        self.lows_needed = setup.trigger_base

        # Alertas
        self.alerta_trick_enviado = False

        # Estatisticas
        self.stats = SessionStats()

        # Prejuizo acumulado no ciclo
        self._cycle_loss = 0.0

        # LOWs contadas APOS o ultimo reset/win/break.
        # Inicia "saturado" para permitir o trigger inicial assim
        # que houver 6 LOWs no historico carregado.
        self._lows_since_reset = 9999

        logger.info(
            f"Martingale: {setup.name} | "
            f"Banca=R${banca:.2f} | "
            f"Bets={setup.get_all_bets(banca)}"
        )

    def _sortear_target(self) -> float:
        """Target aleatorio 1.98-2.00x."""
        return round(random.uniform(1.98, 2.00), 2)

    def _count_consecutive_lows(
        self, history: deque
    ) -> int:
        """Conta LOWs consecutivos no final."""
        count = 0
        for value in reversed(history):
            if value < self.threshold:
                count += 1
            else:
                break
        return count

    def feed_round(self, explosion: float):
        """Atualiza contagem de LOWs desde o ultimo reset.

        Garante que apos um break/win seja necessario aguardar 6 LOWs
        novas antes de reativar - independentemente das LOWs que ja
        estao no historico (incluindo as proprias apostas perdidas).
        """
        if explosion < self.threshold:
            self._lows_since_reset += 1
        else:
            self._lows_since_reset = 0

    def check_trigger(self, history: deque) -> bool:
        """Verifica se deve ativar.

        Exige duas condicoes:
        - 6 LOWs consecutivas no historico (gatilho original)
        - 6 LOWs registradas APOS o ultimo reset (evita reativar
          imediatamente apos um break, contando as proprias apostas
          perdidas como parte do gatilho).
        """
        if self.is_active:
            return False

        lows = self._count_consecutive_lows(history)

        try:
            if (lows == self.lows_needed
                    and not self.alerta_trick_enviado):
                notify_trick(lows, self.setup.name)
                self.alerta_trick_enviado = True
            elif lows < self.lows_needed:
                self.alerta_trick_enviado = False
        except Exception as e:
            logger.error(f"Erro alerta: {e}")

        if (lows >= self.lows_needed
                and self._lows_since_reset >= self.lows_needed):
            self._activate()
            return True

        return False

    def _activate(self):
        """Ativa ciclo."""
        self.is_active = True
        self.dobra_atual = 1
        self._cycle_loss = 0.0
        self.stats.total_sequences += 1
        self.stats.current_dobra = 1
        bet = self.setup.get_bet(0, self.banca)
        logger.info(
            f"ATIVANDO {self.setup.name} - "
            f"Dobra 1/{self.setup.max_dobras} "
            f"R${bet:.2f}"
        )

    def get_bet_recommendation(
        self, balance: float
    ) -> Optional[BetRecommendation]:
        """Retorna recomendacao de aposta."""
        if not self.is_active:
            return None

        idx = self.dobra_atual - 1
        bet = self.setup.get_bet(idx, self.banca)
        target = self._sortear_target()
        self.target_ativo = target

        max_d = self.setup.max_dobras

        return BetRecommendation(
            strategy_name=(
                f"{self.setup.name} | "
                f"Dobra {self.dobra_atual}/{max_d}"
            ),
            bet_1=bet,
            target_1=target,
            bet_2=0,
            target_2=0,
            justification=(
                f"Dobra {self.dobra_atual}/{max_d}"
                f" - Target {target}x"
                f" - R${bet:.2f}"
            ),
            confidence=1.0,
            ready=True,
        )

    def process_result(
        self, explosion: float, current_balance: float
    ) -> bool:
        """
        Processa resultado.
        Retorna True se precisa preparar nova aposta.
        """
        if not self.is_active:
            return False

        target = self.target_ativo
        idx = self.dobra_atual - 1
        bet_value = self.setup.get_bet(idx, self.banca)

        if explosion < target:
            # PERDEU
            self._cycle_loss += bet_value

            if self.dobra_atual >= self.setup.max_dobras:
                # Esgotou todas as dobras → BREAK
                self.stats.total_breaks += 1
                loss = self._cycle_loss
                self.stats.total_profit -= loss
                logger.warning(
                    f"BREAK {self.setup.name} "
                    f"| Perda: -R${loss:.2f}"
                )
                notify_break(self.setup.name, loss)
                self._reset()
                return False
            else:
                # Proxima dobra
                self.dobra_atual += 1
                self.stats.current_dobra = (
                    self.dobra_atual
                )
                next_bet = self.setup.get_bet(
                    self.dobra_atual - 1, self.banca
                )
                max_d = self.setup.max_dobras
                logger.info(
                    f"Dobra {self.dobra_atual - 1}"
                    f"/{max_d} perdeu -> "
                    f"dobra {self.dobra_atual} "
                    f"R${next_bet:.2f}"
                )
                notify_miss(
                    self.dobra_atual - 1,
                    max_d,
                    next_bet,
                )
                return True
        else:
            # GANHOU
            gross = bet_value * (explosion - 1)
            net = gross - self._cycle_loss
            self.stats.total_profit += net

            d = self.dobra_atual
            self.stats.wins_by_dobra[d] = (
                self.stats.wins_by_dobra.get(d, 0) + 1
            )

            notify_hit(
                d, net, current_balance + net,
            )
            logger.info(
                f"GANHO dobra {d} "
                f"({explosion:.2f}x) "
                f"| Lucro: R${net:+.2f}"
            )

            self._reset()
            return False

    def _reset(self):
        """Reseta ciclo."""
        self.is_active = False
        self.dobra_atual = 0
        self.target_ativo = 0.0
        self._cycle_loss = 0.0
        self.stats.current_dobra = 0
        # Apos um reset (win ou break), exigir 6 LOWs novas antes
        # de reativar. Zera o contador para nao reaproveitar LOWs
        # antigas (incluindo as das proprias apostas perdidas).
        self._lows_since_reset = 0

    def get_stats(self) -> SessionStats:
        return self.stats


# ============================================================
# STRATEGY ENGINE
# ============================================================

class StrategyEngine:
    """Motor de estrategia com hot-swap."""

    def __init__(self):
        self.explosion_history: deque = deque(
            maxlen=260
        )
        self.policy: Optional[MartingalePolicy] = None
        self.banca: float = 0.0

        # Hot-swap
        self._pending_setup: Optional[BaseSetup] = None
        self._swap_lock = threading.Lock()

        # Multiplicador (compat, sempre 1.0)
        self.bet_multiplier: float = 1.0

        self.aposta_preparada: Optional[
            BetRecommendation
        ] = None
        self.strategy_stats: Dict[str, Dict] = {}

    def iniciar_sessao(
        self,
        banca: float,
        setup: Optional[BaseSetup] = None,
    ):
        """Inicia sessao com banca fixa."""
        self.banca = banca
        if setup is None:
            setup = SetupModerado()

        self.policy = MartingalePolicy(setup, banca)

        self.strategy_stats[setup.name] = {
            "total_recommendations": 0,
            "total_hits": 0,
            "total_misses": 0,
            "hit_rate": 0.0,
            "profit_loss": 0.0,
        }

        logger.info("=== SESSAO INICIADA ===")
        logger.info(f"Banca: R$ {banca:.2f} (fixa)")
        logger.info(f"Setup: {setup.get_description()}")
        logger.info(
            f"Gatilho: {setup.trigger_base} LOWs"
        )
        logger.info(
            f"Bets: {setup.get_all_bets(banca)}"
        )

    # -- Hot-Swap ----------------------------------------

    def request_swap(self, new_setup: BaseSetup):
        """Solicita troca de setup."""
        with self._swap_lock:
            if self.policy and self.policy.is_active:
                self._pending_setup = new_setup
                logger.info(
                    f"Troca pendente: "
                    f"{self.policy.setup.name}"
                    f" -> {new_setup.name}"
                )
            else:
                self._apply_swap(new_setup)

    def _apply_swap(self, new_setup: BaseSetup):
        old = (
            self.policy.setup.name
            if self.policy else "nenhum"
        )
        self.policy = MartingalePolicy(
            new_setup, self.banca
        )
        if new_setup.name not in self.strategy_stats:
            self.strategy_stats[new_setup.name] = {
                "total_recommendations": 0,
                "total_hits": 0,
                "total_misses": 0,
                "hit_rate": 0.0,
                "profit_loss": 0.0,
            }
        notify_setup_change(old, new_setup.name)
        logger.info(
            f"Setup: {old} -> {new_setup.name}"
        )

    def _check_pending_swap(self):
        with self._swap_lock:
            if self._pending_setup is not None:
                self._apply_swap(self._pending_setup)
                self._pending_setup = None

    def has_pending_swap(self) -> bool:
        with self._swap_lock:
            return self._pending_setup is not None

    def get_pending_setup_name(self) -> Optional[str]:
        with self._swap_lock:
            if self._pending_setup:
                return self._pending_setup.name
            return None

    # -- Processamento -----------------------------------

    def add_explosion_value(
        self, value: float
    ) -> Tuple[
        bool, Optional[BetRecommendation],
        Optional[str]
    ]:
        """Processa cada explosao."""
        self.explosion_history.append(value)

        if self.policy is None:
            return False, None, "Sessao nao iniciada"

        self.policy.feed_round(value)

        needs_bet = False
        was_active = self.policy.is_active
        if was_active:
            needs_bet = self.policy.process_result(
                value, self.banca
            )
            if not self.policy.is_active:
                self._check_pending_swap()

        triggered = False
        if not was_active and not self.policy.is_active:
            triggered = self.policy.check_trigger(
                self.explosion_history
            )

        if needs_bet or triggered:
            triggered = True

        lows_hist = self.policy._count_consecutive_lows(
            self.explosion_history
        )
        lows = min(lows_hist, self.policy._lows_since_reset)
        sn = self.policy.setup.name
        max_d = self.policy.setup.max_dobras
        needed = self.policy.lows_needed
        # Limita o display a "needed" para nao mostrar 9999 inicial
        lows_disp = min(lows, needed)
        msg = (
            f"Baixas: {lows_disp}/{needed} | "
            f"{sn} | Aguardando..."
        )

        if self.policy.is_active:
            d = self.policy.dobra_atual
            msg = (
                f"ATIVO | {sn} | "
                f"Dobra {d}/{max_d}"
            )

        if self.has_pending_swap():
            p = self.get_pending_setup_name()
            msg += f" | Troca -> {p}"

        return triggered, None, msg

    def prepare_bets_for_balance(
        self, balance: float
    ) -> Optional[BetRecommendation]:
        """Prepara aposta."""
        if self.policy and self.policy.is_active:
            rec = self.policy.get_bet_recommendation(
                balance
            )
            if rec:
                self.aposta_preparada = rec
                sn = self.policy.setup.name
                if sn not in self.strategy_stats:
                    self.strategy_stats[sn] = {
                        "total_recommendations": 0,
                        "total_hits": 0,
                        "total_misses": 0,
                        "hit_rate": 0.0,
                        "profit_loss": 0.0,
                    }
                self.strategy_stats[sn][
                    "total_recommendations"
                ] += 1
                return rec

        self.aposta_preparada = None
        return None

    def get_prepared_bets(
        self,
    ) -> Optional[BetRecommendation]:
        return self.aposta_preparada

    def reset_prepared_bets(self):
        self.aposta_preparada = None

    def get_current_analysis(self) -> Dict:
        """Analise atual para a UI."""
        if not self.policy:
            return {
                "history_size": len(
                    self.explosion_history
                ),
                "prepared_bets_ready": False,
                "status": "Aguardando",
                "martingale_active": False,
                "dobra_atual": 0,
                "max_dobras": 0,
                "baixos_consecutivos": "0/0",
                "strategy_name": "N/A",
                "setup_name": "N/A",
                "total_sequences": 0,
                "wins_by_dobra": {},
                "total_wins": 0,
                "total_breaks": 0,
                "total_profit": 0.0,
                "pending_swap": None,
                "next_bet_value": 0,
            }

        active = self.policy.is_active
        d = self.policy.dobra_atual
        max_d = self.policy.setup.max_dobras
        # UI mostra o min entre LOWs do historico e LOWs apos reset
        # para refletir o gatilho real (que exige ambas as condicoes).
        lows_hist = self.policy._count_consecutive_lows(
            self.explosion_history
        )
        lows_since_reset = min(
            self.policy._lows_since_reset,
            self.policy.lows_needed,
        )
        lows = min(lows_hist, lows_since_reset)
        sn = self.policy.setup.name

        if active:
            status = (
                f"{sn} - "
                f"Dobra {d}/{max_d}"
            )
        else:
            status = "Aguardando gatilho..."

        stats = self.policy.get_stats()

        # Proxima aposta
        next_bet = 0.0
        try:
            idx = max(0, d - 1) if active else 0
            next_bet = self.policy.setup.get_bet(
                idx, self.banca
            )
        except Exception:
            pass

        return {
            "history_size": len(
                self.explosion_history
            ),
            "prepared_bets_ready": (
                self.aposta_preparada is not None
            ),
            "status": status,
            "martingale_active": active,
            "dobra_atual": d,
            "max_dobras": max_d,
            "baixos_consecutivos": (
                f"{lows}/{self.policy.lows_needed}"
            ),
            "strategy_name": sn,
            "setup_name": sn,
            "total_sequences": (
                stats.total_sequences
            ),
            "wins_by_dobra": dict(
                stats.wins_by_dobra
            ),
            "total_wins": stats.total_wins,
            "total_breaks": stats.total_breaks,
            "total_profit": stats.total_profit,
            "pending_swap": (
                self.get_pending_setup_name()
            ),
            "next_bet_value": next_bet,
        }

    def get_strategies_stats(self) -> List[Dict]:
        if not self.policy:
            return []

        sn = self.policy.setup.name
        s = self.strategy_stats.get(sn, {})
        recs = s.get("total_recommendations", 0)
        if recs > 0:
            s["hit_rate"] = (
                s["total_hits"] / recs * 100
            )

        ps = self.policy.get_stats()
        return [{
            "name": sn,
            "total_recommendations": recs,
            "total_hits": s.get("total_hits", 0),
            "total_misses": s.get(
                "total_misses", 0
            ),
            "total_hit_rate": s.get("hit_rate", 0.0),
            "profit_loss": ps.total_profit,
            "total_wins": ps.total_wins,
            "total_breaks": ps.total_breaks,
        }]

    def evaluate_executed_bet(
        self, explosion: float, executed_bet: Dict
    ) -> Dict:
        target = executed_bet.get("target_1", 0)
        hit = (
            explosion >= target if target > 0
            else False
        )

        sn = (
            self.policy.setup.name
            if self.policy else "N/A"
        )
        if sn in self.strategy_stats:
            st = self.strategy_stats[sn]
            if hit:
                st["total_hits"] += 1
            else:
                st["total_misses"] += 1

        return {
            "explosion_value": explosion,
            "recommendation_hit": hit,
            "target_1": target,
            "bet_1": executed_bet.get("bet_1", 0),
            "strategy": executed_bet.get(
                "strategy", ""
            ),
            "phase": "N/A",
        }

    def get_setup(self) -> Optional[BaseSetup]:
        if self.policy:
            return self.policy.setup
        return None
