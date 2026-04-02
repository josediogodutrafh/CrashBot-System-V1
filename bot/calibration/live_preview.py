#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false

"""
CRASHBOT v3.0 - LIVE PREVIEW

Preview em tempo real das leituras OCR e detecção de estados.
Valida se as regiões calibradas estão funcionando corretamente.

Uso:
    from calibration.live_preview import LivePreview, ReadingResult

    preview = LivePreview()

    # Testar leitura de uma região
    result = preview.test_region(region, "balance")
    print(f"Valor: {result.value}, Confiança: {result.confidence}")

    # Testar cor de um ponto
    color = preview.get_color_at(x, y)
    print(f"Cor: RGB({color[0]}, {color[1]}, {color[2]})")
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# Imports opcionais
try:
    import cv2

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None

try:
    import mss

    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    mss = None

try:
    import pytesseract

    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    pytesseract = None

# Imports internos
from calibration.profile_manager import (
    CalibrationProfile,
    ColorConfig,
    OCRConfig,
    RegionConfig,
)

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class ReadingStatus(Enum):
    """Status de uma leitura."""

    SUCCESS = auto()  # Leitura OK
    WARNING = auto()  # Leitura incerta
    ERROR = auto()  # Falha na leitura
    NOT_CONFIGURED = auto()  # Região não configurada


@dataclass
class ReadingResult:
    """Resultado de uma leitura."""

    status: ReadingStatus
    value: Any = None
    raw_text: str = ""
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    region_name: str = ""

    @property
    def is_success(self) -> bool:
        """Verifica se a leitura foi bem sucedida."""
        return self.status == ReadingStatus.SUCCESS

    @property
    def status_icon(self) -> str:
        """Retorna ícone do status."""
        icons = {
            ReadingStatus.SUCCESS: "✅",
            ReadingStatus.WARNING: "⚠️",
            ReadingStatus.ERROR: "❌",
            ReadingStatus.NOT_CONFIGURED: "⬜",
        }
        return icons.get(self.status, "❓")

    @property
    def status_color(self) -> Tuple[int, int, int, int]:
        """Retorna cor RGBA do status."""
        colors = {
            ReadingStatus.SUCCESS: (0, 200, 100, 255),
            ReadingStatus.WARNING: (255, 180, 0, 255),
            ReadingStatus.ERROR: (255, 70, 70, 255),
            ReadingStatus.NOT_CONFIGURED: (100, 100, 100, 255),
        }
        return colors.get(self.status, (150, 150, 150, 255))


@dataclass
class ButtonState:
    """Estado do botão de aposta."""

    is_bet_ready: bool = False  # Vermelho = pode apostar
    is_waiting: bool = False  # Verde = aguardando
    color: Tuple[int, int, int] = (0, 0, 0)
    confidence: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE PREVIEW
# ═══════════════════════════════════════════════════════════════════════════════


class LivePreview:
    """
    Sistema de preview em tempo real.

    Captura regiões da tela, executa OCR e valida leituras.
    Usado pelo calibrador para testar configurações.

    Exemplo:
        preview = LivePreview()

        # Testar região de saldo
        region = RegionConfig(x=650, y=105, width=80, height=25)
        result = preview.test_balance(region)

        if result.is_success:
            print(f"Saldo: R$ {result.value}")
    """

    def __init__(self):
        """Inicializa o preview."""
        self._sct: Optional[Any] = None
        self._lock = threading.Lock()

        # Verifica dependências
        if not HAS_MSS:
            logger.warning("mss não disponível - captura desabilitada")

        if not HAS_TESSERACT:
            logger.warning("pytesseract não disponível - OCR desabilitado")

        if not HAS_CV2:
            logger.warning("OpenCV não disponível - processamento limitado")

        logger.debug("LivePreview inicializado")

    def _get_sct(self) -> Optional[Any]:
        """Retorna instância do mss (lazy loading)."""
        if not HAS_MSS:
            return None

        if self._sct is None:
            self._sct = mss.mss()  # type: ignore

        return self._sct

    # ═══════════════════════════════════════════════════════════════════════════
    # CAPTURA DE TELA
    # ═══════════════════════════════════════════════════════════════════════════

    def capture_region(
        self,
        region: RegionConfig,
    ) -> Optional[np.ndarray]:
        """
        Captura uma região da tela.

        Args:
            region: Configuração da região

        Returns:
            Imagem como numpy array (BGR) ou None
        """
        sct = self._get_sct()
        if sct is None:
            return None

        try:
            monitor = {
                "left": region.x,
                "top": region.y,
                "width": region.width,
                "height": region.height,
            }

            with self._lock:
                screenshot = sct.grab(monitor)

            # Converte para numpy array
            img = np.array(screenshot)

            # Remove canal alpha e converte BGRA -> BGR
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)  # type: ignore

            return img

        except Exception as e:
            logger.error(f"Erro ao capturar região: {e}")
            return None

    def capture_full_screen(self) -> Optional[np.ndarray]:
        """
        Captura a tela inteira.

        Returns:
            Imagem como numpy array (BGR) ou None
        """
        sct = self._get_sct()
        if sct is None:
            return None

        try:
            with self._lock:
                screenshot = sct.grab(sct.monitors[1])  # Monitor principal

            img = np.array(screenshot)

            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)  # type: ignore

            return img

        except Exception as e:
            logger.error(f"Erro ao capturar tela: {e}")
            return None

    def get_color_at(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Obtém a cor em um ponto específico da tela.

        Args:
            x: Coordenada X
            y: Coordenada Y

        Returns:
            Tupla RGB
        """
        region = RegionConfig(x=x, y=y, width=1, height=1)
        img = self.capture_region(region)

        if img is None:
            return (0, 0, 0)

        # BGR -> RGB
        b, g, r = img[0, 0]
        return (int(r), int(g), int(b))

    def get_average_color(self, region: RegionConfig) -> Tuple[int, int, int]:
        """
        Obtém a cor média de uma região.

        Args:
            region: Configuração da região

        Returns:
            Tupla RGB média
        """
        img = self.capture_region(region)

        if img is None:
            return (0, 0, 0)

        # Calcula média de cada canal
        avg_color = np.mean(img, axis=(0, 1))

        # BGR -> RGB
        return (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))

    # ═══════════════════════════════════════════════════════════════════════════
    # OCR
    # ═══════════════════════════════════════════════════════════════════════════

    def _preprocess_image(
        self,
        img: np.ndarray,
        for_type: str = "numeric",
    ) -> np.ndarray:
        """
        Pré-processa imagem para OCR.

        Args:
            img: Imagem BGR
            for_type: Tipo de conteúdo ("numeric", "text", "timer")

        Returns:
            Imagem processada
        """
        if not HAS_CV2:
            return img

        # Converte para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # type: ignore

        # Redimensiona para melhor OCR (2x)
        height, width = gray.shape
        gray = cv2.resize(  # type: ignore
            gray,
            (width * 2, height * 2),
            interpolation=cv2.INTER_CUBIC,  # type: ignore
        )

        # Aplica threshold adaptativo
        if for_type == "numeric":
            # Para números, threshold mais agressivo
            _, thresh = cv2.threshold(  # type: ignore
                gray,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,  # type: ignore
            )
        elif for_type == "timer":
            # Timer tem fundo escuro, texto claro
            _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)  # type: ignore
        else:
            # Texto geral
            thresh = cv2.adaptiveThreshold(  # type: ignore
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # type: ignore
                cv2.THRESH_BINARY,  # type: ignore
                11,
                2,
            )

        # Remove ruído
        kernel = np.ones((2, 2), np.uint8)
        thresh = cv2.morphologyEx(  # type: ignore
            thresh,
            cv2.MORPH_CLOSE,  # type: ignore
            kernel,
        )

        return thresh

    def _run_ocr(
        self,
        img: np.ndarray,
        config: Optional[OCRConfig] = None,
    ) -> Tuple[str, float]:
        """
        Executa OCR em uma imagem.

        Args:
            img: Imagem processada
            config: Configuração do OCR

        Returns:
            Tupla (texto, confiança)
        """
        if not HAS_TESSERACT:
            return ("", 0.0)

        # Configuração padrão
        if config is None:
            config = OCRConfig()

        try:
            # Monta string de configuração
            tess_config = f"--psm {config.psm}"
            if config.whitelist:
                tess_config += f" -c tessedit_char_whitelist={config.whitelist}"

            # Executa OCR
            text = pytesseract.image_to_string(  # type: ignore
                img,
                config=tess_config,
            ).strip()

            # Tenta obter confiança
            try:
                data = pytesseract.image_to_data(  # type: ignore
                    img,
                    config=tess_config,
                    output_type=pytesseract.Output.DICT,  # type: ignore
                )
                confidences = [int(c) for c in data["conf"] if int(c) > 0]
                confidence = sum(confidences) / len(confidences) if confidences else 0.0
            except Exception:
                confidence = 50.0  # Valor padrão se não conseguir

            return (text, confidence / 100.0)

        except Exception as e:
            logger.error(f"Erro no OCR: {e}")
            return ("", 0.0)

    # ═══════════════════════════════════════════════════════════════════════════
    # LEITURAS ESPECÍFICAS
    # ═══════════════════════════════════════════════════════════════════════════

    def test_balance(
        self,
        region: RegionConfig,
        ocr_config: Optional[OCRConfig] = None,
    ) -> ReadingResult:
        """
        Testa leitura do saldo.

        Args:
            region: Região do saldo
            ocr_config: Configuração OCR

        Returns:
            ReadingResult com valor numérico
        """
        if not region.is_valid():
            return ReadingResult(
                status=ReadingStatus.NOT_CONFIGURED,
                region_name="balance",
                error="Região não configurada",
            )

        # Captura
        img = self.capture_region(region)
        if img is None:
            return ReadingResult(
                status=ReadingStatus.ERROR,
                region_name="balance",
                error="Falha na captura",
            )

        # Pré-processa
        processed = self._preprocess_image(img, "numeric")

        # OCR
        if ocr_config is None:
            ocr_config = OCRConfig(psm=7, whitelist="0123456789.,")

        text, confidence = self._run_ocr(processed, ocr_config)

        # Parse do valor
        try:
            # Remove caracteres não numéricos exceto . e ,
            clean = re.sub(r"[^\d.,]", "", text)
            # Normaliza separadores
            clean = clean.replace(",", ".")
            # Remove pontos extras (milhares)
            parts = clean.split(".")
            if len(parts) > 2:
                clean = "".join(parts[:-1]) + "." + parts[-1]

            value = float(clean) if clean else 0.0

            # Valida
            if value < 0:
                return ReadingResult(
                    status=ReadingStatus.WARNING,
                    value=value,
                    raw_text=text,
                    confidence=confidence,
                    region_name="balance",
                    error="Valor negativo",
                )

            status = (
                ReadingStatus.SUCCESS if confidence > 0.7 else ReadingStatus.WARNING
            )

            return ReadingResult(
                status=status,
                value=value,
                raw_text=text,
                confidence=confidence,
                region_name="balance",
            )

        except ValueError:
            return ReadingResult(
                status=ReadingStatus.ERROR,
                raw_text=text,
                confidence=confidence,
                region_name="balance",
                error=f"Não foi possível converter: '{text}'",
            )

    def test_timer(
        self,
        region: RegionConfig,
        ocr_config: Optional[OCRConfig] = None,
    ) -> ReadingResult:
        """
        Testa leitura do timer (Bet Xs).

        Args:
            region: Região do timer
            ocr_config: Configuração OCR

        Returns:
            ReadingResult com segundos restantes
        """
        if not region.is_valid():
            return ReadingResult(
                status=ReadingStatus.NOT_CONFIGURED,
                region_name="timer",
                error="Região não configurada",
            )

        # Captura
        img = self.capture_region(region)
        if img is None:
            return ReadingResult(
                status=ReadingStatus.ERROR,
                region_name="timer",
                error="Falha na captura",
            )

        # Pré-processa
        processed = self._preprocess_image(img, "timer")

        # OCR
        if ocr_config is None:
            ocr_config = OCRConfig(psm=7, whitelist="0123456789Bets ")

        text, confidence = self._run_ocr(processed, ocr_config)

        # Parse do timer
        # Formatos: "Bet 8s", "8s", "Bet 8 s"
        match = re.search(r"(\d+)\s*s", text, re.IGNORECASE)

        if match:
            seconds = int(match.group(1))

            status = (
                ReadingStatus.SUCCESS if confidence > 0.6 else ReadingStatus.WARNING
            )

            return ReadingResult(
                status=status,
                value=seconds,
                raw_text=text,
                confidence=confidence,
                region_name="timer",
            )

        # Timer pode não estar visível (rodada em andamento)
        return ReadingResult(
            status=ReadingStatus.WARNING,
            value=None,
            raw_text=text,
            confidence=confidence,
            region_name="timer",
            error="Timer não detectado (rodada em andamento?)",
        )

    def test_multiplier(
        self,
        region: RegionConfig,
        ocr_config: Optional[OCRConfig] = None,
    ) -> ReadingResult:
        """
        Testa leitura do multiplicador.

        Args:
            region: Região do multiplicador
            ocr_config: Configuração OCR

        Returns:
            ReadingResult com valor do multiplicador
        """
        if not region.is_valid():
            return ReadingResult(
                status=ReadingStatus.NOT_CONFIGURED,
                region_name="multiplier",
                error="Região não configurada",
            )

        # Captura
        img = self.capture_region(region)
        if img is None:
            return ReadingResult(
                status=ReadingStatus.ERROR,
                region_name="multiplier",
                error="Falha na captura",
            )

        # Pré-processa
        processed = self._preprocess_image(img, "numeric")

        # OCR
        if ocr_config is None:
            ocr_config = OCRConfig(psm=7, whitelist="0123456789.x")

        text, confidence = self._run_ocr(processed, ocr_config)

        # Parse do multiplicador
        # Formatos: "1.07x", "1.07", "8.98x"
        match = re.search(r"(\d+\.?\d*)", text)

        if match:
            try:
                value = float(match.group(1))

                # Valida range típico
                if value < 1.0 or value > 1000:
                    return ReadingResult(
                        status=ReadingStatus.WARNING,
                        value=value,
                        raw_text=text,
                        confidence=confidence,
                        region_name="multiplier",
                        error=f"Valor fora do range esperado: {value}",
                    )

                status = (
                    ReadingStatus.SUCCESS if confidence > 0.7 else ReadingStatus.WARNING
                )

                return ReadingResult(
                    status=status,
                    value=value,
                    raw_text=text,
                    confidence=confidence,
                    region_name="multiplier",
                )

            except ValueError:
                pass

        return ReadingResult(
            status=ReadingStatus.ERROR,
            raw_text=text,
            confidence=confidence,
            region_name="multiplier",
            error=f"Não foi possível extrair multiplicador: '{text}'",
        )

    def test_button_state(
        self,
        region: RegionConfig,
        bet_ready_color: Optional[ColorConfig] = None,
        waiting_color: Optional[ColorConfig] = None,
    ) -> ButtonState:
        """
        Testa estado do botão de aposta pela cor.

        Args:
            region: Região do botão
            bet_ready_color: Cor quando pode apostar (vermelho)
            waiting_color: Cor quando aguardando (verde)

        Returns:
            ButtonState com estado detectado
        """
        # Cores padrão do Brabet
        if bet_ready_color is None:
            bet_ready_color = ColorConfig(r=239, g=68, b=68, tolerance=40)

        if waiting_color is None:
            waiting_color = ColorConfig(r=34, g=197, b=94, tolerance=40)

        # Obtém cor média da região
        avg_color = self.get_average_color(region)

        # Verifica correspondência
        is_bet_ready = bet_ready_color.matches(*avg_color)
        is_waiting = waiting_color.matches(*avg_color)

        # Calcula confiança baseada na proximidade
        if is_bet_ready:
            confidence = 1.0 - (
                abs(bet_ready_color.r - avg_color[0])
                + abs(bet_ready_color.g - avg_color[1])
                + abs(bet_ready_color.b - avg_color[2])
            ) / (3 * 255)
        elif is_waiting:
            confidence = 1.0 - (
                abs(waiting_color.r - avg_color[0])
                + abs(waiting_color.g - avg_color[1])
                + abs(waiting_color.b - avg_color[2])
            ) / (3 * 255)
        else:
            confidence = 0.0

        return ButtonState(
            is_bet_ready=is_bet_ready,
            is_waiting=is_waiting,
            color=avg_color,
            confidence=confidence,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # TESTE COMPLETO DO PERFIL
    # ═══════════════════════════════════════════════════════════════════════════

    def test_profile(
        self,
        profile: CalibrationProfile,
    ) -> Dict[str, ReadingResult]:
        """
        Testa todas as leituras de um perfil.

        Args:
            profile: Perfil de calibração

        Returns:
            Dicionário com resultados de cada região
        """
        results: Dict[str, ReadingResult] = {}

        # Saldo
        if profile.balance_area:
            results["balance"] = self.test_balance(
                profile.balance_area,
                profile.ocr_balance,
            )
        else:
            results["balance"] = ReadingResult(
                status=ReadingStatus.NOT_CONFIGURED,
                region_name="balance",
            )

        # Timer
        if profile.timer_area:
            results["timer"] = self.test_timer(
                profile.timer_area,
                profile.ocr_timer,
            )
        else:
            results["timer"] = ReadingResult(
                status=ReadingStatus.NOT_CONFIGURED,
                region_name="timer",
            )

        # Multiplicador
        if profile.multiplier_area:
            results["multiplier"] = self.test_multiplier(
                profile.multiplier_area,
                profile.ocr_multiplier,
            )
        else:
            results["multiplier"] = ReadingResult(
                status=ReadingStatus.NOT_CONFIGURED,
                region_name="multiplier",
            )

        # Estado do botão
        if profile.bet_button_area:
            button_state = self.test_button_state(
                profile.bet_button_area,
                profile.button_bet_ready,
                profile.button_waiting,
            )

            state_text = (
                "APOSTAR"
                if button_state.is_bet_ready
                else "AGUARDANDO" if button_state.is_waiting else "DESCONHECIDO"
            )

            results["button"] = ReadingResult(
                status=(
                    ReadingStatus.SUCCESS
                    if button_state.is_bet_ready or button_state.is_waiting
                    else ReadingStatus.WARNING
                ),
                value=state_text,
                confidence=button_state.confidence,
                region_name="button",
            )
        else:
            results["button"] = ReadingResult(
                status=ReadingStatus.NOT_CONFIGURED,
                region_name="button",
            )

        return results

    def cleanup(self) -> None:
        """Libera recursos."""
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_live_preview: Optional[LivePreview] = None
_preview_lock = threading.Lock()


def get_live_preview() -> LivePreview:
    """
    Retorna instância singleton do LivePreview.
    """
    global _live_preview

    if _live_preview is None:
        with _preview_lock:
            if _live_preview is None:
                _live_preview = LivePreview()

    return _live_preview


def reset_live_preview() -> None:
    """Reseta o LivePreview."""
    global _live_preview
    with _preview_lock:
        if _live_preview:
            _live_preview.cleanup()
        _live_preview = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO LIVE PREVIEW - CrashBot v3.0")
    print("=" * 60)

    preview = LivePreview()

    # Verifica dependências
    print("\n--- Dependências ---")
    print(f"   mss: {'✅' if HAS_MSS else '❌'}")
    print(f"   OpenCV: {'✅' if HAS_CV2 else '❌'}")
    print(f"   Tesseract: {'✅' if HAS_TESSERACT else '❌'}")

    # Testa captura
    print("\n--- Teste de Captura ---")
    region = RegionConfig(x=100, y=100, width=200, height=50)
    img = preview.capture_region(region)

    if img is not None:
        print(f"   ✅ Captura OK: {img.shape}")
    else:
        print("   ❌ Falha na captura")

    # Testa cor
    print("\n--- Teste de Cor ---")
    color = preview.get_color_at(500, 500)
    print(f"   Cor em (500, 500): RGB{color}")

    # Testa com perfil de exemplo
    print("\n--- Teste com Perfil ---")
    from calibration.profile_manager import ProfileManager

    manager = ProfileManager()
    profile = manager.create_default_profile("teste")

    results = preview.test_profile(profile)

    for name, result in results.items():
        print(
            f"   {result.status_icon} {name}: {result.value} ({result.confidence:.0%})"
        )
        if result.error:
            print(f"      └─ {result.error}")

    # Cleanup
    preview.cleanup()

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
