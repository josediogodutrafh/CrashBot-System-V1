#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false

"""
CRASHBOT v3.0 - REGION SELECTOR

Overlay transparente para seleção visual de regiões e pontos na tela.
Usa tkinter para criar janela transparente sobre o jogo.

Uso:
    from calibration.region_selector import RegionSelector, SelectionMode

    selector = RegionSelector()

    # Selecionar região (retângulo)
    result = selector.select_region("Selecione a área do SALDO")
    if result:
        print(f"Região: {result.x}, {result.y}, {result.width}, {result.height}")

    # Selecionar ponto (clique)
    result = selector.select_point("Clique no BOTÃO DE APOSTA")
    if result:
        print(f"Ponto: {result.x}, {result.y}")
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional, Tuple

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class SelectionMode(Enum):
    """Modo de seleção."""

    REGION = auto()  # Seleção de retângulo (arrastar)
    POINT = auto()  # Seleção de ponto (clique único)


@dataclass
class SelectionResult:
    """Resultado de uma seleção."""

    success: bool
    mode: SelectionMode
    x: int = 0
    y: int = 0
    width: int = 0  # Só para REGION
    height: int = 0  # Só para REGION

    def to_region_tuple(self) -> Tuple[int, int, int, int]:
        """Retorna como tupla de região (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    def to_point_tuple(self) -> Tuple[int, int]:
        """Retorna como tupla de ponto (x, y)."""
        return (self.x, self.y)


# ═══════════════════════════════════════════════════════════════════════════════
# REGION SELECTOR
# ═══════════════════════════════════════════════════════════════════════════════


class RegionSelector:
    """
    Seletor de regiões e pontos na tela.

    Cria um overlay transparente sobre toda a tela onde o usuário
    pode desenhar retângulos ou clicar em pontos.

    Exemplo:
        selector = RegionSelector()

        # Modo região (arrastar retângulo)
        result = selector.select_region("Selecione o SALDO")

        # Modo ponto (clique único)
        result = selector.select_point("Clique no BOTÃO")
    """

    # Cores do overlay
    OVERLAY_COLOR = "#000001"  # Quase preto (para transparência)
    SELECTION_COLOR = "#00FF00"  # Verde para seleção
    GUIDE_COLOR = "#FFFF00"  # Amarelo para guias
    TEXT_COLOR = "#FFFFFF"  # Branco para texto
    CROSSHAIR_COLOR = "#FF0000"  # Vermelho para mira

    def __init__(self):
        """Inicializa o seletor."""
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None

        # Estado da seleção
        self._mode = SelectionMode.REGION
        self._instruction = ""
        self._start_x = 0
        self._start_y = 0
        self._current_rect: Optional[int] = None
        self._result: Optional[SelectionResult] = None
        self._selection_complete = False

        # Callbacks
        self._on_complete: Optional[Callable[[SelectionResult], None]] = None

        logger.debug("RegionSelector inicializado")

    def select_region(
        self,
        instruction: str = "Arraste para selecionar a região",
        on_complete: Optional[Callable[[SelectionResult], None]] = None,
    ) -> Optional[SelectionResult]:
        """
        Inicia seleção de região (retângulo).

        Args:
            instruction: Texto de instrução exibido
            on_complete: Callback chamado ao completar

        Returns:
            SelectionResult ou None se cancelado
        """
        self._mode = SelectionMode.REGION
        self._instruction = instruction
        self._on_complete = on_complete

        return self._run_selection()

    def select_point(
        self,
        instruction: str = "Clique para selecionar o ponto",
        on_complete: Optional[Callable[[SelectionResult], None]] = None,
    ) -> Optional[SelectionResult]:
        """
        Inicia seleção de ponto (clique único).

        Args:
            instruction: Texto de instrução exibido
            on_complete: Callback chamado ao completar

        Returns:
            SelectionResult ou None se cancelado
        """
        self._mode = SelectionMode.POINT
        self._instruction = instruction
        self._on_complete = on_complete

        return self._run_selection()

    def _run_selection(self) -> Optional[SelectionResult]:
        """Executa o loop de seleção."""
        self._result = None
        self._selection_complete = False

        try:
            # Cria janela
            self._create_overlay()

            # Inicia loop
            if self._root:
                self._root.mainloop()

            return self._result

        except Exception as e:
            logger.error(f"Erro na seleção: {e}")
            return None
        finally:
            self._cleanup()

    def _create_overlay(self) -> None:
        """Cria a janela de overlay transparente."""
        self._root = tk.Tk()
        self._root.title("CrashBot - Seletor")

        # Configurações da janela
        self._root.attributes("-fullscreen", True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.3)  # Semi-transparente

        # Tenta fazer o fundo transparente (Windows)
        try:
            self._root.attributes("-transparentcolor", self.OVERLAY_COLOR)
        except tk.TclError:
            pass  # Não suportado em algumas plataformas

        # Configuração para fechar com Escape
        self._root.bind("<Escape>", self._on_escape)

        # Canvas para desenho
        self._canvas = tk.Canvas(
            self._root,
            bg=self.OVERLAY_COLOR,
            highlightthickness=0,
            cursor="cross",
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Bindings baseados no modo
        if self._mode == SelectionMode.REGION:
            self._canvas.bind("<ButtonPress-1>", self._on_region_start)
            self._canvas.bind("<B1-Motion>", self._on_region_drag)
            self._canvas.bind("<ButtonRelease-1>", self._on_region_end)
        else:
            self._canvas.bind("<ButtonPress-1>", self._on_point_click)

        # Movimento do mouse para crosshair
        self._canvas.bind("<Motion>", self._on_mouse_move)

        # Desenha instruções
        self._draw_instructions()

        # Desenha crosshair inicial
        self._crosshair_h: Optional[int] = None
        self._crosshair_v: Optional[int] = None
        self._coord_text: Optional[int] = None

    def _draw_instructions(self) -> None:
        """Desenha as instruções na tela."""
        if not self._canvas:
            return

        # Fundo semi-transparente para texto
        screen_width = self._root.winfo_screenwidth() if self._root else 1920

        # Texto de instrução
        self._canvas.create_rectangle(
            0,
            0,
            screen_width,
            80,
            fill="#1a1a2e",
            outline="",
        )

        # Título
        mode_text = "REGIÃO" if self._mode == SelectionMode.REGION else "PONTO"
        self._canvas.create_text(
            screen_width // 2,
            25,
            text=f"🎯 CALIBRAÇÃO - SELECIONAR {mode_text}",
            font=("Segoe UI", 16, "bold"),
            fill=self.TEXT_COLOR,
        )

        # Instrução
        self._canvas.create_text(
            screen_width // 2,
            55,
            text=self._instruction,
            font=("Segoe UI", 12),
            fill=self.GUIDE_COLOR,
        )

        # Dica de ESC
        self._canvas.create_text(
            screen_width - 100,
            25,
            text="[ESC] Cancelar",
            font=("Segoe UI", 10),
            fill="#888888",
        )

        # Dica adicional baseada no modo
        if self._mode == SelectionMode.REGION:
            hint = "Clique e arraste para desenhar o retângulo"
        else:
            hint = "Clique no ponto desejado"

        self._canvas.create_text(
            screen_width - 150,
            55,
            text=hint,
            font=("Segoe UI", 9),
            fill="#666666",
        )

    def _on_mouse_move(self, event: tk.Event) -> None:  # type: ignore
        """Atualiza crosshair com movimento do mouse."""
        if not self._canvas:
            return

        # Remove crosshair antigo
        if self._crosshair_h:
            self._canvas.delete(self._crosshair_h)
        if self._crosshair_v:
            self._canvas.delete(self._crosshair_v)
        if self._coord_text:
            self._canvas.delete(self._coord_text)

        screen_width = self._root.winfo_screenwidth() if self._root else 1920
        screen_height = self._root.winfo_screenheight() if self._root else 1080

        # Linhas do crosshair
        self._crosshair_h = self._canvas.create_line(
            0,
            event.y,
            screen_width,
            event.y,
            fill=self.CROSSHAIR_COLOR,
            width=1,
            dash=(4, 4),
        )
        self._crosshair_v = self._canvas.create_line(
            event.x,
            80,
            event.x,
            screen_height,
            fill=self.CROSSHAIR_COLOR,
            width=1,
            dash=(4, 4),
        )

        # Texto com coordenadas
        self._coord_text = self._canvas.create_text(
            event.x + 15,
            event.y - 15,
            text=f"({event.x}, {event.y})",
            font=("Consolas", 10),
            fill=self.TEXT_COLOR,
            anchor="nw",
        )

    def _on_region_start(self, event: tk.Event) -> None:  # type: ignore
        """Início da seleção de região."""
        self._start_x = event.x
        self._start_y = event.y

        # Remove retângulo anterior se existir
        if self._current_rect:
            self._canvas.delete(self._current_rect)  # type: ignore

        # Cria novo retângulo
        self._current_rect = self._canvas.create_rectangle(  # type: ignore
            self._start_x,
            self._start_y,
            self._start_x,
            self._start_y,
            outline=self.SELECTION_COLOR,
            width=2,
            dash=(6, 4),
        )

    def _on_region_drag(self, event: tk.Event) -> None:  # type: ignore
        """Arraste durante seleção de região."""
        if self._current_rect and self._canvas:
            self._canvas.coords(
                self._current_rect,
                self._start_x,
                self._start_y,
                event.x,
                event.y,
            )

    def _on_region_end(self, event: tk.Event) -> None:  # type: ignore
        """Fim da seleção de região."""
        # Calcula dimensões (garante valores positivos)
        x = min(self._start_x, event.x)
        y = min(self._start_y, event.y)
        width = abs(event.x - self._start_x)
        height = abs(event.y - self._start_y)

        # Valida tamanho mínimo
        if width < 10 or height < 10:
            logger.warning("Região muito pequena, tente novamente")
            if self._current_rect and self._canvas:
                self._canvas.delete(self._current_rect)
            self._current_rect = None
            return

        # Cria resultado
        self._result = SelectionResult(
            success=True,
            mode=SelectionMode.REGION,
            x=x,
            y=y,
            width=width,
            height=height,
        )

        logger.info(f"Região selecionada: ({x}, {y}) {width}x{height}")

        # Callback
        if self._on_complete:
            self._on_complete(self._result)

        # Fecha
        self._selection_complete = True
        if self._root:
            self._root.quit()

    def _on_point_click(self, event: tk.Event) -> None:  # type: ignore
        """Clique para seleção de ponto."""
        # Cria resultado
        self._result = SelectionResult(
            success=True,
            mode=SelectionMode.POINT,
            x=event.x,
            y=event.y,
        )

        logger.info(f"Ponto selecionado: ({event.x}, {event.y})")

        # Desenha marcador no ponto
        if self._canvas:
            # Círculo
            self._canvas.create_oval(
                event.x - 10,
                event.y - 10,
                event.x + 10,
                event.y + 10,
                outline=self.SELECTION_COLOR,
                width=3,
            )
            # Cruz
            self._canvas.create_line(
                event.x - 15,
                event.y,
                event.x + 15,
                event.y,
                fill=self.SELECTION_COLOR,
                width=2,
            )
            self._canvas.create_line(
                event.x,
                event.y - 15,
                event.x,
                event.y + 15,
                fill=self.SELECTION_COLOR,
                width=2,
            )

            # Atualiza para mostrar o marcador
            self._canvas.update()

        # Callback
        if self._on_complete:
            self._on_complete(self._result)

        # Pequeno delay para ver o marcador
        if self._root:
            self._root.after(300, self._root.quit)

    def _on_escape(self, event: tk.Event) -> None:  # type: ignore
        """Cancela a seleção com ESC."""
        logger.info("Seleção cancelada pelo usuário")
        self._result = SelectionResult(success=False, mode=self._mode)

        if self._root:
            self._root.quit()

    def _cleanup(self) -> None:
        """Limpa recursos da janela."""
        try:
            if self._root:
                self._root.destroy()
        except Exception:
            pass
        finally:
            self._root = None
            self._canvas = None
            self._current_rect = None


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def quick_select_region(
    instruction: str = "Selecione a região",
) -> Optional[Tuple[int, int, int, int]]:
    """
    Função rápida para selecionar uma região.

    Args:
        instruction: Texto de instrução

    Returns:
        Tupla (x, y, width, height) ou None
    """
    selector = RegionSelector()
    result = selector.select_region(instruction)

    if result and result.success:
        return result.to_region_tuple()

    return None


def quick_select_point(
    instruction: str = "Selecione o ponto",
) -> Optional[Tuple[int, int]]:
    """
    Função rápida para selecionar um ponto.

    Args:
        instruction: Texto de instrução

    Returns:
        Tupla (x, y) ou None
    """
    selector = RegionSelector()
    result = selector.select_point(instruction)

    if result and result.success:
        return result.to_point_tuple()

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO REGION SELECTOR - CrashBot v3.0")
    print("=" * 60)

    print("\n1. Testando seleção de REGIÃO...")
    print("   (Arraste um retângulo na tela ou pressione ESC)")

    region = quick_select_region("Selecione uma área qualquer para teste")

    if region:
        print(f"\n   ✅ Região selecionada:")
        print(f"      X: {region[0]}")
        print(f"      Y: {region[1]}")
        print(f"      Width: {region[2]}")
        print(f"      Height: {region[3]}")
    else:
        print("\n   ⚠️ Seleção cancelada")

    print("\n2. Testando seleção de PONTO...")
    print("   (Clique em um ponto na tela ou pressione ESC)")

    point = quick_select_point("Clique em um ponto para teste")

    if point:
        print(f"\n   ✅ Ponto selecionado:")
        print(f"      X: {point[0]}")
        print(f"      Y: {point[1]}")
    else:
        print("\n   ⚠️ Seleção cancelada")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
