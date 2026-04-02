#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - EXECUTOR DE APOSTAS

Executa apostas através de cliques e digitação automatizada.
Integra com o sistema de visão para coordenadas calibradas.

Uso:
    from engine.trading.executor import BetExecutor, get_executor

    executor = get_executor()
    executor.load_profile_from_config("Monitor 1")

    # Executa aposta
    result = executor.place_bet(amount=10.0, target=1.85)

    if result.success:
        print("Aposta realizada!")
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# PyAutoGUI para automação
try:
    import pyautogui

    pyautogui.FAILSAFE = True  # Move mouse para canto = para tudo
    pyautogui.PAUSE = 0.05  # Pequena pausa entre ações
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False
    pyautogui = None

# Core imports
from core.events import BotEvent, emit
from core.state import get_state

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class BetSlot(Enum):
    """Slots de aposta disponíveis."""

    SLOT_1 = 1
    SLOT_2 = 2


class ExecutionStatus(Enum):
    """Status da execução."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    NO_BALANCE = "no_balance"


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ClickPoint:
    """Ponto de clique na tela."""

    x: int
    y: int
    name: str = ""

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)


@dataclass
class ExecutorProfile:
    """Perfil de coordenadas do executor."""

    # Slot 1
    bet_value_1: ClickPoint = None
    target_value_1: ClickPoint = None
    bet_button_1: ClickPoint = None

    # Slot 2
    bet_value_2: ClickPoint = None
    target_value_2: ClickPoint = None
    bet_button_2: ClickPoint = None

    # Outras áreas
    cancel_button: Optional[ClickPoint] = None
    cashout_button: Optional[ClickPoint] = None

    @classmethod
    def from_config(
        cls, config: Dict[str, Any], monitor_name: str
    ) -> "ExecutorProfile":
        """Carrega perfil de config.json."""
        monitors = config.get("monitors", {})
        monitor_config = monitors.get(monitor_name, {})

        def get_point(key: str) -> Optional[ClickPoint]:
            data = monitor_config.get(key)
            if data and len(data) >= 2:
                return ClickPoint(x=int(data[0]), y=int(data[1]), name=key)
            return None

        return cls(
            bet_value_1=get_point("bet_value_click_1"),
            target_value_1=get_point("target_click_1"),
            bet_button_1=get_point("bet_button_click_1"),
            bet_value_2=get_point("bet_value_click_2"),
            target_value_2=get_point("target_click_2"),
            bet_button_2=get_point("bet_button_click_2"),
        )


@dataclass
class BetResult:
    """Resultado de uma aposta."""

    success: bool
    status: ExecutionStatus
    slot: BetSlot
    amount: float
    target: float
    execution_time: float
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ExecutorConfig:
    """Configuração do executor."""

    # Delays
    click_delay: float = 0.1  # Delay após clique
    type_delay: float = 0.05  # Delay entre teclas
    action_delay: float = 0.2  # Delay entre ações

    # Timeouts
    bet_window_timeout: float = 10.0  # Timeout esperando janela de apostas

    # Comportamento
    clear_before_type: bool = True  # Limpa campo antes de digitar
    verify_after_bet: bool = True  # Verifica se aposta foi feita
    humanize_delays: bool = True  # Adiciona variação aos delays

    # Limites de segurança
    max_bet_amount: float = 1000.0  # Máximo valor de aposta
    min_bet_amount: float = 1.0  # Mínimo valor de aposta


# ═══════════════════════════════════════════════════════════════════════════════
# BET EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════


class BetExecutor:
    """
    Executor de apostas automatizadas.

    Realiza:
    - Cliques em coordenadas calibradas
    - Digitação de valores
    - Confirmação de apostas
    - Cashout automático

    Features:
    - Dois slots de aposta independentes
    - Delays humanizados
    - Verificação pós-aposta
    - Integração com EventBus

    Exemplo:
        executor = BetExecutor()
        executor.load_profile_from_config("Monitor 1")

        # Aposta simples
        result = executor.place_bet(amount=10.0, target=1.85)

        # Aposta em slot específico
        result = executor.place_bet(amount=10.0, target=1.85, slot=BetSlot.SLOT_2)
    """

    def __init__(
        self,
        config: Optional[ExecutorConfig] = None,
        emit_events: bool = True,
    ):
        """
        Inicializa o executor.

        Args:
            config: Configuração do executor
            emit_events: Se True, emite eventos no EventBus
        """
        if not HAS_PYAUTOGUI:
            raise ImportError(
                "PyAutoGUI não encontrado. Instale com: pip install pyautogui"
            )

        self._lock = threading.Lock()
        self._config = config or ExecutorConfig()
        self._emit_events = emit_events

        # Perfil de coordenadas
        self._profile: Optional[ExecutorProfile] = None

        # Estado
        self._is_betting = False
        self._last_bet: Optional[BetResult] = None
        self._active_bets: Dict[BetSlot, Dict] = {}

        # Estatísticas
        self._stats = {
            "total_bets": 0,
            "successful_bets": 0,
            "failed_bets": 0,
            "total_amount_bet": 0.0,
        }

        logger.info("BetExecutor inicializado")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def load_profile(self, profile: ExecutorProfile) -> None:
        """Carrega perfil de coordenadas."""
        with self._lock:
            self._profile = profile
        logger.info("Perfil do executor carregado")

    def load_profile_from_config(
        self, monitor_name: str, config_path: str = "config.json"
    ) -> bool:
        """
        Carrega perfil de arquivo de configuração.

        Args:
            monitor_name: Nome do monitor no config
            config_path: Caminho do arquivo config.json

        Returns:
            True se carregou com sucesso
        """
        try:
            import json

            with open(config_path, "r") as f:
                config = json.load(f)

            profile = ExecutorProfile.from_config(config, monitor_name)
            self.load_profile(profile)

            logger.info(f"Perfil carregado de {config_path} para {monitor_name}")
            return True

        except Exception as e:
            logger.error(f"Erro ao carregar perfil: {e}")
            return False

    def configure(
        self,
        click_delay: Optional[float] = None,
        type_delay: Optional[float] = None,
        humanize: Optional[bool] = None,
        max_bet: Optional[float] = None,
    ) -> None:
        """Configura parâmetros do executor."""
        with self._lock:
            if click_delay is not None:
                self._config.click_delay = click_delay
            if type_delay is not None:
                self._config.type_delay = type_delay
            if humanize is not None:
                self._config.humanize_delays = humanize
            if max_bet is not None:
                self._config.max_bet_amount = max_bet

    # ═══════════════════════════════════════════════════════════════════════════
    # AÇÕES BÁSICAS
    # ═══════════════════════════════════════════════════════════════════════════

    def _humanize_delay(self, base_delay: float) -> float:
        """Adiciona variação humana ao delay."""
        if self._config.humanize_delays:
            variation = base_delay * 0.3  # ±30%
            return base_delay + random.uniform(-variation, variation)
        return base_delay

    def _click(self, point: ClickPoint, clicks: int = 1) -> bool:
        """
        Executa clique em um ponto.

        Args:
            point: Ponto de clique
            clicks: Número de cliques

        Returns:
            True se clicou com sucesso
        """
        try:
            pyautogui.click(
                x=point.x,
                y=point.y,
                clicks=clicks,
            )

            time.sleep(self._humanize_delay(self._config.click_delay))

            logger.debug(f"Clique em {point.name} ({point.x}, {point.y})")
            return True

        except Exception as e:
            logger.error(f"Erro ao clicar em {point.name}: {e}")
            return False

    def _double_click(self, point: ClickPoint) -> bool:
        """Executa duplo clique."""
        return self._click(point, clicks=2)

    def _type_value(self, value: str, clear_first: bool = True) -> bool:
        """
        Digita um valor no campo atual.

        Args:
            value: Valor a digitar
            clear_first: Se True, limpa campo antes

        Returns:
            True se digitou com sucesso
        """
        try:
            if clear_first:
                # Seleciona tudo e apaga
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.05)
                pyautogui.press("delete")
                time.sleep(0.05)

            # Digita valor
            pyautogui.typewrite(
                value,
                interval=self._humanize_delay(self._config.type_delay),
            )

            time.sleep(self._humanize_delay(self._config.click_delay))

            logger.debug(f"Digitado: {value}")
            return True

        except Exception as e:
            logger.error(f"Erro ao digitar: {e}")
            return False

    def _type_number(self, number: float, decimals: int = 2) -> bool:
        """
        Digita um número formatado.

        Args:
            number: Número a digitar
            decimals: Casas decimais

        Returns:
            True se digitou com sucesso
        """
        # Formata número (usa ponto como separador)
        formatted = f"{number:.{decimals}f}"
        return self._type_value(formatted)

    def _press_key(self, key: str) -> bool:
        """Pressiona uma tecla."""
        try:
            pyautogui.press(key)
            time.sleep(self._humanize_delay(self._config.click_delay))
            return True
        except Exception as e:
            logger.error(f"Erro ao pressionar {key}: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # EXECUÇÃO DE APOSTAS
    # ═══════════════════════════════════════════════════════════════════════════

    def place_bet(
        self,
        amount: float,
        target: float,
        slot: BetSlot = BetSlot.SLOT_1,
        wait_for_window: bool = True,
    ) -> BetResult:
        """
        Executa uma aposta.

        Args:
            amount: Valor da aposta
            target: Multiplicador alvo
            slot: Slot de aposta (1 ou 2)
            wait_for_window: Se True, aguarda janela de apostas

        Returns:
            BetResult com resultado da execução
        """
        start_time = time.time()

        with self._lock:
            # Validações
            if self._profile is None:
                return BetResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    slot=slot,
                    amount=amount,
                    target=target,
                    execution_time=0,
                    error="Perfil não carregado",
                )

            if amount < self._config.min_bet_amount:
                return BetResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    slot=slot,
                    amount=amount,
                    target=target,
                    execution_time=0,
                    error=f"Valor abaixo do mínimo ({self._config.min_bet_amount})",
                )

            if amount > self._config.max_bet_amount:
                return BetResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    slot=slot,
                    amount=amount,
                    target=target,
                    execution_time=0,
                    error=f"Valor acima do máximo ({self._config.max_bet_amount})",
                )

            # Obtém pontos de clique para o slot
            if slot == BetSlot.SLOT_1:
                bet_value_point = self._profile.bet_value_1
                target_point = self._profile.target_value_1
                bet_button = self._profile.bet_button_1
            else:
                bet_value_point = self._profile.bet_value_2
                target_point = self._profile.target_value_2
                bet_button = self._profile.bet_button_2

            # Verifica se pontos estão configurados
            if not all([bet_value_point, target_point, bet_button]):
                return BetResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    slot=slot,
                    amount=amount,
                    target=target,
                    execution_time=0,
                    error=f"Slot {slot.value} não configurado",
                )

            self._is_betting = True

            try:
                # Emite evento de início
                if self._emit_events:
                    emit(
                        BotEvent.BET_PLACING,
                        {
                            "slot": slot.value,
                            "amount": amount,
                            "target": target,
                        },
                    )

                # 1. Clica no campo de valor
                logger.info(
                    f"Iniciando aposta: R$ {amount:.2f} @ {target}x (Slot {slot.value})"
                )

                if not self._double_click(bet_value_point):
                    raise Exception("Falha ao clicar no campo de valor")

                time.sleep(self._humanize_delay(self._config.action_delay))

                # 2. Digita valor da aposta
                if not self._type_number(amount):
                    raise Exception("Falha ao digitar valor")

                time.sleep(self._humanize_delay(self._config.action_delay))

                # 3. Clica no campo de alvo
                if not self._double_click(target_point):
                    raise Exception("Falha ao clicar no campo de alvo")

                time.sleep(self._humanize_delay(self._config.action_delay))

                # 4. Digita alvo
                if not self._type_number(target):
                    raise Exception("Falha ao digitar alvo")

                time.sleep(self._humanize_delay(self._config.action_delay))

                # 5. Clica no botão de aposta
                if not self._click(bet_button):
                    raise Exception("Falha ao clicar no botão de aposta")

                execution_time = time.time() - start_time

                # Registra aposta ativa
                self._active_bets[slot] = {
                    "amount": amount,
                    "target": target,
                    "timestamp": datetime.now().isoformat(),
                }

                # Atualiza estatísticas
                self._stats["total_bets"] += 1
                self._stats["successful_bets"] += 1
                self._stats["total_amount_bet"] += amount

                result = BetResult(
                    success=True,
                    status=ExecutionStatus.SUCCESS,
                    slot=slot,
                    amount=amount,
                    target=target,
                    execution_time=execution_time,
                )

                self._last_bet = result

                # Emite evento de sucesso
                if self._emit_events:
                    emit(
                        BotEvent.BET_PLACED,
                        {
                            "slot": slot.value,
                            "amount": amount,
                            "target": target,
                            "execution_time": execution_time,
                        },
                    )

                logger.info(f"Aposta realizada com sucesso em {execution_time:.2f}s")
                return result

            except Exception as e:
                execution_time = time.time() - start_time

                self._stats["total_bets"] += 1
                self._stats["failed_bets"] += 1

                result = BetResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    slot=slot,
                    amount=amount,
                    target=target,
                    execution_time=execution_time,
                    error=str(e),
                )

                self._last_bet = result

                # Emite evento de falha
                if self._emit_events:
                    emit(
                        BotEvent.BET_FAILED,
                        {
                            "slot": slot.value,
                            "amount": amount,
                            "target": target,
                            "error": str(e),
                        },
                    )

                logger.error(f"Falha na aposta: {e}")
                return result

            finally:
                self._is_betting = False

    def cancel_bet(self, slot: BetSlot = BetSlot.SLOT_1) -> bool:
        """
        Cancela aposta ativa (se possível).

        Args:
            slot: Slot da aposta a cancelar

        Returns:
            True se cancelou com sucesso
        """
        # TODO: Implementar cancelamento de aposta
        # Depende de ter o botão de cancelar calibrado
        logger.warning("Cancelamento de aposta não implementado")
        return False

    def cashout(self, slot: BetSlot = BetSlot.SLOT_1) -> bool:
        """
        Executa cashout de aposta ativa.

        Args:
            slot: Slot da aposta

        Returns:
            True se executou cashout
        """
        # TODO: Implementar cashout
        logger.warning("Cashout não implementado")
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # EXECUÇÃO RÁPIDA
    # ═══════════════════════════════════════════════════════════════════════════

    def quick_bet(
        self,
        amount: float,
        target: float,
        slot: BetSlot = BetSlot.SLOT_1,
    ) -> bool:
        """
        Aposta rápida (sem verificações extras).

        Otimizado para velocidade máxima.

        Returns:
            True se iniciou a aposta
        """
        result = self.place_bet(
            amount=amount,
            target=target,
            slot=slot,
            wait_for_window=False,
        )
        return result.success

    def bet_both_slots(
        self,
        amount: float,
        target: float,
    ) -> Tuple[BetResult, BetResult]:
        """
        Aposta nos dois slots simultaneamente.

        Returns:
            Tupla com resultados dos dois slots
        """
        result1 = self.place_bet(amount, target, BetSlot.SLOT_1)
        result2 = self.place_bet(amount, target, BetSlot.SLOT_2)
        return result1, result2

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def is_betting(self) -> bool:
        """Verifica se está executando aposta."""
        return self._is_betting

    @property
    def has_active_bet(self) -> bool:
        """Verifica se há apostas ativas."""
        return len(self._active_bets) > 0

    def get_active_bets(self) -> Dict[BetSlot, Dict]:
        """Retorna apostas ativas."""
        return self._active_bets.copy()

    def clear_active_bets(self) -> None:
        """Limpa registro de apostas ativas."""
        with self._lock:
            self._active_bets.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas."""
        stats = self._stats.copy()
        if stats["total_bets"] > 0:
            stats["success_rate"] = stats["successful_bets"] / stats["total_bets"]
        else:
            stats["success_rate"] = 0.0
        return stats

    def reset_stats(self) -> None:
        """Reseta estatísticas."""
        with self._lock:
            self._stats = {
                "total_bets": 0,
                "successful_bets": 0,
                "failed_bets": 0,
                "total_amount_bet": 0.0,
            }

    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo."""
        return {
            "is_betting": self._is_betting,
            "has_profile": self._profile is not None,
            "active_bets": len(self._active_bets),
            "last_bet": self._last_bet.timestamp if self._last_bet else None,
            "stats": self.get_stats(),
        }

    def test_click(self, slot: BetSlot = BetSlot.SLOT_1) -> bool:
        """
        Testa clique no slot (para calibração).

        Move mouse para o ponto sem clicar.
        """
        if self._profile is None:
            return False

        if slot == BetSlot.SLOT_1:
            point = self._profile.bet_button_1
        else:
            point = self._profile.bet_button_2

        if point:
            pyautogui.moveTo(point.x, point.y, duration=0.5)
            return True

        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_executor: Optional[BetExecutor] = None
_executor_lock = threading.Lock()


def get_executor(**kwargs) -> BetExecutor:
    """
    Retorna a instância singleton do BetExecutor.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _executor

    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = BetExecutor(**kwargs)

    return _executor


