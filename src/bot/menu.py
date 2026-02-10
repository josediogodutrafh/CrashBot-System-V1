#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MENU INTERATIVO + HOT-SWAP
===========================

Menu de configuracao inicial (caixa, banca, setup, meta, horarios)
e listener de teclado para hot-swap em tempo real.

Teclas de atalho (durante execucao):
  F1  -> Conservador (1/2)
  F2  -> Moderado (1/2 + 1/2)
  F3  -> Resistente (1/2 + 1/2 + 1/2)
  F4  -> Equilibrado (1/2/4)
  F5  -> Duplo (1/2/4 + 1/2/4)
  F6  -> Agressivo (1/2/4/8)
  F7  -> Ultra (1/2/4/8/16)
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
    SETUP_DISPLAY_NAMES,
    BaseSetup,
    get_display_name,
    get_setup,
)

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
    console.print("ESTRATEGIA DE JOGO", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()

    opcoes = [
        ("1", "1/2", "Conservador",
         f"aposta inicial = 1/3 da banca (R${banca/3:.2f}), 2 dobras"),
        ("2", "1/2 + 1/2", "Moderado",
         f"aposta inicial = 1/6 da banca (R${banca/6:.2f}), 4 dobras em 2 ciclos"),
        ("3", "1/2 + 1/2 + 1/2", "Resistente",
         f"aposta inicial = 1/9 da banca (R${banca/9:.2f}), 6 dobras em 3 ciclos"),
        ("4", "1/2/4", "Equilibrado",
         f"aposta inicial = 1/7 da banca (R${banca/7:.2f}), 3 dobras"),
        ("5", "1/2/4 + 1/2/4", "Duplo",
         f"aposta inicial = 1/14 da banca (R${banca/14:.2f}), 6 dobras em 2 ciclos"),
        ("6", "1/2/4/8", "Agressivo",
         f"aposta inicial = 1/15 da banca (R${banca/15:.2f}), 4 dobras"),
        ("7", "1/2/4/8/16", "Ultra",
         f"aposta inicial = 1/31 da banca (R${banca/31:.2f}), 5 dobras"),
    ]

    for num, seq, nome, desc in opcoes:
        console.print(f"  [{num}] {nome:14s} ({seq})", style="white")
        console.print(f"      {desc}", style="dim")

    console.print()

    while True:
        try:
            choice = console.input(
                "[green]Escolha a estrategia (1-7): [/green]"
            ).strip()
            idx = int(choice) - 1
            if 0 <= idx < len(SETUP_LIST):
                setup_name = SETUP_LIST[idx]
                setup = get_setup(setup_name)
                display = get_display_name(setup_name)

                # Validar unit >= 1.0
                unit = setup.calculate_unit(banca)
                if unit < 1.0:
                    console.print(
                        f"Banca muito baixa para este setup "
                        f"(aposta base=R${unit:.2f}, minimo R$1.00)",
                        style="red",
                    )
                    continue

                console.print(
                    f"\n  Estrategia: {display} ({setup.name})",
                    style="green",
                )
                return setup

            console.print("Opcao invalida. Digite 1-7.", style="red")
        except (ValueError, IndexError):
            console.print("Opcao invalida.", style="red")


def _input_percentual(
    console: Console, prompt: str, max_val: float = 500,
) -> float:
    """Helper: le um percentual numerico do usuario."""
    while True:
        try:
            raw = console.input(prompt).strip()
            raw = raw.replace(",", ".").replace("%", "")
            val = float(raw)
            if val <= 0:
                console.print("Deve ser maior que 0.", style="red")
                continue
            if val > max_val:
                console.print(f"Maximo: {max_val:.0f}%.", style="red")
                continue
            return val
        except ValueError:
            console.print("Digite um valor numerico valido!", style="red")


def _input_horas(console: Console, prompt: str, max_val: float = 24) -> float:
    """Helper: le horas do usuario (0 = sem limite)."""
    while True:
        try:
            raw = console.input(prompt).strip().replace(",", ".")
            val = float(raw)
            if val < 0:
                console.print("Nao pode ser negativo.", style="red")
                continue
            if val > max_val:
                console.print(f"Maximo: {max_val:.0f} horas.", style="red")
                continue
            return val
        except ValueError:
            console.print("Digite um valor numerico valido!", style="red")


def selecionar_meta(console: Console, caixa: float, banca: float) -> dict:
    """Menu para configurar meta, stop loss, duracao e acoes."""

    # ══════════════════════════════════════════════════════════════
    # 1. STOP GAIN (meta de lucro % do CAIXA)
    # ══════════════════════════════════════════════════════════════
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("META DE LUCRO (STOP GAIN)", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()
    console.print(
        f"  Percentual de lucro em relacao ao caixa (R$ {caixa:.2f})",
        style="dim",
    )
    console.print(
        f"  Ex: 10 = meta de R$ {caixa * 10 / 100:.2f} de lucro",
        style="dim",
    )
    console.print()

    stop_gain = _input_percentual(
        console, "[green]Meta de lucro (% do caixa): [/green]"
    )
    gain_valor = caixa * stop_gain / 100
    console.print(
        f"\n  Stop Gain: {stop_gain:.1f}% do caixa "
        f"(R$ {gain_valor:.2f} de lucro)",
        style="green",
    )

    # Acao ao atingir stop gain
    console.print()
    console.print("  O que fazer ao atingir o stop gain?", style="dim")
    console.print("  [1] Encerrar sessao", style="white")
    console.print(
        "  [2] Suspender apostas por X horas e retomar", style="white"
    )
    console.print(
        "  [3] Reinvestir X% do lucro e continuar", style="white"
    )
    console.print()

    gain_action = "encerrar"
    gain_suspend_hours = 0.0
    gain_reinvest_pct = 0.0

    while True:
        choice = console.input(
            "[green]Acao stop gain (1-3): [/green]"
        ).strip()
        if choice == "1":
            gain_action = "encerrar"
            console.print("  Acao: encerrar sessao", style="green")
            break
        elif choice == "2":
            gain_action = "suspender"
            gain_suspend_hours = _input_horas(
                console,
                "[green]Suspender por quantas horas? [/green]",
            )
            console.print(
                f"  Acao: suspender {gain_suspend_hours:.1f}h e retomar",
                style="green",
            )
            break
        elif choice == "3":
            gain_action = "reinvestir"
            console.print(
                "  Qual % do lucro reinvestir na proxima sessao?",
                style="dim",
            )
            gain_reinvest_pct = _input_percentual(
                console,
                "[green]Reinvestir (% do lucro): [/green]",
                max_val=100,
            )
            console.print(
                f"  Acao: reinvestir {gain_reinvest_pct:.0f}% do lucro",
                style="green",
            )
            break
        console.print("Opcao invalida. Digite 1, 2 ou 3.", style="red")

    # ══════════════════════════════════════════════════════════════
    # 2. STOP LOSS (perda maxima % do CAIXA)
    # ══════════════════════════════════════════════════════════════
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("PERDA MAXIMA (STOP LOSS)", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()
    console.print(
        f"  Percentual maximo de perda do caixa (R$ {caixa:.2f})",
        style="dim",
    )
    console.print(
        f"  Ex: 50 = para se perder R$ {caixa * 50 / 100:.2f}",
        style="dim",
    )
    console.print()

    stop_loss = _input_percentual(
        console, "[green]Stop loss (% do caixa): [/green]", max_val=100,
    )
    loss_valor = caixa * stop_loss / 100
    console.print(
        f"\n  Stop Loss: {stop_loss:.1f}% do caixa "
        f"(para se perder R$ {loss_valor:.2f})",
        style="green",
    )

    # Acao ao atingir stop loss
    console.print()
    console.print("  O que fazer ao atingir o stop loss?", style="dim")
    console.print("  [1] Encerrar sessao", style="white")
    console.print(
        "  [2] Suspender apostas por X horas e retomar", style="white"
    )
    console.print()

    loss_action = "encerrar"
    loss_suspend_hours = 0.0

    while True:
        choice = console.input(
            "[green]Acao stop loss (1-2): [/green]"
        ).strip()
        if choice == "1":
            loss_action = "encerrar"
            console.print("  Acao: encerrar sessao", style="green")
            break
        elif choice == "2":
            loss_action = "suspender"
            loss_suspend_hours = _input_horas(
                console,
                "[green]Suspender por quantas horas? [/green]",
            )
            console.print(
                f"  Acao: suspender {loss_suspend_hours:.1f}h e retomar",
                style="green",
            )
            break
        console.print("Opcao invalida. Digite 1 ou 2.", style="red")

    # ══════════════════════════════════════════════════════════════
    # 3. DURACAO DA SESSAO
    # ══════════════════════════════════════════════════════════════
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("DURACAO DA SESSAO", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()
    console.print(
        "  Quantas horas o sistema deve jogar?",
        style="dim",
    )
    console.print(
        "  Digite 0 para sem limite (encerre manualmente com F10).",
        style="dim",
    )
    console.print()

    horas = _input_horas(
        console, "[green]Duracao em horas (0 = sem limite): [/green]",
    )
    if horas == 0:
        console.print(
            "\n  Duracao: sem limite (encerre com F10)", style="green"
        )
    else:
        console.print(f"\n  Duracao: {horas:.1f} horas", style="green")

    return {
        "stop_gain_pct": stop_gain,
        "gain_action": gain_action,
        "gain_suspend_hours": gain_suspend_hours,
        "gain_reinvest_pct": gain_reinvest_pct,
        "stop_loss_pct": stop_loss,
        "loss_action": loss_action,
        "loss_suspend_hours": loss_suspend_hours,
        "session_hours": horas,
    }


def selecionar_horario(console: Console) -> bool:
    """Menu para escolher modo de horario."""
    console.print()
    console.print("=" * 55, style="cyan")
    console.print("HORARIOS DE OPERACAO", style="bold cyan")
    console.print("=" * 55, style="cyan")
    console.print()
    console.print(
        "  [1] Apenas horarios recomendados",
        style="white",
    )
    console.print(
        "  [2] Todos os horarios",
        style="white",
    )
    console.print()

    while True:
        choice = console.input(
            "[green]Escolha (1/2): [/green]"
        ).strip()
        if choice == "1":
            console.print(
                "\n  Modo: apenas horarios recomendados", style="green"
            )
            return True
        if choice in ("2", ""):
            console.print(
                "\n  Modo: todos os horarios", style="green"
            )
            return False
        console.print("Opcao invalida. Digite 1 ou 2.", style="red")


def exibir_resumo_config(
    console: Console,
    caixa: float,
    banca: float,
    setup: BaseSetup,
    meta_config: dict,
    premium_only: bool,
) -> bool:
    """Exibe resumo da configuracao antes de iniciar."""
    console.print()
    console.print("=" * 55, style="yellow")
    console.print("RESUMO DA CONFIGURACAO", style="bold yellow")
    console.print("=" * 55, style="yellow")
    console.print()

    n_bancas = caixa / banca
    stop_gain = meta_config["stop_gain_pct"]
    stop_loss = meta_config["stop_loss_pct"]
    session_hours = meta_config["session_hours"]
    gain_valor = caixa * stop_gain / 100
    loss_valor = caixa * stop_loss / 100
    horario_str = (
        "Apenas horarios recomendados" if premium_only
        else "Todos os horarios"
    )
    duracao_str = (
        f"{session_hours:.1f}h" if session_hours > 0 else "sem limite"
    )

    # Descricao das acoes
    gain_act = meta_config.get("gain_action", "encerrar")
    if gain_act == "suspender":
        gain_act_str = (
            f"suspender {meta_config.get('gain_suspend_hours', 0):.1f}h"
        )
    elif gain_act == "reinvestir":
        gain_act_str = (
            f"reinvestir {meta_config.get('gain_reinvest_pct', 0):.0f}%"
        )
    else:
        gain_act_str = "encerrar"

    loss_act = meta_config.get("loss_action", "encerrar")
    if loss_act == "suspender":
        loss_act_str = (
            f"suspender {meta_config.get('loss_suspend_hours', 0):.1f}h"
        )
    else:
        loss_act_str = "encerrar"

    console.print(f"  Caixa:      R$ {caixa:.2f}", style="white")
    console.print(
        f"  Banca:      R$ {banca:.2f} ({n_bancas:.1f} bancas)",
        style="white",
    )
    display = get_display_name(setup.name)
    console.print(
        f"  Estrategia: {display} ({setup.name})", style="white"
    )
    console.print(
        f"  Stop Gain:  {stop_gain:.1f}% do caixa "
        f"(R$ {gain_valor:.2f}) -> {gain_act_str}",
        style="white",
    )
    console.print(
        f"  Stop Loss:  {stop_loss:.1f}% do caixa "
        f"(R$ {loss_valor:.2f}) -> {loss_act_str}",
        style="white",
    )
    console.print(f"  Duracao:    {duracao_str}", style="white")
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
    Retorna dict com caixa, banca, setup, meta config, premium_only.
    """
    while True:
        caixa, banca = selecionar_caixa_banca(console)
        setup = selecionar_setup(console, banca)
        meta_config = selecionar_meta(console, caixa, banca)
        premium_only = selecionar_horario(console)

        if exibir_resumo_config(
            console, caixa, banca, setup, meta_config, premium_only
        ):
            return {
                "caixa": caixa,
                "banca": banca,
                "setup": setup,
                "stop_gain_pct": meta_config["stop_gain_pct"],
                "gain_action": meta_config["gain_action"],
                "gain_suspend_hours": meta_config["gain_suspend_hours"],
                "gain_reinvest_pct": meta_config["gain_reinvest_pct"],
                "stop_loss_pct": meta_config["stop_loss_pct"],
                "loss_action": meta_config["loss_action"],
                "loss_suspend_hours": meta_config["loss_suspend_hours"],
                "session_hours": meta_config["session_hours"],
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
