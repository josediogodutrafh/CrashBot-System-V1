#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - DETECTOR (Orquestrador de Visão)

Combina captura de tela e template matching para detectar
elementos do jogo e emitir eventos.

Uso:
    from engine.vision.detector import GameDetector, get_detector

    detector = get_detector()
    detector.load_profile("Monitor 1")
    detector.start()

    # Leituras manuais
    balance = detector.read_balance()
    multiplier = detector.read_multiplier()
    is_bet_open = detector.is_bet_window_open()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Core imports
from core.events import BotEvent, emit

# Imports internos
from engine.vision.capture import CaptureRegion, ScreenCapture, get_capture
from engine.vision.templates import TemplateEngine, TemplateSet, get_templates

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ScreenProfile:
    """Perfil de configuração de tela."""

    name: str

    # Áreas de captura
    multiplier_area: Optional[CaptureRegion] = None
    bet_area: Optional[CaptureRegion] = None
    balance_area: Optional[CaptureRegion] = None
    history_area: Optional[CaptureRegion] = None

    # Pontos de clique - Aposta 1
    bet_value_click_1: Optional[Tuple[int, int]] = None
    target_click_1: Optional[Tuple[int, int]] = None
    bet_button_click_1: Optional[Tuple[int, int]] = None

    # Pontos de clique - Aposta 2
    bet_value_click_2: Optional[Tuple[int, int]] = None
    target_click_2: Optional[Tuple[int, int]] = None
    bet_button_click_2: Optional[Tuple[int, int]] = None

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ScreenProfile":
        """Cria perfil a partir de dicionário (config.json)."""
        profile = cls(name=name)

        # Áreas de captura
        if area := data.get("multiplier_area"):
            profile.multiplier_area = CaptureRegion(
                x=area["x"],
                y=area["y"],
                width=area["width"],
                height=area["height"],
                name="multiplier",
            )

        if area := data.get("bet_area"):
            profile.bet_area = CaptureRegion(
                x=area["x"],
                y=area["y"],
                width=area["width"],
                height=area["height"],
                name="bet_window",
            )

        if area := data.get("balance_area"):
            profile.balance_area = CaptureRegion(
                x=area["x"],
                y=area["y"],
                width=area["width"],
                height=area["height"],
                name="balance",
            )

        if area := data.get("history_area"):
            profile.history_area = CaptureRegion(
                x=area["x"],
                y=area["y"],
                width=area["width"],
                height=area["height"],
                name="history",
            )

        # Pontos de clique - Aposta 1
        if pt := data.get("bet_value_click_1"):
            profile.bet_value_click_1 = (pt["x"], pt["y"])

        if pt := data.get("target_click_1"):
            profile.target_click_1 = (pt["x"], pt["y"])

        if pt := data.get("bet_button_click_1"):
            profile.bet_button_click_1 = (pt["x"], pt["y"])

        # Pontos de clique - Aposta 2
        if pt := data.get("bet_value_click_2"):
            profile.bet_value_click_2 = (pt["x"], pt["y"])

        if pt := data.get("target_click_2"):
            profile.target_click_2 = (pt["x"], pt["y"])

        if pt := data.get("bet_button_click_2"):
            profile.bet_button_click_2 = (pt["x"], pt["y"])

        return profile


@dataclass
class DetectionResult:
    """Resultado de uma detecção."""

    success: bool
    value: Any = None
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# GAME DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════


