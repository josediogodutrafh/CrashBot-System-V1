#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GESTAO DE BANCA
===============

Banca fixa — o valor informado pelo usuario nao muda.
Apenas rastreia o saldo real para exibicao na GUI.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Registro de saque ou deposito."""
    timestamp: datetime
    tipo: str
    valor: float
    saldo_apos: float


class BankrollManager:
    """Gerencia banca fixa e saldo real."""

    def __init__(
        self,
        banca: float = 500.0,
        # Compat: aceita mas ignora
        caixa: float = 0.0,
        meta_percent: float = 0,
        stop_loss_percent: float = 0,
        compound_pct: float = 0.0,
    ):
        self.banca = banca  # FIXA, nao muda
        self.bankroll_base = banca
        self.current_bankroll = banca
        self.caixa = banca  # compat

        # Compat: inativos
        self.meta_percent = 0
        self.meta_value = 0
        self.stop_loss_percent = 0
        self.stop_loss_value = 0
        self.compound_pct = 0.0
        self.total_compounded = 0.0

        # Contadores
        self.total_deposited = banca
        self.total_withdrawn = 0.0
        self.n_deposits = 1
        self.n_withdrawals = 0

        # Historico
        self.transactions: List[Transaction] = []

        # Sessao
        self.session_start = datetime.now()
        self.session_start_balance = banca

        logger.info(
            f"BankrollManager: "
            f"banca=R${banca:.2f} (fixa)"
        )

    @property
    def n_bancas(self) -> float:
        return 1.0

    @property
    def effective_banca(self) -> float:
        """Banca fixa (nao muda)."""
        return self.banca

    @property
    def drawdown_from_peak(self) -> float:
        return 0.0

    # -- Compat stubs -----------------------------------

    def set_meta(self, percent: float):
        pass

    def get_meta_threshold(self) -> float:
        return float("inf")

    def get_meta_progress(self) -> float:
        return 0.0

    def check_meta_reached(self) -> bool:
        return False

    def check_stop_loss(self) -> bool:
        return False

    def apply_compound(self, profit: float) -> float:
        return 0.0

    def check_bust(self) -> bool:
        return self.current_bankroll <= 0

    # -- Saldo real (apenas rastreamento) ---------------

    def update_balance(self, pnl: float):
        """Atualiza saldo real apos resultado."""
        self.current_bankroll = round(
            self.current_bankroll + pnl, 2
        )

    def sync_balance(self, detected_balance: float):
        """Sincroniza com saldo real da plataforma."""
        self.current_bankroll = detected_balance

    # -- Saque e Deposito (compat) ----------------------

    def execute_withdrawal(self) -> float:
        if self.current_bankroll <= self.bankroll_base:
            return 0.0
        withdraw = round(
            self.current_bankroll - self.bankroll_base,
            2,
        )
        self.total_withdrawn += withdraw
        self.n_withdrawals += 1
        self.current_bankroll = self.bankroll_base
        self.transactions.append(Transaction(
            timestamp=datetime.now(),
            tipo="saque",
            valor=withdraw,
            saldo_apos=self.current_bankroll,
        ))
        return withdraw

    def execute_deposit(self) -> float:
        self.total_deposited += self.banca
        self.n_deposits += 1
        self.current_bankroll += self.banca
        self.transactions.append(Transaction(
            timestamp=datetime.now(),
            tipo="deposito",
            valor=self.banca,
            saldo_apos=self.current_bankroll,
        ))
        return self.banca

    # -- Relatorios -------------------------------------

    def get_net_profit(self) -> float:
        return (
            self.total_withdrawn
            + self.current_bankroll
            - self.total_deposited
        )

    def get_session_summary(self) -> dict:
        elapsed = (
            datetime.now() - self.session_start
        ).total_seconds()
        profit = self.get_net_profit()
        dep = self.total_deposited

        return {
            "caixa": self.banca,
            "banca": self.banca,
            "n_bancas": 1.0,
            "bankroll_base": self.bankroll_base,
            "current_bankroll": (
                self.current_bankroll
            ),
            "meta_percent": 0,
            "meta_value": 0,
            "meta_progress": 0,
            "meta_reached": False,
            "total_deposited": self.total_deposited,
            "total_withdrawn": self.total_withdrawn,
            "n_deposits": self.n_deposits,
            "n_withdrawals": self.n_withdrawals,
            "net_profit": profit,
            "roi": (
                (profit / dep * 100) if dep > 0
                else 0
            ),
            "elapsed_seconds": elapsed,
            "compound_pct": 0,
            "total_compounded": 0,
            "effective_banca": self.banca,
            "peak_bankroll": self.banca,
            "drawdown_from_peak": 0,
        }
