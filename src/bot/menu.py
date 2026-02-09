#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MENU INTERATIVO + HOT-SWAP
===========================

Menu de configuracao inicial (caixa, banca, setup, meta, horarios)
e listener de teclado para hot-swap em tempo real.

Teclas de atalho (durante execucao):
  F1  -> Setup 1/2
  F2  -> Setup 1/2 + 1/2
  F3  -> Setup 1/2 + 1/2 + 1/2
  F4  -> Setup 1/2/4
  F5  -> Setup 1/2/4 + 1/2/4
  F6  -> Setup 1/2/4/8
  F7  -> Setup 1/2/4/8/16
  F8  -> Ciclar meta
  F9  -> Pausar/retomar
  F10 -> Encerrar
"""

import logging
import msvcrt
import threading
import time
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.bot.setups import (
    AVAILABLE_SETUPS,
    SETUP_LIST,
    BaseSetup,
    get_setup,
)
from src.bot.bankroll import METAS_DISPONIVEIS

logger = logging.getLogger(__name__)

# Codigos de tecla de funcao no Windows (msvcrt)
FKEY_MAP = {
    59: "F1",   # 0x3B
    60: "F2",   # 0x3C
    61: "F3",   # 0x3D
    62: "F4",   # 0x3E
    63: "F5",   # 0x3F
    64: "F6",   # 0x40
    65: "F7",   # 0x41
    66: "F8",   # 0x42
    67: "F9",   # 0x43
    68: "F10",  # 0x44
}

# Mapa F-key -> nome do setup
FKEY_SETUP_MAP = {
    "F1": "1/2",
    "F2": "1/2 + 1/2",
    "F3": "1/2 + 1/2 + 1/2",
    "F4": "1/2/4",
    "F5": "1/2/4 + 1/2/4",
    "F6": "1/2/4/8",
    "F7": "1/2/4/8/16",
}


# ==============================================================================
# MENU DE CONFIGURACAO INICIAL
# ==============================================================================

def selecionar_caixa_banca(console: Console) -> tuple:
    """Menu para configurar caixa (reserva) e banca (sessao)."""
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("CONFIGURACAO FINANCEIRA", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()
    console.print(
        "  Caixa = sua reserva total (ex: R$ 5.000)",
        style="dim",
    )
    console.print(
        "  Banca = valor alocado para apostas (ex: R$ 500)",
        style="dim",
    )
    console.print()

    # Caixa
    while True:
        try:
            caixa_input = console.input(
                "[green]Caixa (reserva total em R$): [/green]"
            )
            caixa = float(
                caixa_input.replace(",", ".").replace("R$", "").strip()
            )
            if caixa < 50:
                console.print("Minimo: R$ 50,00", style="red")
                continue
            break
        except ValueError:
            console.print("Digite um valor numerico valido!", style="red")

    # Banca
    sugestao = min(caixa, round(caixa / 10, 2)) if caixa >= 500 else caixa
    console.print()
    console.print(
        f"  Sugestao: R$ {sugestao:.2f} "
        f"({caixa / sugestao:.0f} bancas de reserva)",
        style="dim",
    )

    while True:
        try:
            banca_input = console.input(
                "[green]Banca (valor para apostas em R$): [/green]"
            )
            banca = float(
                banca_input.replace(",", ".").replace("R$", "").strip()
            )
            if banca < 31:
                console.print(
                    "Minimo: R$ 31,00 (para suportar todos os setups)",
                    style="red",
                )
                continue
            if banca > caixa:
                console.print(
                    f"Banca nao pode exceder o caixa (R$ {caixa:.2f})",
                    style="red",
                )
                continue
            break
        except ValueError:
            console.print("Digite um valor numerico valido!", style="red")

    n_bancas = caixa / banca
    console.print()
    console.print(
        f"  Caixa: R$ {caixa:.2f} | "
        f"Banca: R$ {banca:.2f} | "
        f"{n_bancas:.1f} bancas de reserva",
        style="green",
    )

    return caixa, banca


def selecionar_setup(console: Console, banca: float) -> BaseSetup:
    """Menu para escolher o setup de jogo."""
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("SETUP DE JOGO", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()

    opcoes = [
        ("1", "1/2", "Conservador", f"banca/3, 2 dobras, unit=R${banca/3:.2f}"),
        ("2", "1/2 + 1/2", "Moderado", f"banca/6, 4 dobras, unit=R${banca/6:.2f}"),
        ("3", "1/2 + 1/2 + 1/2", "Resistente", f"banca/9, 6 dobras, unit=R${banca/9:.2f}"),
        ("4", "1/2/4", "Equilibrado", f"banca/7, 3 dobras, unit=R${banca/7:.2f}"),
        ("5", "1/2/4 + 1/2/4", "Duplo", f"banca/14, 6 dobras, unit=R${banca/14:.2f}"),
        ("6", "1/2/4/8", "Agressivo", f"banca/15, 4 dobras, unit=R${banca/15:.2f}"),
        ("7", "1/2/4/8/16", "Ultra", f"banca/31, 5 dobras, unit=R${banca/31:.2f}"),
    ]

    for num, nome, tipo, desc in opcoes:
        console.print(f"  [{num}] {nome:20s} ({tipo})", style="white")
        console.print(f"      {desc}", style="dim")

    console.print()

    while True:
        try:
            choice = console.input(
                "[green]Escolha o setup (1-7): [/green]"
            ).strip()
            idx = int(choice) - 1
            if 0 <= idx < len(SETUP_LIST):
                setup_name = SETUP_LIST[idx]
                setup = get_setup(setup_name)

                # Validar unit >= 1.0
                unit = setup.calculate_unit(banca)
                if unit < 1.0:
                    console.print(
                        f"Banca muito baixa para este setup "
                        f"(unit=R${unit:.2f}, minimo R$1.00)",
                        style="red",
                    )
                    continue

                console.print(
                    f"\n  Setup: {setup.get_description()}",
                    style="green",
                )
                return setup

            console.print("Opcao invalida. Digite 1-7.", style="red")
        except (ValueError, IndexError):
            console.print("Opcao invalida.", style="red")


def selecionar_meta(console: Console, banca: float) -> int:
    """Menu para escolher a meta de lucro."""
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("META DE LUCRO", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()

    for i, pct in enumerate(METAS_DISPONIVEIS):
        valor = banca * pct / 100
        label = chr(65 + i)  # A, B, C, D, E, F
        console.print(
            f"  [{label}] {pct:>3d}%  ->  "
            f"R$ {valor:.2f}  (saque em R$ {banca + valor:.2f})",
            style="white",
        )

    console.print()
    mapa = {chr(65 + i): pct for i, pct in enumerate(METAS_DISPONIVEIS)}

    while True:
        choice = console.input(
            "[green]Escolha a meta (A-F): [/green]"
        ).strip().upper()
        if choice in mapa:
            pct = mapa[choice]
            valor = banca * pct / 100
            console.print(
                f"\n  Meta: {pct}% (R$ {valor:.2f} de lucro)",
                style="green",
            )
            return pct
        console.print("Opcao invalida. Digite A-F.", style="red")


def selecionar_horario(console: Console) -> bool:
    """Menu para escolher modo de horario."""
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("HORARIOS DE OPERACAO", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()
    console.print(
        "  [P] Premium apenas  (opera so em horarios favoraveis)",
        style="white",
    )
    console.print(
        "  [T] 24/7            (opera em todos os horarios)",
        style="white",
    )
    console.print()

    while True:
        choice = console.input(
            "[green]Escolha (P/T): [/green]"
        ).strip().upper()
        if choice == "P":
            console.print(
                "\n  Modo: PREMIUM (horarios favoraveis)", style="green"
            )
            return True
        if choice in ("T", ""):
            console.print(
                "\n  Modo: 24/7 (todos os horarios)", style="green"
            )
            return False
        console.print("Opcao invalida. Digite P ou T.", style="red")


def exibir_resumo_config(
    console: Console,
    caixa: float,
    banca: float,
    setup: BaseSetup,
    meta_pct: int,
    premium_only: bool,
) -> bool:
    """Exibe resumo da configuracao antes de iniciar."""
    console.print()
    console.print("=" * 55, style="yellow")
    console.print("RESUMO DA CONFIGURACAO", style="bold yellow")
    console.print("=" * 55, style="yellow")
    console.print()

    n_bancas = caixa / banca
    meta_valor = banca * meta_pct / 100
    horario_str = "PREMIUM (horarios favoraveis)" if premium_only else "24/7"

    console.print(f"  Caixa:      R$ {caixa:.2f}", style="white")
    console.print(
        f"  Banca:      R$ {banca:.2f} ({n_bancas:.1f} bancas)",
        style="white",
    )
    console.print(f"  Setup:      {setup.get_description()}", style="white")
    console.print(
        f"  Meta:       {meta_pct}% (R$ {meta_valor:.2f})", style="white"
    )
    console.print(f"  Horarios:   {horario_str}", style="white")
    console.print()

    # Tabela de apostas por ciclo
    bets = setup.get_bets_by_cycle(banca)
    table = Table(
        title="Tabela de Apostas",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Ciclo", style="cyan", justify="center")
    table.add_column("Dobra", style="cyan", justify="center")
    table.add_column("Valor", justify="right", style="green")
    table.add_column("Baixas", justify="center", style="dim")

    current_cycle = 0
    for bet in bets:
        cycle_str = ""
        if bet["cycle"] != current_cycle:
            current_cycle = bet["cycle"]
            cycle_str = f"Ciclo {current_cycle}"

        table.add_row(
            cycle_str,
            f"D{bet['pos_in_cycle']} ({bet['multiplier']}x)",
            f"R$ {bet['value']:.2f}",
            f"{bet['baixas']}+",
        )

    total_risco = sum(b["value"] for b in bets)
    table.add_row("", "", "", "")
    table.add_row("", "TOTAL RISCO", f"R$ {total_risco:.2f}", "")

    console.print(table)
    console.print()

    confirma = console.input(
        "[cyan]Confirma? (S/n): [/cyan]"
    ).strip().lower()
    return confirma in ("", "s", "sim", "y", "yes")


def menu_configuracao_completo(console: Console) -> dict:
    """
    Fluxo completo de configuracao inicial.
    Retorna dict com caixa, banca, setup, meta_pct, premium_only.
    """
    while True:
        caixa, banca = selecionar_caixa_banca(console)
        setup = selecionar_setup(console, banca)
        meta_pct = selecionar_meta(console, banca)
        premium_only = selecionar_horario(console)

        if exibir_resumo_config(
            console, caixa, banca, setup, meta_pct, premium_only
        ):
            return {
                "caixa": caixa,
                "banca": banca,
                "setup": setup,
                "meta_pct": meta_pct,
                "premium_only": premium_only,
            }

        console.print("\nReconfigurando...\n", style="yellow")


# ==============================================================================
# HOT-SWAP KEYBOARD LISTENER
# ==============================================================================

class HotKeyListener:
    """
    Listener de teclas de atalho em thread separada (Windows).
    Usa msvcrt.kbhit/getch para capturar F1-F10 sem bloquear.

    F1-F7: troca de setup
    F8: ciclar meta
    F9: pausar/retomar
    F10: encerrar
    """

    def __init__(
        self,
        on_setup_change: Callable[[str], None],
        on_meta_cycle: Callable[[], None],
        on_pause: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.on_setup_change = on_setup_change
        self.on_meta_cycle = on_meta_cycle
        self.on_pause = on_pause
        self.on_stop = on_stop

        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia o listener em thread daemon."""
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True
        )
        self._thread.start()
        logger.info("HotKeyListener iniciado (F1-F10)")

    def stop(self):
        """Para o listener."""
        self._running = False

    def _listen_loop(self):
        """Loop principal de escuta de teclas."""
        while self._running:
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getch()

                    # Teclas de funcao sao precedidas por \x00 ou \xe0
                    if key in (b'\x00', b'\xe0'):
                        key2 = msvcrt.getch()
                        code = ord(key2)
                        fkey = FKEY_MAP.get(code)

                        if fkey:
                            self._handle_fkey(fkey)

                time.sleep(0.05)  # 50ms polling
            except Exception as e:
                logger.error(f"Erro no HotKeyListener: {e}")
                time.sleep(0.5)

    def _handle_fkey(self, fkey: str):
        """Processa tecla de funcao."""
        logger.info(f"Tecla pressionada: {fkey}")

        # F1-F7: troca de setup
        setup_name = FKEY_SETUP_MAP.get(fkey)
        if setup_name:
            self.on_setup_change(setup_name)
            return

        if fkey == "F8":
            self.on_meta_cycle()
        elif fkey == "F9":
            self.on_pause()
        elif fkey == "F10":
            self.on_stop()
