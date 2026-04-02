#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - OCR (Optical Character Recognition)

Módulo responsável pela leitura de textos na tela.
Suporta Tesseract e EasyOCR como backends.

Uso:
    from engine.vision.ocr import OCREngine, get_ocr

    ocr = get_ocr()

    # Lê texto de uma imagem
    text = ocr.read_text(image)

    # Lê número (otimizado para valores)
    value = ocr.read_number(image)
"""

from __future__ import annotations

import logging
import re
import threading
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np

try:
    import cv2

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import pytesseract

    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import easyocr

    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class OCRBackend(Enum):
    """Backends de OCR disponíveis."""

    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    AUTO = "auto"


class PreprocessMode(Enum):
    """Modos de pré-processamento."""

    NONE = "none"
    STANDARD = "standard"
    NUMERIC = "numeric"
    HIGH_CONTRAST = "high_contrast"


# ═══════════════════════════════════════════════════════════════════════════════
# OCR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class OCREngine:
    """
    Motor de OCR unificado.

    Features:
        - Suporte a Tesseract e EasyOCR
        - Pré-processamento automático
        - Otimizado para números
        - Thread-safe

    Exemplo:
        ocr = OCREngine()

        # Lê texto genérico
        text = ocr.read_text(image)

        # Lê valor numérico
        value = ocr.read_number(image)

        # Lê com backend específico
        text = ocr.read_text(image, backend=OCRBackend.EASYOCR)
    """

    def __init__(
        self,
        preferred_backend: OCRBackend = OCRBackend.AUTO,
        tesseract_path: Optional[str] = None,
    ):
        """
        Inicializa o motor de OCR.

        Args:
            preferred_backend: Backend preferido
            tesseract_path: Caminho do executável Tesseract
        """
        self._lock = threading.Lock()
        self._preferred_backend = preferred_backend

        # Configura Tesseract
        if tesseract_path and HAS_TESSERACT:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif HAS_TESSERACT:
            # Tenta path padrão Windows
            default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            import os

            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path

        # Inicializa EasyOCR (lazy loading)
        self._easyocr_reader: Optional[easyocr.Reader] = None

        # Detecta backend disponível
        self._available_backend = self._detect_backend()

        logger.debug(f"OCREngine inicializado (backend: {self._available_backend})")

    def _detect_backend(self) -> OCRBackend:
        """Detecta qual backend está disponível."""
        if self._preferred_backend == OCRBackend.TESSERACT and HAS_TESSERACT:
            return OCRBackend.TESSERACT
        elif self._preferred_backend == OCRBackend.EASYOCR and HAS_EASYOCR:
            return OCRBackend.EASYOCR
        elif self._preferred_backend == OCRBackend.AUTO:
            # Prefere Tesseract por ser mais rápido
            if HAS_TESSERACT:
                return OCRBackend.TESSERACT
            elif HAS_EASYOCR:
                return OCRBackend.EASYOCR

        logger.warning("Nenhum backend de OCR disponível!")
        return OCRBackend.AUTO

    def _get_easyocr_reader(self) -> Optional[easyocr.Reader]:
        """Retorna reader EasyOCR (lazy loading)."""
        if not HAS_EASYOCR:
            return None

        if self._easyocr_reader is None:
            try:
                self._easyocr_reader = easyocr.Reader(
                    ["pt", "en"], gpu=False, verbose=False
                )
                logger.debug("EasyOCR reader inicializado")
            except Exception as e:
                logger.error(f"Erro ao inicializar EasyOCR: {e}")
                return None

        return self._easyocr_reader

    # ═══════════════════════════════════════════════════════════════════════════
    # PRÉ-PROCESSAMENTO
    # ═══════════════════════════════════════════════════════════════════════════

    def preprocess(
        self,
        image: np.ndarray,
        mode: PreprocessMode = PreprocessMode.STANDARD,
    ) -> np.ndarray:
        """
        Pré-processa imagem para OCR.

        Args:
            image: Imagem de entrada (BGR)
            mode: Modo de pré-processamento

        Returns:
            Imagem processada
        """
        if not HAS_CV2:
            return image

        if mode == PreprocessMode.NONE:
            return image

        # Converte para escala de cinza
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if mode == PreprocessMode.STANDARD:
            # Binarização adaptativa
            processed = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

        elif mode == PreprocessMode.NUMERIC:
            # Otimizado para números
            # Aumenta contraste
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)

            # Threshold Otsu
            _, processed = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            # Dilata levemente para conectar dígitos
            kernel = np.ones((2, 1), np.uint8)
            processed = cv2.dilate(processed, kernel, iterations=1)

        elif mode == PreprocessMode.HIGH_CONTRAST:
            # Alto contraste para textos difíceis
            # CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

            # Binarização
            _, processed = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        else:
            processed = gray

        return processed

    def resize_for_ocr(
        self,
        image: np.ndarray,
        target_height: int = 50,
    ) -> np.ndarray:
        """
        Redimensiona imagem para altura ideal de OCR.

        Args:
            image: Imagem de entrada
            target_height: Altura alvo

        Returns:
            Imagem redimensionada
        """
        if not HAS_CV2:
            return image

        h, w = image.shape[:2]

        if h < target_height:
            scale = target_height / h
            new_w = int(w * scale)
            return cv2.resize(
                image, (new_w, target_height), interpolation=cv2.INTER_CUBIC
            )

        return image

    # ═══════════════════════════════════════════════════════════════════════════
    # LEITURA DE TEXTO
    # ═══════════════════════════════════════════════════════════════════════════

    def read_text(
        self,
        image: np.ndarray,
        backend: Optional[OCRBackend] = None,
        preprocess: PreprocessMode = PreprocessMode.STANDARD,
        config: str = "",
    ) -> str:
        """
        Lê texto de uma imagem.

        Args:
            image: Imagem de entrada (BGR ou grayscale)
            backend: Backend a usar (None = auto)
            preprocess: Modo de pré-processamento
            config: Configuração adicional (Tesseract)

        Returns:
            Texto extraído
        """
        if image is None or image.size == 0:
            return ""

        # Pré-processa
        processed = self.preprocess(image, preprocess)

        # Seleciona backend
        use_backend = backend or self._available_backend

        with self._lock:
            if use_backend == OCRBackend.TESSERACT:
                return self._read_tesseract(processed, config)
            elif use_backend == OCRBackend.EASYOCR:
                return self._read_easyocr(processed)
            else:
                return ""

    def _read_tesseract(self, image: np.ndarray, config: str = "") -> str:
        """Lê texto usando Tesseract."""
        if not HAS_TESSERACT:
            return ""

        try:
            # Configuração padrão
            if not config:
                config = "--psm 7 -c tessedit_char_whitelist=0123456789.,"

            text = pytesseract.image_to_string(image, config=config).strip()

            return text

        except Exception as e:
            logger.error(f"Erro Tesseract: {e}")
            return ""

    def _read_easyocr(self, image: np.ndarray) -> str:
        """Lê texto usando EasyOCR."""
        reader = self._get_easyocr_reader()
        if reader is None:
            return ""

        try:
            results = reader.readtext(image, detail=0)
            return " ".join(results).strip()

        except Exception as e:
            logger.error(f"Erro EasyOCR: {e}")
            return ""

    # ═══════════════════════════════════════════════════════════════════════════
    # LEITURA DE NÚMEROS
    # ═══════════════════════════════════════════════════════════════════════════

    def read_number(
        self,
        image: np.ndarray,
        backend: Optional[OCRBackend] = None,
    ) -> Optional[float]:
        """
        Lê um valor numérico de uma imagem.

        Otimizado para leitura de saldos e multiplicadores.

        Args:
            image: Imagem de entrada
            backend: Backend a usar

        Returns:
            Valor numérico ou None se falhar
        """
        if image is None or image.size == 0:
            return None

        # Redimensiona se necessário
        image = self.resize_for_ocr(image)

        # Usa pré-processamento para números
        processed = self.preprocess(image, PreprocessMode.NUMERIC)

        # Configuração específica para números
        config = "--psm 7 -c tessedit_char_whitelist=0123456789.,"

        # Lê texto
        text = self.read_text(
            processed,
            backend=backend,
            preprocess=PreprocessMode.NONE,  # Já processamos
            config=config,
        )

        # Extrai número
        return self._extract_number(text)

    def _extract_number(self, text: str) -> Optional[float]:
        """
        Extrai valor numérico de uma string.

        Args:
            text: Texto com possível número

        Returns:
            Valor float ou None
        """
        if not text:
            return None

        # Limpa o texto
        text = text.strip()

        # Remove caracteres inválidos mantendo números, ponto e vírgula
        text = re.sub(r"[^\d.,]", "", text)

        if not text:
            return None

        # Trata formato brasileiro (1.234,56) vs americano (1,234.56)
        # Se tem vírgula após ponto, é brasileiro
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                # Formato brasileiro: 1.234,56
                text = text.replace(".", "").replace(",", ".")
            else:
                # Formato americano: 1,234.56
                text = text.replace(",", "")
        elif "," in text:
            # Pode ser decimal brasileiro ou separador de milhar
            parts = text.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Provavelmente decimal: 123,45
                text = text.replace(",", ".")
            else:
                # Separador de milhar: 1,234
                text = text.replace(",", "")

        try:
            return float(text)
        except ValueError:
            logger.debug(f"Não foi possível converter '{text}' para número")
            return None

    def read_multiplier(self, image: np.ndarray) -> Optional[float]:
        """
        Lê um multiplicador (ex: "2.45x").

        Args:
            image: Imagem com o multiplicador

        Returns:
            Valor do multiplicador ou None
        """
        # Lê como número normal
        value = self.read_number(image)

        if value is not None:
            # Valida range típico de multiplicador
            if 1.0 <= value <= 1000.0:
                return value

        # Tenta leitura alternativa com texto completo
        text = self.read_text(image, preprocess=PreprocessMode.HIGH_CONTRAST)

        # Procura padrão de multiplicador
        match = re.search(r"(\d+[.,]\d+)", text)
        if match:
            return self._extract_number(match.group(1))

        return None

    def read_balance(self, image: np.ndarray) -> Optional[float]:
        """
        Lê um saldo (ex: "R$ 1.234,56").

        Args:
            image: Imagem com o saldo

        Returns:
            Valor do saldo ou None
        """
        # Tenta leitura numérica direta
        value = self.read_number(image)

        if value is not None and value >= 0:
            return value

        # Tenta com texto completo
        text = self.read_text(image, preprocess=PreprocessMode.STANDARD)

        # Remove símbolos de moeda
        text = re.sub(r"[R$\s]", "", text)

        return self._extract_number(text)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_ocr_engine: Optional[OCREngine] = None
_ocr_lock = threading.Lock()


def get_ocr() -> OCREngine:
    """
    Retorna a instância singleton do OCREngine.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _ocr_engine

    if _ocr_engine is None:
        with _ocr_lock:
            if _ocr_engine is None:
                _ocr_engine = OCREngine()

    return _ocr_engine


