#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - WEBSOCKET SNIFFER

Intercepta comunicação WebSocket do jogo Crash para obter
multiplicadores em tempo real (como TipMiner).

VANTAGENS sobre OCR:
    - ✅ 100% preciso (dados brutos do servidor)
    - ✅ Tempo real (sem delay de captura/processamento)
    - ✅ Baixo uso de CPU (sem processamento de imagem)
    - ✅ Não depende de posição da janela
    - ✅ Funciona mesmo com jogo minimizado

MÉTODOS DE INTERCEPTAÇÃO:
    1. Proxy Local (recomendado)
    2. Browser DevTools Protocol (CDP)
    3. Packet Sniffing (mitmproxy)
    4. Direct WebSocket Connection (se URL conhecida)

Uso:
    from engine.vision.websocket_sniffer import WebSocketSniffer

    sniffer = WebSocketSniffer()
    sniffer.start()

    # Em callback
    def on_explosion(multiplier):
        print(f"Crash em {multiplier}x!")

    sniffer.on_explosion = on_explosion
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class SnifferMethod(Enum):
    """Métodos de interceptação de WebSocket."""

    PROXY = "proxy"  # Proxy local (mitmproxy)
    CDP = "cdp"  # Chrome DevTools Protocol
    DIRECT = "direct"  # Conexão direta (se URL conhecida)
    PACKET = "packet"  # Packet sniffing (scapy)


class GameEvent(Enum):
    """Eventos do jogo detectados via WebSocket."""

    ROUND_START = "round_start"
    MULTIPLIER_UPDATE = "multiplier_update"
    EXPLOSION = "explosion"
    BET_PLACED = "bet_placed"
    BET_CASHED_OUT = "bet_cashed_out"
    GAME_STATE = "game_state"


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ExplosionEvent:
    """Dados de uma explosão detectada."""

    multiplier: float
    timestamp: datetime
    round_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "multiplier": self.multiplier,
            "timestamp": self.timestamp.isoformat(),
            "round_id": self.round_id,
        }


@dataclass
class MultiplierUpdate:
    """Atualização de multiplicador em tempo real."""

    current_multiplier: float
    timestamp: datetime
    elapsed_time: Optional[float] = None  # Segundos desde início


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET SNIFFER
# ═══════════════════════════════════════════════════════════════════════════════