def reset_executor() -> None:
    """Reseta o executor (útil para testes)."""
    global _executor
    with _executor_lock:
        _executor = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO BET EXECUTOR - CrashBot v3.0")
    print("=" * 60)

    if not HAS_PYAUTOGUI:
        print("❌ PyAutoGUI não instalado!")
        exit(1)

    print(f"\n✅ PyAutoGUI disponível")

    # Cria executor
    executor = BetExecutor(emit_events=False)
    print(f"\n✅ BetExecutor criado")

    # Cria perfil de teste (coordenadas fictícias)
    profile = ExecutorProfile(
        bet_value_1=ClickPoint(x=100, y=200, name="bet_value_1"),
        target_value_1=ClickPoint(x=100, y=250, name="target_1"),
        bet_button_1=ClickPoint(x=100, y=300, name="bet_button_1"),
        bet_value_2=ClickPoint(x=300, y=200, name="bet_value_2"),
        target_value_2=ClickPoint(x=300, y=250, name="target_2"),
        bet_button_2=ClickPoint(x=300, y=300, name="bet_button_2"),
    )

    executor.load_profile(profile)
    print(f"   Perfil carregado")

    # Status
    print(f"\n--- Status ---")
    status = executor.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")

    # Teste de movimento (sem clicar de verdade)
    print(f"\n--- Teste de Movimento ---")
    print("   Movendo mouse para posição do botão...")
    print("   (Mova o mouse para o canto para cancelar)")

    try:
        # Apenas move, não clica
        executor.test_click(BetSlot.SLOT_1)
        print(f"   ✅ Mouse movido para Slot 1")

        time.sleep(1)

        executor.test_click(BetSlot.SLOT_2)
        print(f"   ✅ Mouse movido para Slot 2")

    except pyautogui.FailSafeException:
        print(f"   ⚠️ Failsafe ativado (mouse no canto)")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
    print(
        "\n⚠️ Para testar apostas reais, carregue config.json com coordenadas calibradas"
    )