def reset_ocr() -> None:
    """Reseta o motor de OCR (útil para testes)."""
    global _ocr_engine
    with _ocr_lock:
        _ocr_engine = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO OCR ENGINE - CrashBot v3.0")
    print("=" * 60)

    print(f"\n--- Backends Disponíveis ---")
    print(f"   OpenCV: {'✅' if HAS_CV2 else '❌'}")
    print(f"   Tesseract: {'✅' if HAS_TESSERACT else '❌'}")
    print(f"   EasyOCR: {'✅' if HAS_EASYOCR else '❌'}")

    if not HAS_CV2:
        print("\n❌ OpenCV não instalado!")
        exit(1)

    # Cria engine
    ocr = OCREngine()
    print(f"\n✅ OCREngine criado")
    print(f"   Backend ativo: {ocr._available_backend.value}")

    # Teste de extração de número
    print(f"\n--- Teste Extração de Número ---")
    test_cases = [
        ("123.45", 123.45),
        ("1.234,56", 1234.56),
        ("R$ 1.000,00", 1000.0),
        ("2,45x", 2.45),
        ("abc", None),
    ]

    for text, expected in test_cases:
        result = ocr._extract_number(text)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{text}' -> {result} (esperado: {expected})")

    # Teste com imagem sintética
    if HAS_CV2:
        print(f"\n--- Teste com Imagem Sintética ---")

        # Cria imagem com texto
        img = np.ones((50, 150, 3), dtype=np.uint8) * 255
        cv2.putText(img, "123.45", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # Testa pré-processamento
        processed = ocr.preprocess(img, PreprocessMode.NUMERIC)
        print(f"   ✅ Pré-processamento OK: {processed.shape}")

        # Testa leitura (pode falhar dependendo do backend)
        if ocr._available_backend != OCRBackend.AUTO:
            value = ocr.read_number(img)
            print(f"   Valor lido: {value}")
        else:
            print(f"   ⚠️ Nenhum backend disponível para teste de leitura")

    print("\n" + "=" * 60)
    print("✅ TESTES BÁSICOS CONCLUÍDOS!")
    print("=" * 60)
