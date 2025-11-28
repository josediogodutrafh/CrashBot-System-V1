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
from config import BASE_DIR

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
        # Isso evita o erro 'object has no attribute logger'
        self.logger = logging.getLogger(__name__)

        # --- 2. ENCONTRA O TESSERACT MANUALMENTE (INFALÍVEL) ---
        # Calcula o caminho voltando pastas: .../src/vision -> .../src -> .../Crash (Raiz)
        vision_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(vision_dir)
        root_dir = os.path.dirname(src_dir)

        # Caminho exato onde a pasta Tesseract-OCR deve estar
        tesseract_path = os.path.join(root_dir, "Tesseract-OCR", "tesseract.exe")

        # Debug no terminal para você conferir
        print(f"🔎 VisionSystem procurando Tesseract em: {tesseract_path}")

        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            self.logger.info("✅ Tesseract portátil encontrado e configurado.")
        else:
            self.logger.warning(f"❌ Tesseract NÃO encontrado em: {tesseract_path}")
            self.logger.warning("Tentando usar variável de ambiente do sistema...")
            # Tenta usar o do sistema se o portátil falhar
            pytesseract.pytesseract.tesseract_cmd = "tesseract"

        # --- 3. CONFIGURAÇÃO E CAMINHOS (Código Original) ---
        self.config_path = config_path
        self.config = self.load_config()

        # --- LÓGICA HÍBRIDA DE CAMINHOS PARA TEMPLATES ---
        # Tenta encontrar a pasta de templates em locais comuns
        possible_paths = [
            os.path.join(vision_dir, "templates", "template_saldo"),
            os.path.join(root_dir, "src", "vision", "templates", "template_saldo"),
            os.path.join(root_dir, "templates", "template_saldo"),
        ]

        # Seleciona o primeiro caminho que existe
        self.template_path = next(
            (p for p in possible_paths if os.path.exists(p)), possible_paths[0]
        )

        # --- 4. PRÉ-CARREGAMENTO DOS TEMPLATES ---
        self.template_cache = self.load_templates(str(self.template_path))

        # AQUI TERMINA O SNIPPET (A próxima função é _load_multiplier_templates)
        # O resto das inicializações (EasyOCR, etc) será chamado logo abaixo se você mantiver

        # ATENÇÃO: Certifique-se de manter a chamada para carregar os templates de multiplicador!
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

        print("✅ VisionSystem inicializado")

    def _load_multiplier_templates(self) -> dict:
        """Carrega os templates de dígitos do multiplicador uma única vez."""
        templates = {}

        # --- LÓGICA HÍBRIDA PARA MULTIPLICADOR ---
        possible_paths = [
            # Opção 1: Estrutura de Desenvolvimento
            os.path.join(BASE_DIR, "src", "vision", "templates", "templates_debug"),
            # Opção 2: Estrutura Alternativa
            os.path.join(BASE_DIR, "vision", "templates", "templates_debug"),
            # Opção 3: Estrutura de Distribuição (.exe)
            os.path.join(BASE_DIR, "templates", "templates_debug"),
        ]

        # Seleciona o caminho correto
        template_dir_path = next(
            (p for p in possible_paths if os.path.exists(p)), possible_paths[0]
        )
        template_dir = Path(template_dir_path)

        if not template_dir.is_dir():
            self.logger.error(
                f"Diretório de templates de multiplicador não encontrado em nenhum local: {template_dir}"
            )
            return {}

        # Carrega os dígitos de 0 a 9
        for d in range(10):
            path = template_dir / f"{d}.png"
            if path.exists():
                templates[str(d)] = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

        # Carrega o ponto
        ponto_path = template_dir / "ponto.png"
        if ponto_path.exists():
            templates["."] = cv2.imread(str(ponto_path), cv2.IMREAD_GRAYSCALE)

        self.logger.info(f"{len(templates)} templates de multiplicador carregados.")
        return templates

    def load_config(self) -> Dict:
        """Carrega config.json existente"""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erro ao carregar {self.config_path}: {e}")
            return {}

    def load_balance_corrections(self) -> Dict:
        """Carrega correções aprendidas (compatível com código original)"""
        try:
            path = os.path.join(BASE_DIR, "balance_corrections.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"❌ Erro ao carregar correções: {e}")
        return {}

    # Dentro da classe VisionSystem, em src/vision/vision_system.py

    def load_templates(self, template_path: str) -> Dict[str, np.ndarray]:
        """
        Carrega todos os templates de imagem de um diretório específico (para o saldo)
        e os retorna em um dicionário (cache).
        """
        # 1. Cria um dicionário LOCAL para armazenar os templates
        cache: Dict[str, np.ndarray] = {}

        # Usa pathlib para uma verificação mais robusta
        template_dir = Path(template_path)

        try:
            # 2. Verifica se o diretório existe
            if not template_dir.is_dir():
                self.logger.warning(
                    f"Diretório de template de saldo não encontrado: {template_path}"
                )
                return cache  # Retorna o cache vazio se o diretório não existir

            # 3. Carregar dígitos 0-9
            for digit in range(10):
                # Procura por "00.png", "01.png", etc.
                template_file = template_dir / f"{digit:02d}.png"
                if template_file.exists():
                    template = cv2.imread(str(template_file), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        cache[str(digit)] = template
                # (Opcional: adicione um else para avisar se um dígito estiver faltando)

            # 4. Carregar ponto decimal
            # O código antigo procurava por 'o.png', verifique se é esse o nome do seu arquivo
            point_file = template_dir / "ponto.png"
            if point_file.exists():
                point_template = cv2.imread(str(point_file), cv2.IMREAD_GRAYSCALE)
                if point_template is not None:
                    cache["."] = point_template

            self.logger.info(
                f"✅ Templates de saldo carregados: {len(cache)} items de {template_path}"
            )

        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar templates de saldo: {e}")

        # 5. RETORNA o dicionário local
        return cache

    def capture_region(self, region: Dict) -> Optional[np.ndarray]:
        """Captura região da tela (função base do código original)"""
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
        """✅ CORRIGIDO: Pré-processamento otimizado para texto claro em fundo escuro."""

        # Garante que a imagem está em escala de cinza (8-bit)
        if len(img.shape) >= 3:
            if img.shape[2] == 4:  # Se for BGRA
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            else:  # Se for BGR
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # --- LÓGICA ESPECÍFICA PARA O MULTIPLICADOR ---
        if target_type == "balance":
            scale_factor = 3
            gray = cv2.resize(
                gray,
                (gray.shape[1] * scale_factor, gray.shape[0] * scale_factor),
                interpolation=cv2.INTER_CUBIC,
            )
            gray = cv2.medianBlur(gray, 3)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary

        elif target_type == "bet_detection":
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
            return binary

        elif target_type == "multiplier":
            # Aumenta o tamanho para melhorar a precisão do OCR
            gray_resized = cv2.resize(
                gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
            )

            # ✅ PRESCRIÇÃO PRINCIPAL: Binarização Invertida
            # O texto do jogo é claro (amarelo) e o fundo é escuro.
            # THRESH_BINARY_INV transforma os pixels claros (texto) em PRETO
            # e os pixels escuros (fundo) em BRANCO.
            # O OCR do Tesseract funciona muito melhor com texto preto em fundo branco.
            _, binary = cv2.threshold(
                src=gray_resized,
                thresh=150,  # Limiar de brilho. Pode ser ajustado (ex: 120 ou 180)
                maxval=255,
                type=cv2.THRESH_BINARY_INV,
            )
            return binary

        return gray

    def pytesseract_extract(
        self, img: np.ndarray, target_type: str = "general"
    ) -> List[str]:
        """✅ OTIMIZADO: Extração com pytesseract com configs melhorados"""
        results = []

        try:
            if target_type == "balance":
                # ✅ OTIMIZADO: Múltiplos métodos para saldo com configs melhores
                configs = [
                    "--psm 8 -c tessedit_char_whitelist=0123456789., --dpi 300",
                    "--psm 7 -c tessedit_char_whitelist=0123456789., --dpi 300",
                    "--psm 6 -c tessedit_char_whitelist=0123456789., --dpi 300",
                    "--psm 13 -c tessedit_char_whitelist=0123456789., --dpi 300",
                ]

                for config in configs:
                    text = pytesseract.image_to_string(img, config=config).strip()
                    if text and any(c.isdigit() for c in text):
                        results.append(text)

                # Tentar com inversão se não obteve resultados
                if not results:
                    inverted = cv2.bitwise_not(img)
                    for config in configs[:2]:  # Apenas os 2 primeiros
                        text = pytesseract.image_to_string(
                            inverted, config=config
                        ).strip()
                        if text and any(c.isdigit() for c in text):
                            results.append(text)

            elif target_type == "bet_detection":
                # ✅ AJUSTE PONTUAL: Para detecção de APOSTA com configs melhorados
                configs = [
                    "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    "--psm 6",
                    "--psm 4",  # ✅ NOVO: Modo multi-linha para textos complexos
                ]

                for config in configs:
                    if text := pytesseract.image_to_string(img, config=config).strip():
                        results.append(text)

            elif target_type == "multiplier":
                # ✅ OTIMIZADO: Para multiplicador com configs específicos
                configs = [
                    "--psm 7 -c tessedit_char_whitelist=0123456789.xX --dpi 300",
                    "--psm 8 -c tessedit_char_whitelist=0123456789.xX --dpi 300",
                    "--psm 6 -c tessedit_char_whitelist=0123456789.xX --dpi 300",
                ]

                for config in configs:
                    text = pytesseract.image_to_string(img, config=config).strip()
                    if text and any(c.isdigit() for c in text):
                        results.append(text)

            elif text := pytesseract.image_to_string(img).strip():
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
            texts.extend(
                text for bbox, text, confidence in results if float(confidence) > 0.5
            )
            return texts
        except Exception as e:
            self.logger.error(f"Erro EasyOCR: {e}")
            return []

    def detect_balance_with_templates(self, gray_img: np.ndarray) -> Optional[float]:
        """✅ OTIMIZADO: Template matching para saldo usando cache"""
        try:
            # ✅ OTIMIZAÇÃO: Usar templates do cache
            if not self.template_cache:
                return self.fallback_ocr_balance(gray_img)

            # Redimensionar para melhor matching
            height, width = gray_img.shape
            resized = cv2.resize(
                gray_img, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC
            )
            _, binary = cv2.threshold(resized, 128, 255, cv2.THRESH_BINARY)

            # Template matching
            detections = []
            threshold = 0.7

            for char, template in self.template_cache.items():
                result = cv2.matchTemplate(binary, template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= threshold)

                for pt in zip(*locations[::-1]):
                    confidence = result[pt[1], pt[0]]
                    detections.append(
                        {"char": char, "x": pt[0], "y": pt[1], "confidence": confidence}
                    )

            if not detections:
                return self.fallback_ocr_balance(gray_img)

            # ✅ OTIMIZAÇÃO: Filtrar sobreposições mais eficiente
            filtered_detections = []
            for det in sorted(detections, key=lambda d: d["confidence"], reverse=True):
                overlap = False
                for filtered in filtered_detections:
                    x_dist = abs(det["x"] - filtered["x"])
                    y_dist = abs(det["y"] - filtered["y"])
                    if x_dist < 15 and y_dist < 10:
                        overlap = True
                        break

                if not overlap:
                    filtered_detections.append(det)

            # Ordenar por posição X
            filtered_detections.sort(key=lambda d: d["x"])

            # Construir string
            balance_chars = [det["char"] for det in filtered_detections]
            balance_str = "".join(balance_chars)

            if not balance_str:
                return self.fallback_ocr_balance(gray_img)

            # Gerar candidatos e validar
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
        """✅ OTIMIZADO: OCR fallback para saldo com múltiplas tentativas"""
        try:
            # Tentar pytesseract primeiro
            texts = self.pytesseract_extract(gray_img, "balance")

            for text in texts:
                if cleaned := self.clean_balance_text_simple(text):
                    try:
                        value = float(cleaned)
                        if 0.01 <= value <= 1000000:
                            return value
                    except ValueError:
                        continue

            # Se pytesseract falhou, tentar EasyOCR
            if self.easyocr_reader:
                easyocr_texts = self.easyocr_extract(gray_img)
                for text in easyocr_texts:
                    if cleaned := self.clean_balance_text_simple(text):
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
        """✅ OTIMIZADO: Limpeza de texto para saldo com mais casos"""
        if not text:
            return None

        # Remover caracteres inválidos
        text = text.replace("R$", "").replace("R", "").replace("$", "").replace(" ", "")
        text = (
            text.replace("O", "0").replace("l", "1").replace("I", "1").replace("S", "5")
        )
        text = text.replace("o", "0").replace("B", "8").replace("G", "6")

        # Normalizar vírgula para ponto
        text = text.replace(",", ".")

        # Se tem múltiplos pontos, manter apenas o último
        if text.count(".") > 1:
            parts = text.split(".")
            text = "".join(parts[:-1]) + "." + parts[-1]

        # Validar que contém apenas números e um ponto
        if not text or not any(c.isdigit() for c in text):
            return None

        # ✅ OTIMIZAÇÃO: Melhor lógica para inserir ponto decimal
        if "." not in text and text.isdigit():
            if len(text) == 3:
                return f"{text[0]}.{text[1:]}"
            elif len(text) in {4, 5, 6}:
                return f"{text[:-2]}.{text[-2:]}"
        return text

    def generate_balance_candidates(self, detected_str: str) -> List[str]:
        # sourcery skip: use-contextlib-suppress
        """✅ OTIMIZADO: Gera candidatos de saldo com mais variações"""
        candidates = [detected_str]

        # Se não tem ponto, tentar inserir em posições típicas
        if "." not in detected_str and detected_str.isdigit():
            digits = detected_str

            if len(digits) == 3:
                candidates.extend(
                    [f"{digits[0]}.{digits[1:]}", f"{digits[:2]}.{digits[2]}"]
                )

            elif len(digits) == 4:
                candidates.extend(
                    [
                        f"{digits[:2]}.{digits[2:]}",
                        f"{digits[:3]}.{digits[3]}",
                        f"{digits[0]}.{digits[1:]}",
                    ]
                )

            elif len(digits) == 5:
                candidates.extend(
                    [
                        f"{digits[:3]}.{digits[3:]}",
                        f"{digits[:4]}.{digits[4]}",
                        f"{digits[:2]}.{digits[2:]}",
                    ]
                )

            elif len(digits) == 6:
                candidates.extend(
                    [f"{digits[:4]}.{digits[4:]}", f"{digits[:3]}.{digits[3:]}"]
                )

        # Se tem ponto, tentar mover posição
        elif "." in detected_str:
            parts = detected_str.split(".")
            if len(parts) == 2:
                left, right = parts
                all_digits = left + right

                # Tentar diferentes posições do ponto
                for i in range(1, len(all_digits)):
                    new_candidate = f"{all_digits[:i]}.{all_digits[i:]}"
                    candidates.append(new_candidate)

        # Remover duplicados e candidatos inválidos
        unique_candidates = []
        for candidate in candidates:
            if candidate not in unique_candidates and candidate:
                try:
                    float(candidate)  # Validar se é um número válido
                    unique_candidates.append(candidate)
                except ValueError:
                    pass

        return unique_candidates

    def parse_value_with_context(self, text: str) -> Optional[float]:
        """❌ LIMPO: Parse de multiplicador SEM imposições 7↔1"""
        if not text:
            return None

        with contextlib.suppress(Exception):
            # Limpar texto básico
            text = text.upper().replace("X", "").strip()

            # ✅ OTIMIZAÇÃO: Remover mais caracteres problemáticos
            text = text.replace("O", "0").replace("I", "1").replace("L", "1")
            text = text.replace("S", "5").replace("B", "8").replace("G", "6")

            # Se tem espaços, pode ser número >100 mal interpretado
            if " " in text:
                parts = text.split()
                if len(parts) == 2 and parts[0].isdigit() and "." in parts[1]:
                    text = parts[0] + parts[1]
                else:
                    text = text.replace(" ", "")

            if not text or not any(c.isdigit() for c in text):
                return None

            cleaned = "".join(char for char in text if char.isdigit() or char == ".")
            text = cleaned

            if not text:
                return None

            # ❌ REMOVIDO: Correções pré-conversão com 7→1
            # Manter apenas correções de formato básicas
            if "." not in text:
                if len(text) == 3:
                    text = f"{text[0]}.{text[1:]}"
                elif len(text) == 4:
                    text = f"{text[0]}.{text[1:3]}"

            value = float(text)

            # ✅ OTIMIZAÇÃO: Correções pós-conversão com contexto melhorado
            min_exp, max_exp = self.get_expected_range()

            # ❌ REMOVIDO: Correção 7.XX ↔ 1.XX (OCR livre para detectar)

            # Outras correções otimizadas (mantidas)
            if value >= 40.0 and max_exp < 10.0:
                value /= 10

            elif 10.0 <= value < 20.0 and max_exp < 3.0:
                str_val = f"{value:.2f}"
                if str_val.startswith("1"):
                    new_val = float(str_val[1:])
                    if min_exp <= new_val <= max_exp:
                        value = new_val

            # ✅ OTIMIZAÇÃO: Validação final mais rigorosa
            if 1.0 <= value <= 999.99:
                self.value_history.append(value)
                return round(value, 2)

        return None

    def get_expected_range(self) -> Tuple[float, float]:
        """✅ OTIMIZADO: Calcula faixa esperada baseada no histórico"""
        if not self.value_history:
            return (1.0, 2.5)

        recent_avg = sum(self.value_history) / len(self.value_history)

        # ✅ OTIMIZAÇÃO: Faixa mais dinâmica baseada na variação recente
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
        """✅ OTIMIZADO: Valida saldo com contexto mais inteligente"""
        if not current_balance or detected_balance is None:
            return detected_balance

        current = current_balance
        detected = detected_balance

        # ✅ OTIMIZAÇÃO: Calcular faixa realística mais inteligente
        # Considerar padrões de apostas típicos do Martingale
        max_sequence_loss = current * 0.35  # Máximo 35% em uma sequência de apostas
        max_realistic_gain = current * 2.0  # Máximo ganho realístico

        min_realistic = max(0.01, current - max_sequence_loss)
        max_realistic = current + max_realistic_gain

        # Limites absolutos de segurança
        absolute_min = current * 0.10
        absolute_max = current * 8.0

        min_realistic = max(min_realistic, absolute_min)
        max_realistic = min(max_realistic, absolute_max)

        # Validação
        if min_realistic <= detected <= max_realistic:
            return detected

        # ✅ OTIMIZAÇÃO: Correções por contexto mais precisas
        if detected > max_realistic:
            # Tentar divisões
            for divisor in [10, 100, 1000]:
                corrected = detected / divisor
                if min_realistic <= corrected <= max_realistic:
                    return corrected

        else:
            # Tentar multiplicações
            for multiplier in [10, 100]:
                corrected = detected * multiplier
                if min_realistic <= corrected <= max_realistic:
                    return corrected

        # Se mudança muito drástica, ser mais conservador
        if current > 0:
            change_percent = abs(detected - current) / current * 100
            return current if change_percent > 70 else detected
        return detected

    # ═══════════════════════════════════════════════════════════════════
    # MÉTODOS PÚBLICOS PRINCIPAIS - OTIMIZADOS
    # ═══════════════════════════════════════════════════════════════════

    def get_balance(
        self, region: Dict, current_balance: Optional[float] = None
    ) -> Optional[float]:
        """✅ OTIMIZADO: Método principal para obter saldo com debug"""
        try:
            img = self.capture_region(region)
            if img is None:
                return None

            gray = self.preprocess_for_ocr(img, "balance")

            if balance := self.detect_balance_with_templates(gray):
                # Validar com contexto
                validated = self.validate_balance_with_context(balance, current_balance)

                # ✅ DEBUG: Log do processo
                if validated != balance:
                    print(
                        f"DEBUG SALDO: Detectado={balance:.2f}, Validado={validated:.2f}, Atual={current_balance:.2f if current_balance else 'None'}"
                    )

                return validated

            return None

        except Exception as e:
            self.logger.error(f"Erro na detecção de saldo: {e}")
            return None

    def match_multiplier_with_templates(self, img: np.ndarray) -> Optional[float]:
        """Tenta identificar o multiplicador usando templates pré-carregados."""
        # Se os templates não foram carregados, não há o que fazer.
        if not self.multiplier_templates:
            return None

        # Pré-processar imagem para template matching
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        h, w = binary.shape
        result = []
        x = 0
        while x < w:
            best_score = 0
            best_char = None
            best_template = None

            # Usa os templates da memória (self.multiplier_templates), não do disco
            for char, tmpl in self.multiplier_templates.items():
                if tmpl is None:
                    continue  # Segurança caso um template falhe ao carregar
                th, tw = tmpl.shape
                if x + tw > w or 0 + th > h:  # Adicionado checagem de altura
                    continue
                roi = binary[0:th, x : x + tw]

                # Comparação de tamanho é crucial
                if roi.shape != tmpl.shape:
                    continue

                res = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)
                score = res[0][0]
                if score > best_score and score > 0.92:
                    best_score = score
                    best_char = char
                    best_template = tmpl

            if best_char and best_template is not None:
                result.append(best_char)
                x += best_template.shape[1]
            else:
                x += 1

        # Reconstruir valor
        if result:
            val_str = "".join(result)
            # logger.debug(f"[DEBUG TEMPLATE MATCHING] Valor reconstruído: {val_str}")
            with contextlib.suppress(ValueError):
                if val_str.count(".") <= 1 and len(val_str) >= 3:
                    val = float(val_str)
                    if 1.0 <= val <= 999.99:
                        return round(val, 2)
        return None

    def get_multiplier(self, region: Dict) -> Optional[float]:
        """OTIMIZADO: Método principal para obter multiplicador com debug e template matching"""
        try:
            img = self.capture_region(region)
            if img is None:
                return None

            binary = self.preprocess_for_ocr(img, "multiplier")

            if value := self.match_multiplier_with_templates(binary):
                return value

            # Tentar pytesseract primeiro
            texts = self.pytesseract_extract(binary, "multiplier")

            for text in texts:
                if value := self.parse_value_with_context(text):
                    return value

            # Fallback para EasyOCR se disponível
            if self.easyocr_reader:
                easyocr_texts = self.easyocr_extract(binary)
                for text in easyocr_texts:
                    if value := self.parse_value_with_context(text):
                        return value

            return None

        except Exception as e:
            self.logger.error(f"Erro na detecção de multiplicador: {e}")
            return None

    def detect_bet_text(self, region: Dict) -> bool:
        """✅ AJUSTE PONTUAL: Detecta 'APOSTA' com melhor precisão e debug"""
        try:
            img = self.capture_region(region)
            if img is None:
                return False

            binary = self.preprocess_for_ocr(img, "bet_detection")

            # ✅ AJUSTE: Pytesseract com configs específicos para APOSTA
            texts = self.pytesseract_extract(binary, "bet_detection")
            for text in texts:
                text_clean = text.upper().strip()
                # ✅ AJUSTE: Mais variações de APOSTA
                aposta_keywords = [
                    "APOSTA",
                    "APOSTAR",
                    "APOSTE",
                    "BET",
                    "APOST",
                    "POSTA",
                ]
                if any(keyword in text_clean for keyword in aposta_keywords):
                    print(f"✅ APOSTA detectada (Tesseract): '{text_clean}'")
                    return True

            # ✅ AJUSTE: EasyOCR fallback com debug
            if self.easyocr_reader:
                easyocr_texts = self.easyocr_extract(binary)
                for text in easyocr_texts:
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
                        print(f"✅ APOSTA detectada (EasyOCR): '{text_clean}'")
                        return True

            # ✅ AJUSTE: Debug quando não detecta (só a cada 10 tentativas para não spam)
            if not hasattr(self, "_debug_counter"):
                self._debug_counter = 0
            self._debug_counter += 1

            if self._debug_counter % 10 == 0:
                print(f"⚠️ APOSTA não detectada. Textos encontrados: {texts}")

            return False

        except Exception as e:
            self.logger.error(f"Erro na detecção de APOSTA: {e}")
            return False

    def debug_save_capture(self, region: Dict, filename: str = "debug_capture.png"):
        """✅ NOVO: Salva captura para debug"""
        try:
            img = self.capture_region(region)
            if img is not None:
                cv2.imwrite(filename, img)
                print(f"✅ Debug: Captura salva em {filename}")
        except Exception as e:
            print(f"❌ Erro ao salvar debug: {e}")

    def get_stats(self) -> Dict:
        """✅ NOVO: Retorna estatísticas do sistema de visão"""
        return {
            "templates_loaded": len(self.template_cache),
            "easyocr_available": EASYOCR_AVAILABLE,
            "value_history_size": len(self.value_history),
            "recent_values": list(self.value_history),
        }
