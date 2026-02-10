#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GESTÃO DE BANCA
===============

Controla saldo, metas de lucro, saques e reposições.
- Meta configurável: 10%, 20%, 30%, 50%, 70%, 100%
- Saque automático ao atingir meta
- Reposição automática ao zerar banca
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

METAS_DISPONIVEIS = [10, 20, 30, 50, 70, 100]


@dataclass
class Transaction:
    """Registro de saque ou depósito."""
    timestamp: datetime
    tipo: str  # "saque" ou "deposito"
    valor: float
    saldo_apos: float


class BankrollManager:
    """Gerencia caixa (reserva), banca (sessao), metas e fluxo financeiro."""

    def __init__(
        self,
        caixa: float = 0.0,
        banca: float = 500.0,
        meta_percent: float = 20,
        stop_loss_percent: float = 100,
    ):
        # Caixa = reserva total | Banca = alocacao para apostas
        self.caixa = caixa if caixa > 0 else banca
        self.banca = banca
        self.bankroll_base = banca  # alias para compatibilidade

        self.current_bankroll = banca

        # Meta de lucro (% do CAIXA)
        self.meta_percent = meta_percent
        self.meta_value = self.caixa * meta_percent / 100

        # Stop Loss (% do CAIXA)
        self.stop_loss_percent = stop_loss_percent
        self.stop_loss_value = self.caixa * stop_loss_percent / 100

        # Contadores financeiros
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
            f"BankrollManager: caixa=R${self.caixa:.2f}, "
            f"banca=R${banca:.2f} ({self.n_bancas:.1f} bancas), "
            f"meta={meta_percent:.1f}% do caixa (R${self.meta_value:.2f}), "
            f"stop_loss={stop_loss_percent:.1f}% do caixa "
            f"(R${self.stop_loss_value:.2f})"
        )

    @property
    def n_bancas(self) -> float:
        """Quantas bancas cabem no caixa."""
        if self.banca <= 0:
            return 0.0
        return self.caixa / self.banca

    # ── Meta ──────────────────────────────────────────────────────────

    def set_meta(self, percent: float):
        """Altera a meta de lucro (% do caixa)."""
        if percent <= 0:
            raise ValueError(f"Meta {percent}% inválida. Deve ser > 0.")
        self.meta_percent = percent
        self.meta_value = self.caixa * percent / 100
        logger.info(
            f"Meta alterada para {percent:.1f}% do caixa "
            f"(R${self.meta_value:.2f})"
        )

    def get_meta_threshold(self) -> float:
        """Saldo que dispara o saque."""
        return self.bankroll_base + self.meta_value

    def get_meta_progress(self) -> float:
        """Progresso até a meta (0.0 a 1.0+)."""
        if self.meta_value <= 0:
            return 0.0
        profit = self.current_bankroll - self.bankroll_base
        return max(0.0, profit / self.meta_value)

    def check_meta_reached(self) -> bool:
        """Verifica se a meta foi atingida."""
        return self.current_bankroll >= self.get_meta_threshold()

    # ── Saque e Depósito ──────────────────────────────────────────────

    def execute_withdrawal(self) -> float:
        """Saca o excedente acima da banca base. Retorna valor sacado."""
        if self.current_bankroll <= self.bankroll_base:
            return 0.0

        withdraw = round(self.current_bankroll - self.bankroll_base, 2)
        self.total_withdrawn += withdraw
        self.n_withdrawals += 1
        self.current_bankroll = self.bankroll_base

        self.transactions.append(Transaction(
            timestamp=datetime.now(),
            tipo="saque",
            valor=withdraw,
            saldo_apos=self.current_bankroll,
        ))

        logger.info(f"SAQUE: R${withdraw:.2f} | Total sacado: R${self.total_withdrawn:.2f}")
        return withdraw

    def execute_deposit(self) -> float:
        """Repõe a banca base após bust. Retorna valor depositado."""
        self.total_deposited += self.bankroll_base
        self.n_deposits += 1
        self.current_bankroll = self.bankroll_base

        self.transactions.append(Transaction(
            timestamp=datetime.now(),
            tipo="deposito",
            valor=self.bankroll_base,
            saldo_apos=self.current_bankroll,
        ))

        logger.info(
            f"DEPÓSITO: R${self.bankroll_base:.2f} | "
            f"Total depositado: R${self.total_deposited:.2f}"
        )
        return self.bankroll_base

    def check_bust(self) -> bool:
        """Verifica se a banca zerou."""
        return self.current_bankroll <= 0

    def check_stop_loss(self) -> bool:
        """Verifica se atingiu o stop loss."""
        loss = self.bankroll_base - self.current_bankroll
        return loss >= self.stop_loss_value

    # ── Atualização de saldo ──────────────────────────────────────────

    def update_balance(self, pnl: float):
        """Atualiza saldo após resultado de aposta."""
        self.current_bankroll = round(self.current_bankroll + pnl, 2)

    def sync_balance(self, detected_balance: float):
        """Sincroniza com saldo detectado via OCR (para correções)."""
        self.current_bankroll = detected_balance

    # ── Relatórios ────────────────────────────────────────────────────

    def get_net_profit(self) -> float:
        """Lucro líquido = sacado + saldo atual - depositado."""
        return self.total_withdrawn + self.current_bankroll - self.total_deposited

    def get_session_summary(self) -> dict:
        """Resumo completo da sessão."""
        elapsed = (datetime.now() - self.session_start).total_seconds()
        profit = self.get_net_profit()

        return {
            "caixa": self.caixa,
            "banca": self.banca,
            "n_bancas": self.n_bancas,
            "bankroll_base": self.bankroll_base,
            "current_bankroll": self.current_bankroll,
            "meta_percent": self.meta_percent,
            "meta_value": self.meta_value,
            "meta_progress": self.get_meta_progress(),
            "meta_reached": self.check_meta_reached(),
            "total_deposited": self.total_deposited,
            "total_withdrawn": self.total_withdrawn,
            "n_deposits": self.n_deposits,
            "n_withdrawals": self.n_withdrawals,
            "net_profit": profit,
            "roi": (profit / self.total_deposited * 100) if self.total_deposited > 0 else 0,
            "elapsed_seconds": elapsed,
        }
