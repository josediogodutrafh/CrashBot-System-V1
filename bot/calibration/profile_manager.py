#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false

"""
CRASHBOT v3.0 - PROFILE MANAGER

Gerenciador de perfis de calibração.
Salva e carrega configurações de regiões e pontos de clique.

Uso:
    from calibration.profile_manager import ProfileManager, get_profile_manager

    manager = get_profile_manager()

    # Listar perfis
    profiles = manager.list_profiles()

    # Carregar perfil
    profile = manager.load("brabet")

    # Salvar perfil
    manager.save(profile)

    # Deletar perfil
    manager.delete("brabet")
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RegionConfig:
    """Configuração de uma região de captura."""

    x: int = 0
    y: int = 0
    width: int = 100
    height: int = 50

    def to_dict(self) -> Dict[str, int]:
        """Converte para dicionário."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "RegionConfig":
        """Cria a partir de dicionário."""
        return cls(
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 100),
            height=data.get("height", 50),
        )

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Retorna como tupla (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    def is_valid(self) -> bool:
        """Verifica se a região é válida."""
        return self.width > 0 and self.height > 0


@dataclass
class ClickPoint:
    """Configuração de um ponto de clique."""

    x: int = 0
    y: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Converte para dicionário."""
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, int]]) -> Optional["ClickPoint"]:
        """Cria a partir de dicionário."""
        if data is None:
            return None
        return cls(x=data.get("x", 0), y=data.get("y", 0))

    def to_tuple(self) -> Tuple[int, int]:
        """Retorna como tupla (x, y)."""
        return (self.x, self.y)


@dataclass
class ColorConfig:
    """Configuração de cor para detecção."""

    r: int = 0
    g: int = 0
    b: int = 0
    tolerance: int = 30

    def to_dict(self) -> Dict[str, int]:
        """Converte para dicionário."""
        return {
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "tolerance": self.tolerance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "ColorConfig":
        """Cria a partir de dicionário."""
        return cls(
            r=data.get("r", 0),
            g=data.get("g", 0),
            b=data.get("b", 0),
            tolerance=data.get("tolerance", 30),
        )

    def to_tuple(self) -> Tuple[int, int, int]:
        """Retorna como tupla RGB."""
        return (self.r, self.g, self.b)

    def matches(self, r: int, g: int, b: int) -> bool:
        """Verifica se uma cor corresponde dentro da tolerância."""
        return (
            abs(self.r - r) <= self.tolerance
            and abs(self.g - g) <= self.tolerance
            and abs(self.b - b) <= self.tolerance
        )


@dataclass
class OCRConfig:
    """Configuração de OCR para uma região."""

    psm: int = 7  # Page segmentation mode
    whitelist: str = "0123456789."

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {"psm": self.psm, "whitelist": self.whitelist}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OCRConfig":
        """Cria a partir de dicionário."""
        return cls(
            psm=data.get("psm", 7),
            whitelist=data.get("whitelist", "0123456789."),
        )


@dataclass
class CalibrationProfile:
    """Perfil completo de calibração."""

    # Identificação
    name: str = "default"
    platform: str = "Brabet"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Resolução da tela
    screen_width: int = 1920
    screen_height: int = 1080

    # Regiões de captura
    balance_area: Optional[RegionConfig] = None
    timer_area: Optional[RegionConfig] = None
    history_area: Optional[RegionConfig] = None
    multiplier_area: Optional[RegionConfig] = None
    bet_button_area: Optional[RegionConfig] = None
    bet_value_area: Optional[RegionConfig] = None
    target_multiplier_area: Optional[RegionConfig] = None

    # Pontos de clique - Aposta 1
    bet_value_click_1: Optional[ClickPoint] = None
    target_click_1: Optional[ClickPoint] = None
    bet_button_click_1: Optional[ClickPoint] = None

    # Pontos de clique - Aposta 2
    bet_value_click_2: Optional[ClickPoint] = None
    target_click_2: Optional[ClickPoint] = None
    bet_button_click_2: Optional[ClickPoint] = None

    # Cores de detecção
    button_bet_ready: Optional[ColorConfig] = None
    button_waiting: Optional[ColorConfig] = None

    # Configurações OCR
    ocr_balance: Optional[OCRConfig] = None
    ocr_timer: Optional[OCRConfig] = None
    ocr_multiplier: Optional[OCRConfig] = None

    def __post_init__(self) -> None:
        """Inicializa valores padrão após criação."""
        # Cores padrão do Brabet
        if self.button_bet_ready is None:
            self.button_bet_ready = ColorConfig(r=239, g=68, b=68, tolerance=30)

        if self.button_waiting is None:
            self.button_waiting = ColorConfig(r=34, g=197, b=94, tolerance=30)

        # OCR padrão
        if self.ocr_balance is None:
            self.ocr_balance = OCRConfig(psm=7, whitelist="0123456789.,")

        if self.ocr_timer is None:
            self.ocr_timer = OCRConfig(psm=7, whitelist="0123456789Bets ")

        if self.ocr_multiplier is None:
            self.ocr_multiplier = OCRConfig(psm=7, whitelist="0123456789.x")

    def to_dict(self) -> Dict[str, Any]:
        """Converte perfil para dicionário (para salvar em JSON)."""
        return {
            # Identificação
            "name": self.name,
            "platform": self.platform,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat(),
            # Resolução
            "screen_resolution": [self.screen_width, self.screen_height],
            # Regiões
            "regions": {
                "balance_area": (
                    self.balance_area.to_dict() if self.balance_area else None
                ),
                "timer_area": (self.timer_area.to_dict() if self.timer_area else None),
                "history_area": (
                    self.history_area.to_dict() if self.history_area else None
                ),
                "multiplier_area": (
                    self.multiplier_area.to_dict() if self.multiplier_area else None
                ),
                "bet_button_area": (
                    self.bet_button_area.to_dict() if self.bet_button_area else None
                ),
                "bet_value_area": (
                    self.bet_value_area.to_dict() if self.bet_value_area else None
                ),
                "target_multiplier_area": (
                    self.target_multiplier_area.to_dict()
                    if self.target_multiplier_area
                    else None
                ),
            },
            # Pontos de clique
            "click_points": {
                "bet_value_click_1": (
                    self.bet_value_click_1.to_dict() if self.bet_value_click_1 else None
                ),
                "target_click_1": (
                    self.target_click_1.to_dict() if self.target_click_1 else None
                ),
                "bet_button_click_1": (
                    self.bet_button_click_1.to_dict()
                    if self.bet_button_click_1
                    else None
                ),
                "bet_value_click_2": (
                    self.bet_value_click_2.to_dict() if self.bet_value_click_2 else None
                ),
                "target_click_2": (
                    self.target_click_2.to_dict() if self.target_click_2 else None
                ),
                "bet_button_click_2": (
                    self.bet_button_click_2.to_dict()
                    if self.bet_button_click_2
                    else None
                ),
            },
            # Cores
            "colors": {
                "button_bet_ready": (
                    self.button_bet_ready.to_dict() if self.button_bet_ready else None
                ),
                "button_waiting": (
                    self.button_waiting.to_dict() if self.button_waiting else None
                ),
            },
            # OCR
            "ocr_config": {
                "balance": (self.ocr_balance.to_dict() if self.ocr_balance else None),
                "timer": self.ocr_timer.to_dict() if self.ocr_timer else None,
                "multiplier": (
                    self.ocr_multiplier.to_dict() if self.ocr_multiplier else None
                ),
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationProfile":
        """Cria perfil a partir de dicionário (carregado de JSON)."""
        profile = cls(
            name=data.get("name", "default"),
            platform=data.get("platform", "Brabet"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )

        # Resolução
        resolution = data.get("screen_resolution", [1920, 1080])
        profile.screen_width = resolution[0]
        profile.screen_height = resolution[1]

        # Regiões
        regions = data.get("regions", {})

        if regions.get("balance_area"):
            profile.balance_area = RegionConfig.from_dict(regions["balance_area"])

        if regions.get("timer_area"):
            profile.timer_area = RegionConfig.from_dict(regions["timer_area"])

        if regions.get("history_area"):
            profile.history_area = RegionConfig.from_dict(regions["history_area"])

        if regions.get("multiplier_area"):
            profile.multiplier_area = RegionConfig.from_dict(regions["multiplier_area"])

        if regions.get("bet_button_area"):
            profile.bet_button_area = RegionConfig.from_dict(regions["bet_button_area"])

        if regions.get("bet_value_area"):
            profile.bet_value_area = RegionConfig.from_dict(regions["bet_value_area"])

        if regions.get("target_multiplier_area"):
            profile.target_multiplier_area = RegionConfig.from_dict(
                regions["target_multiplier_area"]
            )

        # Pontos de clique
        clicks = data.get("click_points", {})

        profile.bet_value_click_1 = ClickPoint.from_dict(
            clicks.get("bet_value_click_1")
        )
        profile.target_click_1 = ClickPoint.from_dict(clicks.get("target_click_1"))
        profile.bet_button_click_1 = ClickPoint.from_dict(
            clicks.get("bet_button_click_1")
        )
        profile.bet_value_click_2 = ClickPoint.from_dict(
            clicks.get("bet_value_click_2")
        )
        profile.target_click_2 = ClickPoint.from_dict(clicks.get("target_click_2"))
        profile.bet_button_click_2 = ClickPoint.from_dict(
            clicks.get("bet_button_click_2")
        )

        # Cores
        colors = data.get("colors", {})

        if colors.get("button_bet_ready"):
            profile.button_bet_ready = ColorConfig.from_dict(colors["button_bet_ready"])

        if colors.get("button_waiting"):
            profile.button_waiting = ColorConfig.from_dict(colors["button_waiting"])

        # OCR
        ocr = data.get("ocr_config", {})

        if ocr.get("balance"):
            profile.ocr_balance = OCRConfig.from_dict(ocr["balance"])

        if ocr.get("timer"):
            profile.ocr_timer = OCRConfig.from_dict(ocr["timer"])

        if ocr.get("multiplier"):
            profile.ocr_multiplier = OCRConfig.from_dict(ocr["multiplier"])

        return profile

    def get_calibration_status(self) -> Dict[str, bool]:
        """Retorna status de calibração de cada elemento."""
        return {
            "balance": self.balance_area is not None and self.balance_area.is_valid(),
            "timer": self.timer_area is not None and self.timer_area.is_valid(),
            "history": self.history_area is not None and self.history_area.is_valid(),
            "multiplier": (
                self.multiplier_area is not None and self.multiplier_area.is_valid()
            ),
            "bet_button": (
                self.bet_button_area is not None and self.bet_button_area.is_valid()
            ),
            "bet_value_click": self.bet_value_click_1 is not None,
            "target_click": self.target_click_1 is not None,
            "bet_button_click": self.bet_button_click_1 is not None,
        }

    def get_completion_percentage(self) -> float:
        """Retorna porcentagem de calibração completa."""
        status = self.get_calibration_status()
        total = len(status)
        completed = sum(1 for v in status.values() if v)
        return (completed / total) * 100 if total > 0 else 0.0

    def to_detector_format(self) -> Dict[str, Any]:
        """
        Converte para formato compatível com ScreenProfile do detector.

        Usado para integrar com engine/vision/detector.py
        """
        result: Dict[str, Any] = {}

        # Regiões
        if self.multiplier_area:
            result["multiplier_area"] = self.multiplier_area.to_dict()

        if self.bet_button_area:
            result["bet_area"] = self.bet_button_area.to_dict()

        if self.balance_area:
            result["balance_area"] = self.balance_area.to_dict()

        if self.history_area:
            result["history_area"] = self.history_area.to_dict()

        # Pontos de clique
        if self.bet_value_click_1:
            result["bet_value_click_1"] = self.bet_value_click_1.to_dict()

        if self.target_click_1:
            result["target_click_1"] = self.target_click_1.to_dict()

        if self.bet_button_click_1:
            result["bet_button_click_1"] = self.bet_button_click_1.to_dict()

        if self.bet_value_click_2:
            result["bet_value_click_2"] = self.bet_value_click_2.to_dict()

        if self.target_click_2:
            result["target_click_2"] = self.target_click_2.to_dict()

        if self.bet_button_click_2:
            result["bet_button_click_2"] = self.bet_button_click_2.to_dict()

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════


class ProfileManager:
    """
    Gerenciador de perfis de calibração.

    Salva e carrega perfis em arquivos JSON na pasta profiles/.

    Exemplo:
        manager = ProfileManager()

        # Criar novo perfil
        profile = CalibrationProfile(name="brabet", platform="Brabet")
        profile.balance_area = RegionConfig(x=650, y=105, width=80, height=25)

        # Salvar
        manager.save(profile)

        # Carregar
        loaded = manager.load("brabet")

        # Listar
        profiles = manager.list_profiles()
    """

    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Inicializa o gerenciador.

        Args:
            profiles_dir: Diretório dos perfis. Se None, usa calibration/profiles/
        """
        if profiles_dir is None:
            # Usa calibration/profiles/ relativo ao arquivo atual
            self._profiles_dir = Path(__file__).parent / "profiles"
        else:
            self._profiles_dir = Path(profiles_dir)

        # Cria diretório se não existir
        self._profiles_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()

        logger.debug(f"ProfileManager inicializado: {self._profiles_dir}")

    @property
    def profiles_dir(self) -> Path:
        """Retorna o diretório de perfis."""
        return self._profiles_dir

    def list_profiles(self) -> List[str]:
        """
        Lista todos os perfis disponíveis.

        Returns:
            Lista de nomes de perfis (sem extensão .json)
        """
        profiles = []

        for file in self._profiles_dir.glob("*.json"):
            profiles.append(file.stem)

        return sorted(profiles)

    def list_profiles_for_platform(self, platform: str) -> List[str]:
        """Lista perfis filtrados por plataforma."""
        result = []
        for name in self.list_profiles():
            profile = self.load(name)
            if profile and profile.platform == platform:
                result.append(name)
        return result

    def exists(self, name: str) -> bool:
        """
        Verifica se um perfil existe.

        Args:
            name: Nome do perfil

        Returns:
            True se o perfil existe
        """
        file_path = self._profiles_dir / f"{name}.json"
        return file_path.exists()

    def load(self, name: str) -> Optional[CalibrationProfile]:
        """
        Carrega um perfil do disco.

        Args:
            name: Nome do perfil (sem extensão)

        Returns:
            CalibrationProfile ou None se não encontrado
        """
        file_path = self._profiles_dir / f"{name}.json"

        if not file_path.exists():
            logger.warning(f"Perfil não encontrado: {name}")
            return None

        try:
            with self._lock:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            profile = CalibrationProfile.from_dict(data)
            logger.info(f"Perfil carregado: {name}")
            return profile

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON do perfil {name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao carregar perfil {name}: {e}")
            return None

    def save(self, profile: CalibrationProfile) -> bool:
        """
        Salva um perfil no disco.

        Args:
            profile: Perfil a salvar

        Returns:
            True se salvou com sucesso
        """
        file_path = self._profiles_dir / f"{profile.name}.json"

        try:
            data = profile.to_dict()

            with self._lock:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Perfil salvo: {profile.name}")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar perfil {profile.name}: {e}")
            return False

    def delete(self, name: str) -> bool:
        """
        Deleta um perfil.

        Args:
            name: Nome do perfil

        Returns:
            True se deletou com sucesso
        """
        file_path = self._profiles_dir / f"{name}.json"

        if not file_path.exists():
            logger.warning(f"Perfil não encontrado para deletar: {name}")
            return False

        try:
            with self._lock:
                file_path.unlink()

            logger.info(f"Perfil deletado: {name}")
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar perfil {name}: {e}")
            return False

    def duplicate(
        self, source_name: str, new_name: str
    ) -> Optional[CalibrationProfile]:
        """
        Duplica um perfil existente.

        Args:
            source_name: Nome do perfil origem
            new_name: Nome do novo perfil

        Returns:
            Novo perfil ou None se falhou
        """
        source = self.load(source_name)

        if source is None:
            return None

        # Cria cópia com novo nome
        source.name = new_name
        source.created_at = datetime.now().isoformat()
        source.updated_at = datetime.now().isoformat()

        if self.save(source):
            return source

        return None

    def get_profile_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações resumidas de um perfil.

        Args:
            name: Nome do perfil

        Returns:
            Dicionário com informações ou None
        """
        profile = self.load(name)

        if profile is None:
            return None

        return {
            "name": profile.name,
            "platform": profile.platform,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "resolution": f"{profile.screen_width}x{profile.screen_height}",
            "completion": f"{profile.get_completion_percentage():.0f}%",
            "status": profile.get_calibration_status(),
        }

    def create_default_profile(self, name: str = "brabet") -> CalibrationProfile:
        """
        Cria um perfil padrão para Brabet.

        Args:
            name: Nome do perfil

        Returns:
            Novo perfil com valores padrão
        """
        profile = CalibrationProfile(
            name=name,
            platform="Brabet",
            screen_width=1920,
            screen_height=1080,
        )

        # Valores estimados para Brabet (serão ajustados na calibração)
        profile.balance_area = RegionConfig(x=650, y=105, width=80, height=25)
        profile.timer_area = RegionConfig(x=280, y=400, width=200, height=60)
        profile.history_area = RegionConfig(x=75, y=240, width=560, height=35)
        profile.bet_button_area = RegionConfig(x=460, y=755, width=170, height=55)

        return profile


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_profile_manager: Optional[ProfileManager] = None
_manager_lock = threading.Lock()


def get_profile_manager() -> ProfileManager:
    """
    Retorna a instância singleton do ProfileManager.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _profile_manager

    if _profile_manager is None:
        with _manager_lock:
            if _profile_manager is None:
                _profile_manager = ProfileManager()

    return _profile_manager


def reset_profile_manager() -> None:
    """Reseta o ProfileManager (útil para testes)."""
    global _profile_manager
    with _manager_lock:
        _profile_manager = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO PROFILE MANAGER - CrashBot v3.0")
    print("=" * 60)

    # Cria manager
    manager = ProfileManager()
    print(f"\n📁 Diretório de perfis: {manager.profiles_dir}")

    # Lista perfis existentes
    print("\n--- Perfis Existentes ---")
    profiles = manager.list_profiles()
    if profiles:
        for p in profiles:
            print(f"   • {p}")
    else:
        print("   (nenhum perfil encontrado)")

    # Cria perfil de teste
    print("\n--- Criando Perfil de Teste ---")
    profile = manager.create_default_profile("teste_brabet")
    print(f"   Nome: {profile.name}")
    print(f"   Plataforma: {profile.platform}")
    print(f"   Resolução: {profile.screen_width}x{profile.screen_height}")
    print(f"   Completude: {profile.get_completion_percentage():.0f}%")

    # Salva
    print("\n--- Salvando Perfil ---")
    if manager.save(profile):
        print("   ✅ Perfil salvo com sucesso")
    else:
        print("   ❌ Erro ao salvar")

    # Carrega
    print("\n--- Carregando Perfil ---")
    loaded = manager.load("teste_brabet")
    if loaded:
        print(f"   ✅ Perfil carregado: {loaded.name}")
        print(f"   Status: {loaded.get_calibration_status()}")
    else:
        print("   ❌ Erro ao carregar")

    # Info
    print("\n--- Informações do Perfil ---")
    info = manager.get_profile_info("teste_brabet")
    if info:
        for key, value in info.items():
            print(f"   {key}: {value}")

    # Cleanup
    print("\n--- Limpeza ---")
    if manager.delete("teste_brabet"):
        print("   ✅ Perfil de teste deletado")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
