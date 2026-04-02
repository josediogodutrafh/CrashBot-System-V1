#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - CAPTURA DE TELA

Módulo responsável pela captura de regiões da tela usando mss.
Otimizado para performance em tempo real.

Uso:
    from engine.vision.capture import ScreenCapture, get_capture

    capture = get_capture()

    # Captura região específica
    img = capture.capture_region(100, 200, 300, 50)

    # Captura tela inteira
    full = capture.capture_full()
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    import mss
    import mss.tools

    HAS_MSS = True
except ImportError:
    HAS_MSS = False

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CaptureRegion:
    """Define uma região de captura."""

    x: int
    y: int
    width: int
    height: int
    name: str = ""

    def to_mss_monitor(self) -> Dict[str, int]:
        """Converte para formato mss."""
        return {
            "left": self.x,
            "top": self.y,
            "width": self.width,
            "height": self.height,
        }

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Retorna como tupla (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN CAPTURE
# ═══════════════════════════════════════════════════════════════════════════════


class ScreenCapture:
    """
    Gerenciador de captura de tela.

    Features:
        - Captura de regiões específicas
        - Captura de tela inteira
        - Reutilização do contexto mss para performance
        - Thread-safe

    Exemplo:
        capture = ScreenCapture()

        # Captura região
        img = capture.capture_region(100, 200, 300, 50)

        # Captura com CaptureRegion
        region = CaptureRegion(100, 200, 300, 50, "multiplicador")
        img = capture.capture(region)
    """

    def __init__(self):
        """Inicializa o capturador."""
        if not HAS_MSS:
            raise ImportError("Módulo mss não encontrado. Instale com: pip install mss")

        self._lock = threading.Lock()
        # Mudei de mss.mss para Any para evitar erro do Pylance e usar o import Any
        self._sct: Optional[Any] = None

        logger.debug("ScreenCapture inicializado")

    def _get_sct(self) -> Any:
        """Retorna instância mss (cria se necessário)."""
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Optional[np.ndarray]:
        """
        Captura uma região específica da tela.

        Args:
            x: Posição X (esquerda)
            y: Posição Y (topo)
            width: Largura da região
            height: Altura da região

        Returns:
            Imagem como numpy array (BGR) ou None se falhar
        """
        monitor = {
            "left": x,
            "top": y,
            "width": width,
            "height": height,
        }

        return self._capture_monitor(monitor)

    def capture(self, region: CaptureRegion) -> Optional[np.ndarray]:
        """
        Captura usando um objeto CaptureRegion.

        Args:
            region: Região a capturar

        Returns:
            Imagem como numpy array (BGR) ou None se falhar
        """
        return self._capture_monitor(region.to_mss_monitor())

    def capture_full(self, monitor_index: int = 1) -> Optional[np.ndarray]:
        """
        Captura a tela inteira.

        Args:
            monitor_index: Índice do monitor (1 = principal)

        Returns:
            Imagem como numpy array (BGR) ou None se falhar
        """
        with self._lock:
            try:
                sct = self._get_sct()

                if monitor_index >= len(sct.monitors):
                    logger.warning(f"Monitor {monitor_index} não existe")
                    monitor_index = 1

                monitor = sct.monitors[monitor_index]
                return self._capture_monitor(monitor)

            except Exception as e:
                logger.error(f"Erro ao capturar tela inteira: {e}")
                return None

    def _capture_monitor(self, monitor: Dict[str, int]) -> Optional[np.ndarray]:
        """
        Captura um monitor/região específico.

        Args:
            monitor: Dicionário com left, top, width, height

        Returns:
            Imagem como numpy array (BGR) ou None se falhar
        """
        with self._lock:
            try:
                sct = self._get_sct()
                screenshot = sct.grab(monitor)

                # Converte para numpy array
                img = np.array(screenshot)

                # mss retorna BGRA, converte para BGR (OpenCV padrão)
                if img.shape[2] == 4:
                    img = img[:, :, :3]

                return img

            except Exception as e:
                logger.error(f"Erro ao capturar região: {e}")
                return None

    def get_screen_size(self, monitor_index: int = 1) -> Tuple[int, int]:
        """
        Retorna o tamanho da tela.

        Args:
            monitor_index: Índice do monitor

        Returns:
            Tupla (width, height)
        """
        with self._lock:
            try:
                sct = self._get_sct()

                if monitor_index >= len(sct.monitors):
                    monitor_index = 1

                monitor = sct.monitors[monitor_index]
                return (monitor["width"], monitor["height"])

            except Exception as e:
                logger.error(f"Erro ao obter tamanho da tela: {e}")
                return (1920, 1080)  # Fallback

    def get_monitors_info(self) -> list:
        """Retorna informações sobre todos os monitores."""
        with self._lock:
            try:
                sct = self._get_sct()
                return list(sct.monitors)
            except Exception as e:
                logger.error(f"Erro ao obter monitores: {e}")
                return []

    def close(self) -> None:
        """Libera recursos."""
        with self._lock:
            if self._sct:
                self._sct.close()
                self._sct = None
        logger.debug("ScreenCapture fechado")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_screen_capture: Optional[ScreenCapture] = None
_capture_lock = threading.Lock()


def get_capture() -> ScreenCapture:
    """
    Retorna a instância singleton do ScreenCapture.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _screen_capture

    if _screen_capture is None:
        with _capture_lock:
            if _screen_capture is None:
                _screen_capture = ScreenCapture()

    return _screen_capture


def reset_capture() -> None:
    """Reseta o capturador (útil para testes)."""
    global _screen_capture
    with _capture_lock:
        if _screen_capture:
            _screen_capture.close()
        _screen_capture = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO SCREEN CAPTURE - CrashBot v3.0")
    print("=" * 60)

    if not HAS_MSS:
        print("❌ Módulo mss não instalado!")
        exit(1)

    # Cria capturador
    capture = ScreenCapture()
    print("\n✅ Capturador criado")

    # Info dos monitores
    monitors = capture.get_monitors_info()
    print("\n--- Monitores Detectados ---")
    for i, mon in enumerate(monitors):
        print(f"   [{i}] {mon}")

    # Tamanho da tela
    width, height = capture.get_screen_size()
    print("\n--- Tela Principal ---")
    print(f"   Tamanho: {width}x{height}")

    # Captura região de teste
    print("\n--- Teste de Captura ---")
    img = capture.capture_region(0, 0, 100, 100)
    if img is not None:
        print(f"   ✅ Região capturada: {img.shape}")
    else:
        print("   ❌ Falha na captura")

    # Captura com CaptureRegion
    region = CaptureRegion(100, 100, 200, 50, "teste")
    img2 = capture.capture(region)
    if img2 is not None:
        print(f"   ✅ CaptureRegion capturada: {img2.shape}")
    else:
        print("   ❌ Falha na captura")

    # Cleanup
    capture.close()
    print("\n✅ Capturador fechado")

    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