class GameDetector:
    """
    Detector principal do jogo.

    Orquestra captura de tela e template matching para:
    - Ler multiplicador atual
    - Ler saldo
    - Detectar janela de apostas ("Bet 8s")
    - Ler histórico de explosões

    Integrado com EventBus para emitir eventos automaticamente.

    Exemplo:
        detector = GameDetector()
        detector.load_profile_from_config("Monitor 1")
        detector.load_templates("assets/templates")

        # Leituras
        mult = detector.read_multiplier()
        balance = detector.read_balance()

        if detector.is_bet_window_open():
            print("Hora de apostar!")
    """

    def __init__(
        self,
        capture: Optional[ScreenCapture] = None,
        templates: Optional[TemplateEngine] = None,
        emit_events: bool = True,
    ):
        """
        Inicializa o detector.

        Args:
            capture: Instância de ScreenCapture (usa singleton se None)
            templates: Instância de TemplateEngine (usa singleton se None)
            emit_events: Se True, emite eventos no EventBus
        """
        self._capture = capture or get_capture()
        self._templates = templates or get_templates()
        self._emit_events = emit_events

        self._lock = threading.Lock()
        self._profile: Optional[ScreenProfile] = None
        self._templates_loaded = False

        # Cache de últimas leituras
        self._last_multiplier: Optional[float] = None
        self._last_balance: Optional[float] = None
        self._last_bet_window_state: bool = False

        # Configurações
        self._multiplier_threshold = 0.75
        self._balance_threshold = 0.75
        self._bet_window_threshold = 0.80

        logger.debug("GameDetector inicializado")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def load_profile(self, profile: ScreenProfile) -> None:
        """
        Carrega um perfil de tela.

        Args:
            profile: Objeto ScreenProfile com as configurações
        """
        with self._lock:
            self._profile = profile

        logger.info(f"Perfil carregado: {profile.name}")

    def load_profile_from_config(
        self,
        profile_name: str,
        config_path: str = "config.json",
    ) -> bool:
        """
        Carrega perfil do arquivo config.json.

        Args:
            profile_name: Nome do perfil
            config_path: Caminho do arquivo de configuração

        Returns:
            True se carregou com sucesso
        """
        import json

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            profiles = config.get("profiles", {})

            if profile_name not in profiles:
                logger.error(f"Perfil não encontrado: {profile_name}")
                return False

            profile_data = profiles[profile_name]
            profile = ScreenProfile.from_dict(profile_name, profile_data)

            self.load_profile(profile)
            return True

        except FileNotFoundError:
            logger.error(f"Arquivo não encontrado: {config_path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao ler JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao carregar perfil: {e}")
            return False

    def load_templates(self, templates_base_path: str = "assets/templates") -> bool:
        """
        Carrega todos os templates necessários.

        Args:
            templates_base_path: Pasta base dos templates

        Returns:
            True se carregou com sucesso
        """
        base = Path(templates_base_path)
        success = True

        # Templates do multiplicador central
        mult_path = base / "multiplier"
        if mult_path.exists():
            if not self._templates.load_digit_templates(
                str(mult_path), TemplateSet.MULTIPLIER_CENTRAL
            ):
                success = False
        else:
            logger.warning(f"Pasta não encontrada: {mult_path}")
            success = False

        # Templates do histórico (pills)
        hist_path = base / "history"
        if hist_path.exists():
            self._templates.load_digit_templates(
                str(hist_path), TemplateSet.MULTIPLIER_HISTORY
            )

        # Template especial: bet_8s
        bet_path = base / "special" / "bet_8s.png"
        if bet_path.exists():
            self._templates.load_special_template(str(bet_path), "bet_8s")
        else:
            logger.warning(f"Template não encontrado: {bet_path}")

        self._templates_loaded = success
        return success

    # ═══════════════════════════════════════════════════════════════════════════
    # LEITURA DE MULTIPLICADOR
    # ═══════════════════════════════════════════════════════════════════════════

    def read_multiplier(self) -> DetectionResult:
        """
        Lê o multiplicador atual da tela.

        Returns:
            DetectionResult com o valor lido
        """
        if not self._profile or not self._profile.multiplier_area:
            return DetectionResult(
                success=False, error="Área do multiplicador não configurada"
            )

        # Captura a região
        image = self._capture.capture(self._profile.multiplier_area)

        if image is None:
            return DetectionResult(success=False, error="Falha na captura de tela")

        # Lê o valor usando templates
        (
            value,
            confidence,
            matches,
        ) = self._templates.read_value_with_confidence(
            image, TemplateSet.MULTIPLIER_CENTRAL, self._multiplier_threshold
        )

        if value is None:
            return DetectionResult(
                success=False,
                confidence=confidence,
                error="Não foi possível ler o multiplicador",
            )

        # Valida range
        if not (1.0 <= value <= 1000.0):
            logger.warning(f"Multiplicador fora do range: {value}")
            return DetectionResult(
                success=False,
                value=value,
                confidence=confidence,
                error=f"Valor fora do range: {value}",
            )

        # Atualiza cache
        old_value = self._last_multiplier
        self._last_multiplier = value

        # Emite evento se mudou significativamente
        if self._emit_events and old_value != value:
            emit(
                BotEvent.MULTIPLIER_UPDATE,
                {
                    "value": value,
                    "confidence": confidence,
                    "old_value": old_value,
                },
            )

        return DetectionResult(success=True, value=value, confidence=confidence)

    def read_multiplier_multiple(
        self,
        num_reads: int = 3,
        interval: float = 0.05,
    ) -> DetectionResult:
        """
        Lê o multiplicador múltiplas vezes e usa votação.

        Args:
            num_reads: Número de leituras
            interval: Intervalo entre leituras (segundos)

        Returns:
            DetectionResult com valor mais frequente
        """
        readings: List[float] = []
        confidences: List[float] = []

        for _ in range(num_reads):
            result = self.read_multiplier()
            if result.success and result.value is not None:
                readings.append(result.value)
                confidences.append(result.confidence)
            time.sleep(interval)

        if not readings:
            return DetectionResult(success=False, error="Nenhuma leitura válida")

        # Votação: valor mais frequente
        counter = Counter(readings)
        most_common_value, count = counter.most_common(1)[0]

        avg_confidence = sum(confidences) / len(confidences)

        return DetectionResult(
            success=True, value=most_common_value, confidence=avg_confidence
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LEITURA DE SALDO
    # ═══════════════════════════════════════════════════════════════════════════

    def read_balance(self) -> DetectionResult:
        """
        Lê o saldo atual da tela.

        Returns:
            DetectionResult com o valor lido
        """
        if not self._profile or not self._profile.balance_area:
            return DetectionResult(success=False, error="Área do saldo não configurada")

        # Captura a região
        image = self._capture.capture(self._profile.balance_area)

        if image is None:
            return DetectionResult(success=False, error="Falha na captura de tela")

        # Lê o valor usando templates
        # Nota: Saldo usa mesmos templates do multiplicador
        (
            value,
            confidence,
            matches,
        ) = self._templates.read_value_with_confidence(
            image, TemplateSet.MULTIPLIER_CENTRAL, self._balance_threshold
        )

        if value is None:
            return DetectionResult(
                success=False,
                confidence=confidence,
                error="Não foi possível ler o saldo",
            )

        # Valida range
        if value < 0:
            return DetectionResult(
                success=False,
                value=value,
                confidence=confidence,
                error=f"Saldo negativo: {value}",
            )

        # Valida mudança drástica (possível erro de leitura)
        if self._last_balance is not None:
            diff = abs(value - self._last_balance)
            change_percent = (diff / self._last_balance) * 100
            if change_percent > 50:
                logger.warning(
                    f"Mudança drástica: {self._last_balance} -> {value} "
                    f"({change_percent:.1f}%)"
                )

        # Atualiza cache
        old_balance = self._last_balance
        self._last_balance = value

        # Emite evento se mudou
        if self._emit_events and old_balance != value:
            emit(
                BotEvent.BALANCE_CHANGED,
                {
                    "old": old_balance,
                    "new": value,
                    "confidence": confidence,
                },
            )

        return DetectionResult(success=True, value=value, confidence=confidence)

    # ═══════════════════════════════════════════════════════════════════════════
    # DETECÇÃO DE JANELA DE APOSTAS
    # ═══════════════════════════════════════════════════════════════════════════

    def is_bet_window_open(self) -> bool:
        """
        Verifica se a janela de apostas ("Bet 8s") está aberta.

        Returns:
            True se a janela está aberta
        """
        if not self._profile or not self._profile.bet_area:
            logger.warning("Área do Bet não configurada")
            return False

        # Captura a região
        image = self._capture.capture(self._profile.bet_area)

        if image is None:
            return False

        # Detecta template
        found, confidence = self._templates.detect_bet_window(
            image, self._bet_window_threshold
        )

        # Emite evento se estado mudou
        if self._emit_events and found != self._last_bet_window_state and found:
            emit(BotEvent.BET_WINDOW_OPEN, {"confidence": confidence})

        self._last_bet_window_state = found

        return found

    def wait_for_bet_window(
        self,
        timeout: float = 30.0,
        check_interval: float = 0.1,
    ) -> bool:
        """
        Aguarda a janela de apostas abrir.

        Args:
            timeout: Tempo máximo de espera (segundos)
            check_interval: Intervalo entre verificações

        Returns:
            True se a janela abriu dentro do timeout
        """
        start = time.time()

        while (time.time() - start) < timeout:
            if self.is_bet_window_open():
                return True
            time.sleep(check_interval)

        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # DETECÇÃO DE EXPLOSÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def detect_explosion(self) -> DetectionResult:
        """
        Detecta se houve uma explosão (fim da rodada).

        Verifica se o multiplicador parou de mudar ou se
        a janela de apostas apareceu.

        Returns:
            DetectionResult com o valor final da explosão
        """
        # Método 1: Janela de apostas apareceu
        if self.is_bet_window_open():
            return DetectionResult(
                success=True, value=self._last_multiplier, confidence=1.0
            )

        # Método 2: Poderia verificar mudança de cor, etc.
        # (implementar conforme necessidade)

        return DetectionResult(success=False, error="Explosão não detectada")

    # ═══════════════════════════════════════════════════════════════════════════
    # PONTOS DE CLIQUE
    # ═══════════════════════════════════════════════════════════════════════════

    def get_bet_value_click(self, slot: int = 1) -> Optional[Tuple[int, int]]:
        """Retorna coordenadas do campo de valor da aposta."""
        if not self._profile:
            return None

        if slot == 1:
            return self._profile.bet_value_click_1
        else:
            return self._profile.bet_value_click_2

    def get_target_click(self, slot: int = 1) -> Optional[Tuple[int, int]]:
        """Retorna coordenadas do campo de alvo (multiplicador)."""
        if not self._profile:
            return None

        if slot == 1:
            return self._profile.target_click_1
        else:
            return self._profile.target_click_2

    def get_bet_button_click(self, slot: int = 1) -> Optional[Tuple[int, int]]:
        """Retorna coordenadas do botão de aposta."""
        if not self._profile:
            return None

        if slot == 1:
            return self._profile.bet_button_click_1
        else:
            return self._profile.bet_button_click_2

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do detector."""
        return {
            "profile_loaded": self._profile is not None,
            "profile_name": self._profile.name if self._profile else None,
            "templates_loaded": self._templates_loaded,
            "last_multiplier": self._last_multiplier,
            "last_balance": self._last_balance,
            "bet_window_open": self._last_bet_window_state,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_game_detector: Optional[GameDetector] = None
_detector_lock = threading.Lock()


def get_detector() -> GameDetector:
    """
    Retorna a instância singleton do GameDetector.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _game_detector

    if _game_detector is None:
        with _detector_lock:
            if _game_detector is None:
                _game_detector = GameDetector()

    return _game_detector


def reset_detector() -> None:
    """Reseta o detector (útil para testes)."""
    global _game_detector
    with _detector_lock:
        _game_detector = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO GAME DETECTOR - CrashBot v3.0")
    print("=" * 60)

    # Cria detector
    detector = GameDetector(emit_events=False)
    print("\n✅ GameDetector criado")

    # Tenta carregar perfil
    print("\n--- Carregamento de Perfil ---")
    if detector.load_profile_from_config("Monitor 1"):
        print("   ✅ Perfil carregado")
    else:
        print("   ⚠️ Perfil não encontrado (normal se config.json não existe)")

    # Tenta carregar templates
    print("\n--- Carregamento de Templates ---")
    if detector.load_templates("assets/templates"):
        print("   ✅ Templates carregados")
    else:
        print("   ⚠️ Templates não encontrados")

    # Status
    print("\n--- Status ---")
    status = detector.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ TESTES BÁSICOS CONCLUÍDOS!")
    print("=" * 60)
