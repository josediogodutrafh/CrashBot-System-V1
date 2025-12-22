#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - TEMPLATE MATCHING

Reconhecimento de dígitos e elementos visuais usando template matching.
Mais preciso que OCR para a fonte específica do jogo.

Uso:
    from engine.vision.templates import TemplateEngine, get_templates

    templates = get_templates()
    templates.load_digit_templates("assets/templates/multiplier")

    # Lê valor do multiplicador
    value = templates.read_value(image)

    # Detecta "Bet 8s"
    found = templates.detect_bet_window(image)
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════


class TemplateSet(Enum):
    """Conjuntos de templates disponíveis."""

    MULTIPLIER_CENTRAL = "multiplier"  # Dígitos grandes amarelos
    MULTIPLIER_HISTORY = "history"  # Dígitos pequenos das pills
    BET_WINDOW = "bet_window"  # "Bet 8s"


# Threshold padrão para considerar um match válido
DEFAULT_MATCH_THRESHOLD = 0.75

# Dígitos esperados
DIGIT_CHARS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "ponto"]


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TemplateMatch:
    """Resultado de um template matching."""

    char: str  # Caractere encontrado ('0'-'9' ou '.')
    confidence: float  # Confiança do match (0-1)
    x: int  # Posição X na imagem
    y: int  # Posição Y na imagem
    width: int  # Largura do template
    height: int  # Altura do template

    @property
    def center_x(self) -> int:
        """Centro X do match."""
        return self.x + self.width // 2

    @property
    def right(self) -> int:
        """Borda direita do match."""
        return self.x + self.width


