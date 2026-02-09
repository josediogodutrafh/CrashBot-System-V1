#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo VisionSystem (Sistema de Visão)
Responsável por toda a interação visual com a tela, incluindo captura,
reconhecimento de caracteres (OCR) e template matching.
"""


import contextlib
import json
import logging
import os
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import mss
import numpy as np
import pytesseract
from src.config import (
    PROJECT_ROOT,
    TESSERACT_PATH,
    TEMPLATES_SALDO,
    TEMPLATES_DEBUG,
)

# Tentar importar EasyOCR como fallback
try:
    import easyocr

    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("EasyOCR não instalado. Usando apenas pytesseract.")


class VisionSystem:
    """Sistema de visão que integra com estrutura existente - OTIMIZADO"""

    def __init__(self, config_path: str):
        # --- 1. CRIA O LOGGER PRIMEIRO (CORREÇÃO CRÍTICA) ---
        self.logger = logging.getLogger(__name__)

        # --- 2. CONFIGURA O TESSERACT ---
        tesseract_path = str(TESSERACT_PATH)

        self.logger.info(f"VisionSystem procurando Tesseract em: {tesseract_path}")

        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            self.logger.info("Tesseract encontrado e configurado.")
        else:
            self.logger.warning(
                f"Tesseract NAO encontrado em: {tesseract_path}"
            )
            self.logger.warning(
                "Tentando usar variável de ambiente do sistema..."
            )
            pytesseract.pytesseract.tesseract_cmd = 'tesseract'

        # --- 3. CONFIGURAÇÃO E CAMINHOS ---
        self.config_path = config_path
        self.config = self.load_config()

        # Templates de saldo
        self.template_path = str(TEMPLATES_SALDO)

        # --- 4. PRÉ-CARREGAMENTO DOS TEMPLATES ---
        self.template_cache = self.load_templates(self.template_path)

        # Carrega os templates de multiplicador
        self.multiplier_templates = self._load_multiplier_templates()

        # --- 5. INICIALIZAÇÃO DO OCR DE FALLBACK ---
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr_reader = easyocr.Reader(["pt", "en"], gpu=False)
                self.logger.info("EasyOCR inicializado.")
            except Exception as e:
                self.logger.error(f"Erro ao inicializar EasyOCR: {e}")
                self.easyocr_reader = None

        self.value_history = deque(maxlen=5)
        self.balance_corrections = self.load_balance_corrections()

        self.logger.info("VisionSystem inicializado")

    def _load_multiplier_templates(self) -> dict:
        """Carrega os templates de dígitos do multiplicador e binariza."""
        templates = {}

        template_dir = Path(TEMPLATES_DEBUG)

        if not template_dir.is_dir():
            self.logger.error(
                f"Diretório de templates de multiplicador não encontrado: {template_dir}"
            )
            return {}

        # Carrega os dígitos de 0 a 9
        for d in range(10):
            path = template_dir / f"{d}.png"
            if path.exists():
                gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                if gray is not None:
                    # Binarizar: dígitos brancos (255) em fundo preto (0)
                    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                    templates[str(d)] = binary

        # Carrega o ponto
        ponto_path = template_dir / "ponto.png"
        if ponto_path.exists():
            gray = cv2.imread(str(ponto_path), cv2.IMREAD_GRAYSCALE)
            if gray is not None:
                _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
                templates["."] = binary

        self.logger.info(
            f"{len(templates)} templates de multiplicador carregados (binarizados)."
        )
        return templates

    def _disambiguate_3_vs_5(self, roi: np.ndarray) -> str:
        """
        Desempata 3 e 5 olhando se existe a linha vertical na esquerda.
        Retorna '5' se tiver pixels na esquerda, '3' se for vazio.
        """
        h, w = roi.shape

        y_start, y_end = int(h * 0.15), int(h * 0.50)
        x_start, x_end = 0, int(w * 0.30)

        neck_region = roi[y_start:y_end, x_start:x_end]

        white_pixels = cv2.countNonZero(neck_region)
        total_pixels = neck_region.size

        if total_pixels == 0:
            return '3'

        ratio = white_pixels / total_pixels

        if ratio > 0.20:
            return '5'
        else:
            return '3'

    def load_config(self) -> Dict:
        """Carrega config.json existente"""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar {self.config_path}: {e}")
            return {}

    def load_balance_corrections(self) -> Dict:
        """Carrega correções aprendidas"""
        try:
            path = PROJECT_ROOT / "data" / "balance_corrections.json"
            if path.exists():
                with open(path, "r") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar correcoes: {e}")
        return {}

    def load_templates(self, template_path: str) -> Dict[str, np.ndarray]:
        """
        Carrega todos os templates de imagem de um diretório específico
        e os retorna em um dicionário (cache).
        """
        cache: Dict[str, np.ndarray] = {}

        template_dir = Path(template_path)

        try:
            if not template_dir.is_dir():
                self.logger.warning(
                    f"Diretório de template de saldo não encontrado: "
                    f"{template_path}"
                )
                return cache

            for digit in range(10):
                template_file = template_dir / f"{digit:02d}.png"
                if template_file.exists():
                    template = cv2.imread(
                        str(template_file), cv2.IMREAD_GRAYSCALE
                    )
                    if template is not None:
                        cache[str(digit)] = template

            point_file = template_dir / "ponto.png"
            if point_file.exists():
                point_template = cv2.imread(
                    str(point_file), cv2.IMREAD_GRAYSCALE
                )
                if point_template is not None:
                    cache["."] = point_template

            self.logger.info(
                f"✅ Templates de saldo carregados: "
                f"{len(cache)} items de {template_path}"
            )

        except Exception as e:
            self.logger.error(f"Erro ao carregar templates de saldo: {e}")

        return cache

    def capture_region(self, region: Dict) -> Optional[np.ndarray]:
        """Captura região da tela"""
        try:
            with mss.mss() as sct:
                screenshot = sct.grab(
                    {
                        "top": region["y"],
                        "left": region["x"],
                        "width": region["width"],
                        "height": region["height"],
                    }
                )
                return np.array(screenshot)
        except Exception as e:
            self.logger.error(f"Erro na captura: {e}")
            return None

    def preprocess_for_ocr(
        self, img: np.ndarray, target_type: str = "general"
    ) -> np.ndarray:
        """Pré-processamento otimizado para texto claro em fundo escuro."""

        if len(img.shape) >= 3:
            if img.shape[2] == 4:
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        if target_type == "balance":
            scale_factor = 3
            gray = cv2.resize(
                gray,
                (gray.shape[1] * scale_factor, gray.shape[0] * scale_factor),
                interpolation=cv2.INTER_CUBIC,
            )
            gray = cv2.medianBlur(gray, 3)
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            return binary

        elif target_type == "bet_detection":
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
            return binary

        elif target_type == "multiplier":
            gray_resized = cv2.resize(
                gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
            )
            _, binary = cv2.threshold(
                src=gray_resized,
                thresh=150,
                maxval=255,
                type=cv2.THRESH_BINARY_INV,
            )
            return binary

        return gray

    def pytesseract_extract(
        self, img: np.ndarray, target_type: str = "general"
    ) -> List[str]:
        """Extração com pytesseract com configs melhorados"""
        results = []

        try:
            if target_type == "balance":
                configs = [
                    "--psm 8 -c tessedit_char_whitelist=0123456789., "
                    "--dpi 300",
                    "--psm 7 -c tessedit_char_whitelist=0123456789., "
                    "--dpi 300",
                    "--psm 6 -c tessedit_char_whitelist=0123456789., "
                    "--dpi 300",
                    "--psm 13 -c tessedit_char_whitelist=0123456789., "
                    "--dpi 300",
                ]

                for config in configs:
                    text = pytesseract.image_to_string(
                        img, config=config
                    ).strip()
                    if text and any(c.isdigit() for c in text):
                        results.append(text)

                if not results:
                    inverted = cv2.bitwise_not(img)
                    for config in configs[:2]:
                        text = pytesseract.image_to_string(
                            inverted, config=config
                        ).strip()
                        if text and any(c.isdigit() for c in text):
                            results.append(text)

            elif target_type == "bet_detection":
                configs = [
                    "--psm 7 -c "
                    "tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    "--psm 8 -c "
                    "tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    "--psm 6",
                    "--psm 4",
                ]

                for config in configs:
                    text = pytesseract.image_to_string(
                        img, config=config
                    ).strip()
                    if text:
                        results.append(text)

            elif target_type == "multiplier":
                # Testar múltiplos PSMs como o sistema antigo (comprovado)
                configs = [
                    "--psm 7 -c tessedit_char_whitelist=0123456789.xX "
                    "--dpi 300",
                    "--psm 8 -c tessedit_char_whitelist=0123456789.xX "
                    "--dpi 300",
                    "--psm 6 -c tessedit_char_whitelist=0123456789.xX "
                    "--dpi 300",
                ]

                for config in configs:
                    text = pytesseract.image_to_string(
                        img, config=config
                    ).strip()
                    if text and any(c.isdigit() for c in text):
                        results.append(text)

            else:
                text = pytesseract.image_to_string(img).strip()
                if text:
                    results.append(text)

        except Exception as e:
            self.logger.error(f"Erro pytesseract: {e}")

        return results

    def easyocr_extract(self, img: np.ndarray) -> List[str]:
        """Extração com EasyOCR como fallback"""
        if not self.easyocr_reader:
            return []

        try:
            results = self.easyocr_reader.readtext(img)
            texts = []
            for bbox, text, confidence in results:
                if float(confidence) > 0.5:
                    texts.append(text)
            return texts
        except Exception as e:
            self.logger.error(f"Erro EasyOCR: {e}")
            return []

    def detect_balance_with_templates(
        self, gray_img: np.ndarray
    ) -> Optional[float]:
        """Template matching para saldo usando cache"""
        try:
            if not self.template_cache:
                return self.fallback_ocr_balance(gray_img)

            height, width = gray_img.shape
            resized = cv2.resize(
                gray_img,
                (width * 2, height * 2),
                interpolation=cv2.INTER_CUBIC
            )
            _, binary = cv2.threshold(resized, 128, 255, cv2.THRESH_BINARY)

            detections = []
            threshold = 0.7

            for char, template in self.template_cache.items():
                result = cv2.matchTemplate(
                    binary, template, cv2.TM_CCOEFF_NORMED
                )
                locations = np.where(result >= threshold)

                for pt in zip(*locations[::-1]):
                    confidence = result[pt[1], pt[0]]
                    detections.append({
                        "char": char,
                        "x": pt[0],
                        "y": pt[1],
                        "confidence": confidence
                    })

            if not detections:
                return self.fallback_ocr_balance(gray_img)

            filtered_detections = []
            sorted_dets = sorted(
                detections, key=lambda d: d["confidence"], reverse=True
            )
            for det in sorted_dets:
                overlap = False
                for filtered in filtered_detections:
                    x_dist = abs(det["x"] - filtered["x"])
                    y_dist = abs(det["y"] - filtered["y"])
                    if x_dist < 15 and y_dist < 10:
                        overlap = True
                        break

                if not overlap:
                    filtered_detections.append(det)

            filtered_detections.sort(key=lambda d: d["x"])

            balance_chars = [det["char"] for det in filtered_detections]
            balance_str = "".join(balance_chars)

            if not balance_str:
                return self.fallback_ocr_balance(gray_img)

            candidates = self.generate_balance_candidates(balance_str)

            for candidate in candidates:
                try:
                    value = float(candidate)
                    if 0.01 <= value <= 1000000:
                        return value
                except ValueError:
                    continue

            return self.fallback_ocr_balance(gray_img)

        except Exception:
            return self.fallback_ocr_balance(gray_img)

    def fallback_ocr_balance(self, gray_img: np.ndarray) -> Optional[float]:
        """OCR fallback para saldo com múltiplas tentativas"""
        try:
            texts = self.pytesseract_extract(gray_img, "balance")

            for text in texts:
                cleaned = self.clean_balance_text_simple(text)
                if cleaned:
                    try:
                        value = float(cleaned)
                        if 0.01 <= value <= 1000000:
                            return value
                    except ValueError:
                        continue

            if self.easyocr_reader:
                easyocr_texts = self.easyocr_extract(gray_img)
                for text in easyocr_texts:
                    cleaned = self.clean_balance_text_simple(text)
                    if cleaned:
                        try:
                            value = float(cleaned)
                            if 0.01 <= value <= 1000000:
                                return value
                        except ValueError:
                            continue

            return None

        except Exception:
            return None

    def clean_balance_text_simple(self, text: str) -> Optional[str]:
        """Limpeza de texto para saldo com mais casos"""
        if not text:
            return None

        text = text.replace("R$", "").replace("R", "")
        text = text.replace("$", "").replace(" ", "")
        text = text.replace("O", "0").replace("l", "1")
        text = text.replace("I", "1").replace("S", "5")
        text = text.replace("o", "0").replace("B", "8").replace("G", "6")

        text = text.replace(",", ".")

        if text.count(".") > 1:
            parts = text.split(".")
            text = "".join(parts[:-1]) + "." + parts[-1]

        if not text or not any(c.isdigit() for c in text):
            return None

        if "." not in text and text.isdigit():
            if len(text) == 3:
                # 3 digitos: pode ser XXX (ex: 301) ou X.XX (ex: 5.12)
                # Priorizar XX.X para saldos (mais provavel que X.XX)
                return f"{text[:2]}.{text[2]}"
            elif len(text) in {4, 5, 6}:
                return f"{text[:-2]}.{text[-2:]}"
        return text

    def generate_balance_candidates(self, detected_str: str) -> List[str]:
        """Gera candidatos de saldo com mais variações"""
        candidates = [detected_str]

        if "." not in detected_str and detected_str.isdigit():
            digits = detected_str

            if len(digits) == 3:
                candidates.extend([
                    f"{digits[0]}.{digits[1:]}",
                    f"{digits[:2]}.{digits[2]}"
                ])

            elif len(digits) == 4:
                candidates.extend([
                    f"{digits[:2]}.{digits[2:]}",
                    f"{digits[:3]}.{digits[3]}",
                    f"{digits[0]}.{digits[1:]}",
                ])

            elif len(digits) == 5:
                candidates.extend([
                    f"{digits[:3]}.{digits[3:]}",
                    f"{digits[:4]}.{digits[4]}",
                    f"{digits[:2]}.{digits[2:]}",
                ])

            elif len(digits) == 6:
                candidates.extend([
                    f"{digits[:4]}.{digits[4:]}",
                    f"{digits[:3]}.{digits[3:]}"
                ])

        elif "." in detected_str:
            parts = detected_str.split(".")
            if len(parts) == 2:
                left, right = parts
                all_digits = left + right

                for i in range(1, len(all_digits)):
                    new_candidate = f"{all_digits[:i]}.{all_digits[i:]}"
                    candidates.append(new_candidate)

        unique_candidates = []
        for candidate in candidates:
            if candidate not in unique_candidates and candidate:
                try:
                    float(candidate)
                    unique_candidates.append(candidate)
                except ValueError:
                    pass

        return unique_candidates

    def parse_value_with_context(self, text: str) -> Optional[float]:
        """Parse de multiplicador SEM imposições 7↔1"""
        if not text:
            return None

        with contextlib.suppress(Exception):
            text = text.upper().replace("X", "").strip()

            text = text.replace("O", "0").replace("I", "1").replace("L", "1")
            text = text.replace("S", "5").replace("B", "8").replace("G", "6")

            if " " in text:
                parts = text.split()
                if len(parts) == 2 and parts[0].isdigit() and "." in parts[1]:
                    text = parts[0] + parts[1]
                else:
                    text = text.replace(" ", "")

            if not text or not any(c.isdigit() for c in text):
                return None

            cleaned = "".join(
                char for char in text if char.isdigit() or char == "."
            )
            text = cleaned

            if not text:
                return None

            # Inserir ponto decimal quando OCR nao detecta
            # 95%+ dos crashes sao 1.00-9.99 (formato X.XX)
            if "." not in text:
                if len(text) <= 3:
                    # 3 digitos: X.XX (ex: "192" -> "1.92")
                    # 2 digitos: X.X  (ex: "19" -> "1.9")
                    if len(text) >= 2:
                        text = text[0] + "." + text[1:]
                elif len(text) == 4:
                    # 4 digitos: tentar X.XX primeiro (mais comum)
                    # "1920" -> "1.920" = 1.92 (nao "19.20")
                    # Se valor > 9.99, tentar XX.XX
                    v_low = float(text[0] + "." + text[1:])
                    if 1.0 <= v_low <= 9.99:
                        text = text[0] + "." + text[1:]
                    else:
                        text = text[:2] + "." + text[2:]
                else:
                    # 5+ digitos: XX.XX ou XXX.XX (2 decimais do fim)
                    text = text[:-2] + "." + text[-2:]

            value = float(text)

            # Rejeitar valores absurdos baseado no historico
            min_exp, max_exp = self.get_expected_range()

            if value >= 40.0 and max_exp < 10.0:
                value /= 10

            elif 10.0 <= value < 20.0 and max_exp < 3.0:
                str_val = f"{value:.2f}"
                if str_val.startswith("1"):
                    new_val = float(str_val[1:])
                    if min_exp <= new_val <= max_exp:
                        value = new_val

            if 1.0 <= value <= 999.99:
                # Rejeitar leituras absurdas (ex: 92.0 quando historico ~2.0)
                if value > 15.0:
                    if not self.value_history:
                        return None  # Primeiro valor nao pode ser > 15
                    avg = sum(self.value_history) / len(self.value_history)
                    if value > avg * 8:
                        return None  # Muito acima do historico recente

                self.value_history.append(value)
                return round(value, 2)

        return None

    def get_expected_range(self) -> Tuple[float, float]:
        """Calcula faixa esperada baseada no histórico"""
        if not self.value_history:
            return (1.0, 2.5)

        recent_avg = sum(self.value_history) / len(self.value_history)

        if len(self.value_history) >= 3:
            recent_std = np.std(self.value_history)
            min_expected = max(1.0, recent_avg - recent_std)
            max_expected = recent_avg + recent_std * 1.5
        else:
            min_expected = max(1.0, recent_avg - 0.5)
            max_expected = recent_avg + 1.0

        return (float(min_expected), float(min(max_expected, 50.0)))

    def validate_balance_with_context(
        self, detected_balance: float, current_balance: Optional[float]
    ) -> Optional[float]:
        """Valida saldo com contexto mais inteligente"""
        if not current_balance or detected_balance is None:
            return detected_balance

        current = current_balance
        detected = detected_balance

        max_sequence_loss = current * 0.35
        max_realistic_gain = current * 2.0

        min_realistic = max(0.01, current - max_sequence_loss)
        max_realistic = current + max_realistic_gain

        absolute_min = current * 0.10
        absolute_max = current * 8.0

        min_realistic = max(min_realistic, absolute_min)
        max_realistic = min(max_realistic, absolute_max)

        if min_realistic <= detected <= max_realistic:
            return detected

        if detected > max_realistic:
            for divisor in [10, 100, 1000]:
                corrected = detected / divisor
                if min_realistic <= corrected <= max_realistic:
                    return corrected

        else:
            for multiplier in [10, 100]:
                corrected = detected * multiplier
                if min_realistic <= corrected <= max_realistic:
                    return corrected

        if current > 0:
            change_percent = abs(detected - current) / current * 100
            if change_percent > 70:
                return current
            return detected
        return detected

    # ═══════════════════════════════════════════════════════════════════
    # MÉTODOS PÚBLICOS PRINCIPAIS
    # ═══════════════════════════════════════════════════════════════════

    def get_balance(
        self, region: Dict, current_balance: Optional[float] = None
    ) -> Optional[float]:
        """Método principal para obter saldo"""
        try:
            img = self.capture_region(region)
            if img is None:
                return None

            gray = self.preprocess_for_ocr(img, "balance")

            balance = self.detect_balance_with_templates(gray)
            if balance:
                validated = self.validate_balance_with_context(
                    balance, current_balance
                )

                if validated != balance:
                    curr_str = (
                        f"{current_balance:.2f}" if current_balance else "None"
                    )
                    print(
                        f"DEBUG SALDO: Detectado={balance:.2f}, "
                        f"Validado={validated:.2f}, Atual={curr_str}"
                    )

                return validated

            return None

        except Exception as e:
            self.logger.error(f"Erro na detecção de saldo: {e}")
            return None

    def match_multiplier_with_templates(
        self, img: np.ndarray
    ) -> Optional[float]:
        """Identifica o multiplicador usando templates pré-carregados.
        Recebe imagem ORIGINAL (não preprocessada).
        Multi-scale: tenta varias escalas para suportar diferentes perfis.
        """
        if not self.multiplier_templates:
            return None

        # Converter para escala de cinza (aceita BGRA, BGR ou gray)
        if len(img.shape) >= 3:
            if img.shape[2] == 4:
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # Binarizar: digitos BRANCOS em fundo PRETO
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        h, w = binary.shape
        threshold = 0.82

        # Multi-scale: tenta escala original, depois alternativas
        scales = [1.0, 0.95, 0.90, 1.05, 1.10]

        all_matches = []  # [(x, char, score, tw)]
        for scale in scales:
            scale_matches = []
            for char, tmpl in self.multiplier_templates.items():
                if tmpl is None:
                    continue

                # Redimensionar template se necessario
                if scale != 1.0:
                    new_h = max(1, int(tmpl.shape[0] * scale))
                    new_w = max(1, int(tmpl.shape[1] * scale))
                    interp = (cv2.INTER_AREA if scale < 1.0
                              else cv2.INTER_LINEAR)
                    s_tmpl = cv2.resize(
                        tmpl, (new_w, new_h),
                        interpolation=interp)
                else:
                    s_tmpl = tmpl

                th, tw = s_tmpl.shape
                if tw > w or th > h:
                    continue

                res = cv2.matchTemplate(
                    binary, s_tmpl, cv2.TM_CCOEFF_NORMED)

                locations = np.where(res >= threshold)
                for py, px in zip(*locations):
                    score = res[py, px]
                    scale_matches.append((px, char, score, tw))

            if scale_matches:
                all_matches = scale_matches
                break  # Usa a primeira escala que encontra matches

        if not all_matches:
            return None

        # 2. Ordenar por posição x
        all_matches.sort(key=lambda m: m[0])

        # 3. Greedy: para cada posição, escolher o melhor char (non-max suppression)
        result = []
        last_x_end = -1
        i = 0
        while i < len(all_matches):
            px, char, score, tw = all_matches[i]

            # Pular se sobrepõe com match anterior
            if px < last_x_end:
                # Verificar se é melhor que o match anterior na mesma posição
                if result and abs(px - result[-1][0]) < 5:
                    if score > result[-1][2]:
                        result[-1] = (px, char, score, tw)
                i += 1
                continue

            # Encontrar o melhor match nesta posição (dentro de 5px)
            best = (px, char, score, tw)
            j = i + 1
            while j < len(all_matches) and all_matches[j][0] < px + 5:
                if all_matches[j][2] > best[2]:
                    best = all_matches[j]
                j += 1

            # Desempate 3 vs 5
            bx, bchar, bscore, btw = best
            if bchar in ['3', '5']:
                # Extrair ROI para desambiguação
                th_max = max(t.shape[0] for t in self.multiplier_templates.values() if t is not None)
                # Encontrar melhor y para o ROI
                for tmpl_c in [self.multiplier_templates.get('3'), self.multiplier_templates.get('5')]:
                    if tmpl_c is not None:
                        r = cv2.matchTemplate(binary, tmpl_c, cv2.TM_CCOEFF_NORMED)
                        _, _, _, max_loc = cv2.minMaxLoc(r)
                        if abs(max_loc[0] - bx) < 5:
                            th_t, tw_t = tmpl_c.shape
                            roi_y = max_loc[1]
                            roi = binary[roi_y:roi_y+th_t, bx:bx+tw_t]
                            if roi.shape[0] > 0 and roi.shape[1] > 0:
                                bchar = self._disambiguate_3_vs_5(roi)
                            break

            result.append((bx, bchar, bscore, btw))
            last_x_end = bx + btw
            i = j if j > i + 1 else i + 1

        if result:
            val_str = "".join([r[1] for r in result])
            with contextlib.suppress(ValueError):
                # Inserir ponto decimal (95%+ dos crashes sao X.XX)
                if "." not in val_str:
                    if len(val_str) <= 3 and len(val_str) >= 2:
                        val_str = val_str[0] + "." + val_str[1:]
                    elif len(val_str) == 4:
                        v_low = float(val_str[0] + "." + val_str[1:])
                        if 1.0 <= v_low <= 9.99:
                            val_str = val_str[0] + "." + val_str[1:]
                        else:
                            val_str = val_str[:2] + "." + val_str[2:]
                    elif len(val_str) >= 5:
                        val_str = val_str[:-2] + "." + val_str[-2:]

                if val_str.count(".") <= 1 and len(val_str) >= 3:
                    val = float(val_str)
                    if 1.0 <= val <= 999.99:
                        return round(val, 2)
        return None

    def get_multiplier(self, region: Dict) -> Optional[float]:
        """Método principal para obter multiplicador.

        Pipeline comprovado (sistema antigo):
        1. OCR (pytesseract) em imagem 3x + BINARY_INV  → mais preciso
        2. Template matching na resolução original       → mais rápido (fallback)
        3. EasyOCR como último recurso
        """
        try:
            img = self.capture_region(region)
            if img is None:
                return None

            # 1. OCR (comprovado preciso no sistema antigo)
            #    3x resize + BINARY_INV = texto preto em fundo branco
            binary = self.preprocess_for_ocr(img, "multiplier")
            texts = self.pytesseract_extract(binary, "multiplier")

            for text in texts:
                value = self.parse_value_with_context(text)
                if value:
                    return value

            # 2. Template matching como fallback
            value = self.match_multiplier_with_templates(img)
            if value:
                return value

            # 3. EasyOCR último recurso
            if self.easyocr_reader:
                easyocr_texts = self.easyocr_extract(binary)
                for text in easyocr_texts:
                    value = self.parse_value_with_context(text)
                    if value:
                        return value

            return None

        except Exception as e:
            self.logger.error(f"Erro na detecção de multiplicador: {e}")
            return None

    def detect_bet_text(self, region: Dict) -> bool:
        """
        Detecta fase de apostas.

        Aceita:
        - Texto "APOSTA"/"BET" (botão de aposta)
        - Countdown digits 1-9 (timer azul/branco "3", "7", etc.)
        - Texto com "s" (ex: "8s", "3s")
        """
        try:
            img = self.capture_region(region)
            if img is None:
                return False

            binary = self.preprocess_for_ocr(img, "bet_detection")

            # --- Método 1: OCR para texto "APOSTA"/"BET" ---
            texts = self.pytesseract_extract(binary, "bet_detection")
            for text in texts:
                text_clean = text.upper().strip()
                aposta_keywords = [
                    "APOSTA",
                    "APOSTAR",
                    "APOSTE",
                    "BET",
                    "APOST",
                    "POSTA",
                ]
                if any(keyword in text_clean for keyword in aposta_keywords):
                    return True

            # --- Método 2: Detectar countdown (dígitos 1-9) ---
            # A área pode capturar o timer "3", "7", "Bet 8s", etc.
            digit_configs = [
                "--psm 8 -c tessedit_char_whitelist=0123456789s --dpi 300",
                "--psm 7 -c tessedit_char_whitelist=0123456789sBet --dpi 300",
            ]
            for config in digit_configs:
                try:
                    text = pytesseract.image_to_string(binary, config=config).strip()
                    if text:
                        cleaned = text.replace("s", "").replace("S", "")
                        cleaned = cleaned.replace("B", "").replace("e", "").replace("t", "")
                        cleaned = cleaned.strip()
                        if cleaned.isdigit() and 1 <= int(cleaned) <= 15:
                            return True
                except Exception:
                    pass

            # --- Método 3: EasyOCR fallback ---
            if self.easyocr_reader:
                easyocr_texts = self.easyocr_extract(binary)
                for text in easyocr_texts:
                    text_clean = text.upper().strip()
                    aposta_keywords = [
                        "APOSTA", "APOSTAR", "APOSTE",
                        "BET", "APOST", "POSTA",
                    ]
                    if any(kw in text_clean for kw in aposta_keywords):
                        return True
                    # Countdown via EasyOCR
                    cleaned = text.strip().replace("s", "").replace("S", "")
                    if cleaned.isdigit() and 1 <= int(cleaned) <= 9:
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Erro na detecção de APOSTA: {e}")
            return False

    def debug_save_capture(
        self, region: Dict, filename: str = "debug_capture.png"
    ):
        """Salva captura para debug"""
        try:
            img = self.capture_region(region)
            if img is not None:
                cv2.imwrite(filename, img)
                print(f"Debug: Captura salva em {filename}")
        except Exception as e:
            print(f"Erro ao salvar debug: {e}")

    def get_stats(self) -> Dict:
        """Retorna estatísticas do sistema de visão"""
        return {
            "templates_loaded": len(self.template_cache),
            "easyocr_available": EASYOCR_AVAILABLE,
            "value_history_size": len(self.value_history),
            "recent_values": list(self.value_history),
        }