class WebSocketSniffer:
    """
    Intercepta comunicação WebSocket do jogo para obter dados em tempo real.

    Features:
        - Detecção automática de explosões
        - Updates de multiplicador em tempo real
        - Callbacks customizáveis
        - Thread-safe
        - Múltiplos métodos de interceptação

    Exemplo:
        sniffer = WebSocketSniffer()

        @sniffer.on_explosion
        def handle_explosion(event: ExplosionEvent):
            print(f"Crash em {event.multiplier}x!")

        sniffer.start()
    """

    def __init__(
        self,
        method: SnifferMethod = SnifferMethod.DIRECT,
        websocket_url: Optional[str] = None,
    ):
        """
        Inicializa o sniffer.

        Args:
            method: Método de interceptação
            websocket_url: URL do WebSocket (se método DIRECT)
        """
        self.method = method
        self.websocket_url = websocket_url

        # Estado
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Histórico
        self._explosion_history: List[ExplosionEvent] = []
        self._max_history = 1000

        # Callbacks
        self._on_explosion_callback: Optional[Callable[[ExplosionEvent], None]] = None
        self._on_multiplier_callback: Optional[
            Callable[[MultiplierUpdate], None]
        ] = None

        # Stats
        self.total_explosions = 0
        self.last_explosion: Optional[ExplosionEvent] = None

        logger.info(f"WebSocketSniffer criado: method={method.value}")

    # ═══════════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def on_explosion(self) -> Optional[Callable[[ExplosionEvent], None]]:
        """Callback chamado quando detecta explosão."""
        return self._on_explosion_callback

    @on_explosion.setter
    def on_explosion(self, callback: Callable[[ExplosionEvent], None]) -> None:
        """Define callback de explosão."""
        self._on_explosion_callback = callback

    @property
    def on_multiplier(self) -> Optional[Callable[[MultiplierUpdate], None]]:
        """Callback chamado a cada update de multiplicador."""
        return self._on_multiplier_callback

    @on_multiplier.setter
    def on_multiplier(self, callback: Callable[[MultiplierUpdate], None]) -> None:
        """Define callback de multiplicador."""
        self._on_multiplier_callback = callback

    # ═══════════════════════════════════════════════════════════════════════
    # CONTROLE
    # ═══════════════════════════════════════════════════════════════════════

    def start(self) -> bool:
        """
        Inicia interceptação.

        Returns:
            True se iniciou com sucesso
        """
        with self._lock:
            if self._running:
                logger.warning("Sniffer já está rodando")
                return False

            self._running = True

            # Escolhe método
            if self.method == SnifferMethod.DIRECT:
                self._thread = threading.Thread(
                    target=self._run_direct_connection, daemon=True
                )
            elif self.method == SnifferMethod.PROXY:
                self._thread = threading.Thread(target=self._run_proxy, daemon=True)
            elif self.method == SnifferMethod.CDP:
                self._thread = threading.Thread(target=self._run_cdp, daemon=True)
            else:
                logger.error(f"Método não implementado: {self.method}")
                self._running = False
                return False

            self._thread.start()
            logger.info("WebSocketSniffer iniciado")
            return True

    def stop(self) -> None:
        """Para interceptação."""
        with self._lock:
            if not self._running:
                return

            self._running = False

        if self._thread:
            self._thread.join(timeout=2.0)

        logger.info("WebSocketSniffer parado")

    def is_running(self) -> bool:
        """Verifica se está rodando."""
        return self._running

    # ═══════════════════════════════════════════════════════════════════════
    # MÉTODOS DE INTERCEPTAÇÃO
    # ═══════════════════════════════════════════════════════════════════════

    def _run_direct_connection(self) -> None:
        """
        Conecta diretamente ao WebSocket do jogo (se URL conhecida).

        Requer: websocket_url definida
        """
        if not self.websocket_url:
            logger.error("websocket_url não definida para método DIRECT")
            self._running = False
            return

        try:
            import websocket

            logger.info(f"Conectando a {self.websocket_url}")

            ws = websocket.WebSocketApp(
                self.websocket_url,
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
                on_open=self._on_ws_open,
            )

            # Run forever (bloqueante)
            ws.run_forever()

        except Exception as e:
            logger.error(f"Erro na conexão WebSocket: {e}")
            self._running = False

    def _run_proxy(self) -> None:
        """
        Usa proxy local (mitmproxy) para interceptar.

        Requer: mitmproxy instalado
        """
        logger.warning("Método PROXY não implementado ainda")
        # TODO: Implementar com mitmproxy
        self._running = False

    def _run_cdp(self) -> None:
        """
        Usa Chrome DevTools Protocol para interceptar.

        Requer: chrome com --remote-debugging-port
        """
        logger.warning("Método CDP não implementado ainda")
        # TODO: Implementar com pychrome ou playwright
        self._running = False

    # ═══════════════════════════════════════════════════════════════════════
    # WEBSOCKET HANDLERS
    # ═══════════════════════════════════════════════════════════════════════

    def _on_ws_open(self, ws) -> None:
        """Chamado quando WebSocket abre."""
        logger.info("WebSocket conectado")

    def _on_ws_message(self, ws, message: str) -> None:
        """
        Chamado ao receber mensagem WebSocket.

        Args:
            ws: WebSocket instance
            message: Mensagem recebida
        """
        try:
            # Parse JSON
            data = json.loads(message)

            # Detecta tipo de evento
            event_type = self._detect_event_type(data)

            if event_type == GameEvent.EXPLOSION:
                self._handle_explosion(data)
            elif event_type == GameEvent.MULTIPLIER_UPDATE:
                self._handle_multiplier_update(data)

        except json.JSONDecodeError:
            logger.debug(f"Mensagem não-JSON: {message[:100]}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    def _on_ws_error(self, ws, error) -> None:
        """Chamado em erro."""
        logger.error(f"WebSocket error: {error}")

    def _on_ws_close(self, ws, close_status_code, close_msg) -> None:
        """Chamado ao fechar."""
        logger.info(f"WebSocket fechado: {close_status_code} - {close_msg}")
        self._running = False

    # ═══════════════════════════════════════════════════════════════════════
    # PROCESSAMENTO DE EVENTOS
    # ═══════════════════════════════════════════════════════════════════════

    def _detect_event_type(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """
        Detecta tipo de evento baseado na estrutura dos dados.

        Args:
            data: Dados recebidos

        Returns:
            Tipo do evento ou None
        """
        # Padrões comuns de jogos Crash
        if "crash" in data or "bust" in data or "explosion" in data:
            return GameEvent.EXPLOSION

        if "multiplier" in data or "current" in data:
            return GameEvent.MULTIPLIER_UPDATE

        if "round" in data and "start" in str(data).lower():
            return GameEvent.ROUND_START

        return None

    def _handle_explosion(self, data: Dict[str, Any]) -> None:
        """
        Processa evento de explosão.

        Args:
            data: Dados do evento
        """
        # Tenta extrair multiplicador
        multiplier = self._extract_multiplier(data)

        if multiplier is None:
            logger.warning(f"Não conseguiu extrair multiplicador de: {data}")
            return

        # Cria evento
        event = ExplosionEvent(
            multiplier=multiplier,
            timestamp=datetime.now(),
            round_id=data.get("round_id") or data.get("id"),
            raw_data=data,
        )

        # Atualiza histórico
        with self._lock:
            self._explosion_history.append(event)
            if len(self._explosion_history) > self._max_history:
                self._explosion_history.pop(0)

            self.total_explosions += 1
            self.last_explosion = event

        logger.info(f"💥 Explosão detectada: {multiplier}x")

        # Callback
        if self._on_explosion_callback:
            try:
                self._on_explosion_callback(event)
            except Exception as e:
                logger.error(f"Erro no callback de explosão: {e}")

    def _handle_multiplier_update(self, data: Dict[str, Any]) -> None:
        """
        Processa update de multiplicador em tempo real.

        Args:
            data: Dados do update
        """
        multiplier = self._extract_multiplier(data)

        if multiplier is None:
            return

        update = MultiplierUpdate(
            current_multiplier=multiplier,
            timestamp=datetime.now(),
            elapsed_time=data.get("elapsed") or data.get("time"),
        )

        # Callback
        if self._on_multiplier_callback:
            try:
                self._on_multiplier_callback(update)
            except Exception as e:
                logger.error(f"Erro no callback de multiplicador: {e}")

    def _extract_multiplier(self, data: Dict[str, Any]) -> Optional[float]:
        """
        Extrai valor do multiplicador dos dados.

        Args:
            data: Dados brutos

        Returns:
            Multiplicador ou None
        """
        # Tenta vários campos possíveis
        for key in [
            "crash",
            "bust",
            "explosion",
            "multiplier",
            "mult",
            "value",
            "result",
            "current",
        ]:
            if key in data:
                try:
                    value = data[key]

                    # Se for string, tenta remover 'x' e converter
                    if isinstance(value, str):
                        value = value.replace("x", "").replace("X", "").strip()

                    return float(value)
                except (ValueError, TypeError):
                    continue

        return None

    # ═══════════════════════════════════════════════════════════════════════
    # GETTERS
    # ═══════════════════════════════════════════════════════════════════════

    def get_history(
        self, limit: Optional[int] = None
    ) -> List[ExplosionEvent]:
        """
        Retorna histórico de explosões.

        Args:
            limit: Número máximo de explosões (None = todas)

        Returns:
            Lista de explosões
        """
        with self._lock:
            if limit is None:
                return self._explosion_history.copy()
            return self._explosion_history[-limit:]

    def get_last_n_multipliers(self, n: int = 10) -> List[float]:
        """
        Retorna últimos N multiplicadores.

        Args:
            n: Quantidade

        Returns:
            Lista de multiplicadores
        """
        history = self.get_history(limit=n)
        return [event.multiplier for event in history]

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas.

        Returns:
            Dicionário com stats
        """
        history = self.get_history()
        multipliers = [e.multiplier for e in history]

        if not multipliers:
            return {"total": 0}

        import statistics

        return {
            "total_explosions": self.total_explosions,
            "history_size": len(history),
            "mean": statistics.mean(multipliers),
            "median": statistics.median(multipliers),
            "min": min(multipliers),
            "max": max(multipliers),
            "last": multipliers[-1] if multipliers else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_sniffer_instance: Optional[WebSocketSniffer] = None
_sniffer_lock = threading.Lock()


def get_sniffer(
    method: SnifferMethod = SnifferMethod.DIRECT,
    websocket_url: Optional[str] = None,
) -> WebSocketSniffer:
    """
    Retorna instância singleton do sniffer.

    Args:
        method: Método de interceptação
        websocket_url: URL do WebSocket

    Returns:
        Instância do sniffer
    """
    global _sniffer_instance

    with _sniffer_lock:
        if _sniffer_instance is None:
            _sniffer_instance = WebSocketSniffer(
                method=method, websocket_url=websocket_url
            )

    return _sniffer_instance