@dataclass
class DigitTemplate:
    """Template de um dígito."""

    char: str  # '0'-'9' ou 'ponto'
    image: np.ndarray  # Imagem do template
    width: int  # Largura
    height: int  # Altura

    @property
    def display_char(self) -> str:
        """Caractere para exibição."""
        return "." if self.char == "ponto" else self.char


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class TemplateEngine:
    """
    Motor de reconhecimento por template matching.

    Features:
        - Carrega templates de dígitos de uma pasta
        - Reconhece valores numéricos em imagens
        - Detecta elementos específicos (Bet 8s)
        - Suporte a múltiplas escalas
        - Cache de templates para performance

    Exemplo:
        engine = TemplateEngine()
        engine.load_digit_templates("assets/templates/multiplier")

        # Lê multiplicador
        value = engine.read_value(multiplier_image)
        print(f"Multiplicador: {value}x")

        # Detecta janela de apostas
        if engine.detect_template(screen, "bet_8s.png"):
            print("Janela de apostas aberta!")
    """

    def __init__(self, match_threshold: float = DEFAULT_MATCH_THRESHOLD):
        """
        Inicializa o motor de templates.

        Args:
            match_threshold: Threshold mínimo para considerar match válido
        """
        if not HAS_CV2:
            raise ImportError(
                "OpenCV não encontrado. Instale com: pip install opencv-python"
            )

        self._match_threshold = match_threshold
        self._lock = threading.Lock()

        # Cache de templates por conjunto
        self._digit_templates: Dict[TemplateSet, List[DigitTemplate]] = {}

        # Templates especiais (bet_8s, etc)
        self._special_templates: Dict[str, np.ndarray] = {}

        logger.debug(f"TemplateEngine inicializado (threshold={match_threshold})")

    # ═══════════════════════════════════════════════════════════════════════════
    # CARREGAMENTO DE TEMPLATES
    # ═══════════════════════════════════════════════════════════════════════════

    def load_digit_templates(
        self,
        folder_path: str,
        template_set: TemplateSet = TemplateSet.MULTIPLIER_CENTRAL,
    ) -> bool:
        """
        Carrega templates de dígitos de uma pasta.

        Espera arquivos: 0.png, 1.png, ..., 9.png, ponto.png

        Args:
            folder_path: Caminho da pasta com os templates
            template_set: Identificador do conjunto de templates

        Returns:
            True se carregou com sucesso
        """
        folder = Path(folder_path)

        if not folder.exists():
            logger.error(f"Pasta não encontrada: {folder_path}")
            return False

        templates = []

        for char in DIGIT_CHARS:
            # Tenta diferentes extensões
            for ext in [".png", ".jpg", ".bmp"]:
                file_path = folder / f"{char}{ext}"
                if file_path.exists():
                    template = self._load_template_file(file_path, char)
                    if template:
                        templates.append(template)
                    break

        if not templates:
            logger.error(f"Nenhum template encontrado em: {folder_path}")
            return False

        with self._lock:
            self._digit_templates[template_set] = templates

        logger.info(
            f"Carregados {len(templates)} templates de '{template_set.value}' de {folder_path}"
        )
        return True

    def load_special_template(self, file_path: str, name: str) -> bool:
        """
        Carrega um template especial (bet_8s, botões, etc).

        Args:
            file_path: Caminho do arquivo de imagem
            name: Nome identificador do template

        Returns:
            True se carregou com sucesso
        """
        path = Path(file_path)

        if not path.exists():
            logger.error(f"Template não encontrado: {file_path}")
            return False

        try:
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                logger.error(f"Falha ao ler imagem: {file_path}")
                return False

            with self._lock:
                self._special_templates[name] = img

            logger.info(f"Template especial '{name}' carregado")
            return True

        except Exception as e:
            logger.error(f"Erro ao carregar template: {e}")
            return False

    def _load_template_file(
        self, file_path: Path, char: str
    ) -> Optional[DigitTemplate]:
        """Carrega um arquivo de template."""
        try:
            img = cv2.imread(str(file_path), cv2.IMREAD_COLOR)
            if img is None:
                logger.warning(f"Falha ao ler: {file_path}")
                return None

            h, w = img.shape[:2]

            return DigitTemplate(char=char, image=img, width=w, height=h)

        except Exception as e:
            logger.error(f"Erro ao carregar {file_path}: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════════
    # TEMPLATE MATCHING
    # ═══════════════════════════════════════════════════════════════════════════

    def find_all_matches(
        self,
        image: np.ndarray,
        template_set: TemplateSet = TemplateSet.MULTIPLIER_CENTRAL,
        threshold: Optional[float] = None,
    ) -> List[TemplateMatch]:
        """
        Encontra todos os dígitos em uma imagem.

        Args:
            image: Imagem onde procurar
            template_set: Conjunto de templates a usar
            threshold: Threshold de confiança (usa default se None)

        Returns:
            Lista de matches encontrados, ordenados por posição X
        """
        if image is None or image.size == 0:
            return []

        threshold = threshold or self._match_threshold

        with self._lock:
            templates = self._digit_templates.get(template_set, [])

        if not templates:
            logger.warning(f"Templates não carregados para: {template_set.value}")
            return []

        all_matches: List[TemplateMatch] = []

        for template in templates:
            matches = self._find_template_matches(image, template, threshold)
            all_matches.extend(matches)

        # Remove matches sobrepostos (Non-Maximum Suppression)
        filtered_matches = self._non_max_suppression(all_matches)

        # Ordena por posição X (esquerda para direita)
        filtered_matches.sort(key=lambda m: m.x)

        return filtered_matches

    def _find_template_matches(
        self,
        image: np.ndarray,
        template: DigitTemplate,
        threshold: float,
    ) -> List[TemplateMatch]:
        """Encontra todas as ocorrências de um template na imagem."""
        matches = []

        # Verifica se template cabe na imagem
        img_h, img_w = image.shape[:2]
        if template.height > img_h or template.width > img_w:
            return []

        try:
            # Template matching
            result = cv2.matchTemplate(image, template.image, cv2.TM_CCOEFF_NORMED)

            # Encontra locais acima do threshold
            locations = np.where(result >= threshold)

            for pt in zip(*locations[::-1]):  # x, y
                confidence = result[pt[1], pt[0]]

                match = TemplateMatch(
                    char=template.char,
                    confidence=float(confidence),
                    x=int(pt[0]),
                    y=int(pt[1]),
                    width=template.width,
                    height=template.height,
                )
                matches.append(match)

        except Exception as e:
            logger.error(f"Erro no template matching: {e}")

        return matches

    def _non_max_suppression(
        self,
        matches: List[TemplateMatch],
        overlap_threshold: float = 0.5,
    ) -> List[TemplateMatch]:
        """
        Remove matches sobrepostos, mantendo o de maior confiança.

        Args:
            matches: Lista de matches
            overlap_threshold: Threshold de sobreposição para considerar duplicado

        Returns:
            Lista filtrada de matches
        """
        if not matches:
            return []

        # Ordena por confiança (maior primeiro)
        sorted_matches = sorted(matches, key=lambda m: m.confidence, reverse=True)

        kept = []

        for match in sorted_matches:
            # Verifica se sobrepõe com algum já mantido
            overlaps = False

            for kept_match in kept:
                if self._calculate_overlap(match, kept_match) > overlap_threshold:
                    overlaps = True
                    break

            if not overlaps:
                kept.append(match)

        return kept

    def _calculate_overlap(self, m1: TemplateMatch, m2: TemplateMatch) -> float:
        """Calcula a sobreposição entre dois matches (IoU)."""
        # Calcula interseção
        x1 = max(m1.x, m2.x)
        y1 = max(m1.y, m2.y)
        x2 = min(m1.x + m1.width, m2.x + m2.width)
        y2 = min(m1.y + m1.height, m2.y + m2.height)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)

        # Calcula união
        area1 = m1.width * m1.height
        area2 = m2.width * m2.height
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    # ═══════════════════════════════════════════════════════════════════════════
    # LEITURA DE VALORES
    # ═══════════════════════════════════════════════════════════════════════════

    def read_value(
        self,
        image: np.ndarray,
        template_set: TemplateSet = TemplateSet.MULTIPLIER_CENTRAL,
        threshold: Optional[float] = None,
    ) -> Optional[float]:
        """
        Lê um valor numérico de uma imagem.

        Args:
            image: Imagem contendo o número
            template_set: Conjunto de templates a usar
            threshold: Threshold de confiança

        Returns:
            Valor float ou None se não conseguir ler
        """
        matches = self.find_all_matches(image, template_set, threshold)

        if not matches:
            return None

        # Monta string a partir dos matches ordenados por X
        chars = []
        for match in matches:
            if match.char == "ponto":
                chars.append(".")
            else:
                chars.append(match.char)

        value_str = "".join(chars)

        # Converte para float
        try:
            value = float(value_str)
            logger.debug(f"Valor lido: {value_str} -> {value}")
            return value
        except ValueError:
            logger.warning(f"Não foi possível converter '{value_str}' para número")
            return None

    def read_value_with_confidence(
        self,
        image: np.ndarray,
        template_set: TemplateSet = TemplateSet.MULTIPLIER_CENTRAL,
        threshold: Optional[float] = None,
    ) -> Tuple[Optional[float], float, List[TemplateMatch]]:
        """
        Lê um valor e retorna também a confiança e os matches.

        Args:
            image: Imagem contendo o número
            template_set: Conjunto de templates a usar
            threshold: Threshold de confiança

        Returns:
            Tupla (valor, confiança_média, lista_de_matches)
        """
        matches = self.find_all_matches(image, template_set, threshold)

        if not matches:
            return None, 0.0, []

        # Calcula confiança média
        avg_confidence = sum(m.confidence for m in matches) / len(matches)

        # Monta valor
        chars = []
        for match in matches:
            chars.append("." if match.char == "ponto" else match.char)

        value_str = "".join(chars)

        try:
            value = float(value_str)
            return value, avg_confidence, matches
        except ValueError:
            return None, avg_confidence, matches

    # ═══════════════════════════════════════════════════════════════════════════
    # DETECÇÃO DE TEMPLATES ESPECIAIS
    # ═══════════════════════════════════════════════════════════════════════════

    def detect_template(
        self,
        image: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
    ) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
        """
        Detecta se um template especial está presente na imagem.

        Args:
            image: Imagem onde procurar
            template_name: Nome do template (ex: "bet_8s")
            threshold: Threshold de confiança

        Returns:
            Tupla (encontrado, confiança, posição_xy)
        """
        threshold = threshold or self._match_threshold

        with self._lock:
            template = self._special_templates.get(template_name)

        if template is None:
            logger.warning(f"Template especial não carregado: {template_name}")
            return False, 0.0, None

        try:
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)

            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                return True, float(max_val), max_loc
            else:
                return False, float(max_val), None

        except Exception as e:
            logger.error(f"Erro ao detectar template: {e}")
            return False, 0.0, None

    def detect_bet_window(
        self,
        image: np.ndarray,
        threshold: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """
        Detecta se a janela "Bet 8s" está visível.

        Args:
            image: Imagem da tela
            threshold: Threshold de confiança

        Returns:
            Tupla (encontrado, confiança)
        """
        found, confidence, _ = self.detect_template(image, "bet_8s", threshold)
        return found, confidence

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_loaded_templates(self) -> Dict[str, int]:
        """Retorna informações sobre templates carregados."""
        with self._lock:
            info = {}

            for template_set, templates in self._digit_templates.items():
                info[f"digits_{template_set.value}"] = len(templates)

            info["special"] = len(self._special_templates)

            return info

    def set_threshold(self, threshold: float) -> None:
        """Define o threshold global de matching."""
        self._match_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Threshold atualizado: {self._match_threshold}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_template_engine: Optional[TemplateEngine] = None
_template_lock = threading.Lock()


def get_templates() -> TemplateEngine:
    """
    Retorna a instância singleton do TemplateEngine.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _template_engine

    if _template_engine is None:
        with _template_lock:
            if _template_engine is None:
                _template_engine = TemplateEngine()

    return _template_engine


def reset_templates() -> None:
    """Reseta o motor de templates (útil para testes)."""
    global _template_engine
    with _template_lock:
        _template_engine = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO TEMPLATE ENGINE - CrashBot v3.0")
    print("=" * 60)

    if not HAS_CV2:
        print("❌ OpenCV não instalado!")
        exit(1)

    # Cria engine
    engine = TemplateEngine()
    print(f"\n✅ TemplateEngine criado")
    print(f"   Threshold: {engine._match_threshold}")

    # Testa carregamento (pasta fictícia para demonstração)
    print(f"\n--- Teste de Carregamento ---")

    # Verifica se pasta de templates existe
    test_paths = [
        "assets/templates/multiplier",
        "templates/multiplier",
        "../templates/multiplier",
    ]

    loaded = False
    for path in test_paths:
        if os.path.exists(path):
            if engine.load_digit_templates(path, TemplateSet.MULTIPLIER_CENTRAL):
                print(f"   ✅ Templates carregados de: {path}")
                loaded = True
                break

    if not loaded:
        print(f"   ⚠️ Pasta de templates não encontrada")
        print(f"   Crie a pasta com os arquivos: 0.png - 9.png + ponto.png")

    # Info dos templates
    info = engine.get_loaded_templates()
    print(f"\n--- Templates Carregados ---")
    for key, count in info.items():
        print(f"   {key}: {count}")

    # Teste com imagem sintética
    print(f"\n--- Teste com Imagem Sintética ---")

    # Cria imagem de teste
    test_img = np.ones((100, 300, 3), dtype=np.uint8) * 50
    cv2.putText(
        test_img, "1.23", (50, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 3
    )

    print(f"   Imagem criada: {test_img.shape}")
    print(f"   (Para teste real, use imagens capturadas do jogo)")

    print("\n" + "=" * 60)
    print("✅ TESTES BÁSICOS CONCLUÍDOS!")
    print("=" * 60)
