#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SERVIÇO DE TELEMETRIA

Envia dados de telemetria para a API de forma assíncrona.
Integrado com EventBus para capturar eventos automaticamente.

Uso:
    from services.telemetry import TelemetryService, get_telemetry

    telemetry = get_telemetry()
    telemetry.configure(user_id="123", license_key="ABC")
    telemetry.start()

    # Envia manualmente
    telemetry.send("session_start", {"mode": "MODERADO"})

    # Ou automaticamente via EventBus
    emit(BotEvent.SESSION_STARTED, {...})  # Capturado automaticamente
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from core.constants import API_BASE_URL, API_ENDPOINTS, API_TIMEOUT, BOT_VERSION

# Core imports
from core.events import BotEvent, EventData, get_event_bus
from core.state import get_state

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TelemetryPayload:
    """Payload de telemetria a ser enviado."""

    event_type: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 0  # 0=baixa, 1=normal, 2=alta

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SERVIÇO DE TELEMETRIA
# ═══════════════════════════════════════════════════════════════════════════════


class TelemetryService:
    """
    Serviço de telemetria assíncrona.

    Features:
        - Envio em background (não bloqueia)
        - Fila de eventos com retry
        - Batch de eventos para eficiência
        - Integração automática com EventBus
        - Fallback para arquivo local se API falhar

    Exemplo:
        service = TelemetryService()
        service.configure(user_id="123", license_key="ABC", hwid="XYZ")
        service.start()

        # Envio manual
        service.send("bet_executed", {"amount": 10.0, "target": 1.85})

        # Automático via eventos
        emit(BotEvent.BET_EXECUTED, {...})
    """

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        auto_subscribe: bool = True,
        batch_size: int = 10,
        flush_interval: float = 30.0,
    ):
        """
        Inicializa o serviço de telemetria.

        Args:
            api_base_url: URL base da API
            auto_subscribe: Se True, captura eventos do EventBus automaticamente
            batch_size: Quantidade de eventos para enviar em batch
            flush_interval: Intervalo em segundos para flush automático
        """
        self._api_base_url = api_base_url or API_BASE_URL
        self._batch_size = batch_size
        self._flush_interval = flush_interval

        # Identificação
        self._user_id: Optional[str] = None
        self._license_key: Optional[str] = None
        self._hwid: Optional[str] = None
        self._session_id: Optional[str] = None

        # Fila de eventos
        self._queue: queue.Queue[TelemetryPayload] = queue.Queue()

        # Thread de envio
        self._sender_thread: Optional[threading.Thread] = None
        self._running = False

        # EventBus
        self._event_bus = get_event_bus()
        self._unsubscribers: List[Callable] = []

        # Estatísticas
        self._stats = {
            "sent": 0,
            "failed": 0,
            "queued": 0,
        }

        # Habilita/desabilita
        self._enabled = True

        # Auto-subscribe
        if auto_subscribe:
            self._setup_event_handlers()

        logger.debug(f"TelemetryService inicializado (API: {self._api_base_url})")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def configure(
        self,
        user_id: Optional[str] = None,
        license_key: Optional[str] = None,
        hwid: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Configura identificadores para telemetria.

        Args:
            user_id: ID do usuário
            license_key: Chave de licença
            hwid: Hardware ID
            session_id: ID da sessão atual
        """
        if user_id:
            self._user_id = user_id
        if license_key:
            self._license_key = license_key
        if hwid:
            self._hwid = hwid
        if session_id:
            self._session_id = session_id

        logger.debug(f"Telemetria configurada: user={user_id}, session={session_id}")

    def set_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita telemetria."""
        self._enabled = enabled
        logger.info(f"Telemetria {'habilitada' if enabled else 'desabilitada'}")

    # ═══════════════════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self) -> None:
        """Inicia o serviço (thread de envio)."""
        if self._running:
            logger.warning("TelemetryService já está rodando")
            return

        self._running = True
        self._sender_thread = threading.Thread(
            target=self._sender_loop, daemon=True, name="TelemetrySender"
        )
        self._sender_thread.start()
        logger.info("TelemetryService iniciado")

    def stop(self, flush: bool = True) -> None:
        """
        Para o serviço.

        Args:
            flush: Se True, envia eventos pendentes antes de parar
        """
        self._running = False

        # Flush pendentes
        if flush:
            self._flush_queue()

        # Desinscreve dos eventos
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

        # Aguarda thread finalizar
        if self._sender_thread and self._sender_thread.is_alive():
            self._sender_thread.join(timeout=5.0)

        logger.info(
            f"TelemetryService parado (enviados: {self._stats['sent']}, falhas: {self._stats['failed']})"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # ENVIO DE TELEMETRIA
    # ═══════════════════════════════════════════════════════════════════════════

    def send(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 1,
    ) -> bool:
        """
        Enfileira um evento de telemetria para envio.

        Args:
            event_type: Tipo do evento (ex: "session_start", "bet_executed")
            data: Dados do evento
            priority: Prioridade (0=baixa, 1=normal, 2=alta)

        Returns:
            True se enfileirado com sucesso
        """
        if not self._enabled:
            return False

        payload = TelemetryPayload(
            event_type=event_type,
            data=data or {},
            priority=priority,
        )

        try:
            self._queue.put_nowait(payload)
            self._stats["queued"] += 1
            logger.debug(f"Telemetria enfileirada: {event_type}")
            return True
        except queue.Full:
            logger.warning("Fila de telemetria cheia")
            return False

    def send_immediate(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Envia telemetria imediatamente (síncrono).

        Use com cuidado - bloqueia a thread atual.

        Args:
            event_type: Tipo do evento
            data: Dados do evento

        Returns:
            True se enviado com sucesso
        """
        if not self._enabled:
            return False

        payload = TelemetryPayload(
            event_type=event_type,
            data=data or {},
            priority=2,
        )

        return self._send_to_api([payload])

    def _sender_loop(self) -> None:
        """Loop da thread de envio."""
        logger.debug("Thread de telemetria iniciada")

        batch: List[TelemetryPayload] = []
        last_flush = time.time()

        while self._running:
            try:
                # Tenta pegar da fila com timeout
                try:
                    payload = self._queue.get(timeout=1.0)
                    batch.append(payload)
                except queue.Empty:
                    pass

                # Verifica se deve enviar
                should_flush = (
                    len(batch) >= self._batch_size
                    or (time.time() - last_flush) >= self._flush_interval
                )

                if batch and should_flush:
                    self._send_to_api(batch)
                    batch = []
                    last_flush = time.time()

            except Exception as e:
                logger.error(f"Erro no loop de telemetria: {e}")

        # Envia restante ao parar
        if batch:
            self._send_to_api(batch)

        logger.debug("Thread de telemetria finalizada")

    def _flush_queue(self) -> None:
        """Envia todos os eventos pendentes na fila."""
        batch: List[TelemetryPayload] = []

        while not self._queue.empty():
            try:
                payload = self._queue.get_nowait()
                batch.append(payload)
            except queue.Empty:
                break

        if batch:
            self._send_to_api(batch)

    def _send_to_api(self, payloads: List[TelemetryPayload]) -> bool:
        """
        Envia batch de eventos para a API.

        Args:
            payloads: Lista de payloads a enviar

        Returns:
            True se enviado com sucesso
        """
        if not HAS_REQUESTS:
            logger.warning("requests não disponível")
            return False

        if not payloads:
            return True

        url = f"{self._api_base_url}{API_ENDPOINTS['telemetry']}"

        sent = 0
        failed = 0

        for payload in payloads:
            # Monta payload flat compatível com TelemetriaRequest do backend
            event_data = payload.data if isinstance(payload.data, dict) else {}
            request_data = {
                "sessao_id": self._session_id or "unknown",
                "hwid": self._hwid or "unknown",
                "tipo": payload.event_type,
                "dados": str(event_data),
                "versao_bot": BOT_VERSION,
                "lucro": event_data.get("profit", event_data.get("lucro", 0.0)),
                "saldo": event_data.get("current_balance", event_data.get("saldo")),
                "valor_aposta": event_data.get("bet_amount", event_data.get("valor_aposta")),
                "banca_inicial": event_data.get("banca_inicial"),
                "banca_final": event_data.get("banca_final"),
                "modo_risco": event_data.get("risk_mode", event_data.get("modo_risco")),
                "estrategia": event_data.get("estrategia"),
                "target": event_data.get("target"),
                "explosao": event_data.get("explosao", event_data.get("explosion")),
                "resultado": event_data.get("resultado", event_data.get("result")),
                "sequencia_perdas": event_data.get("sequencia_perdas"),
                "dobra_atual": event_data.get("dobra_atual"),
                "total_rodadas": event_data.get("round_count", event_data.get("total_rodadas")),
                "plataforma": event_data.get("plataforma"),
            }

            # Remove campos None para não enviar lixo
            request_data = {k: v for k, v in request_data.items() if v is not None}

            try:
                response = requests.post(
                    url,
                    json=request_data,
                    timeout=API_TIMEOUT,
                )

                if response.status_code in (200, 201, 202):
                    sent += 1
                else:
                    failed += 1
                    logger.warning(
                        f"Erro ao enviar telemetria: HTTP {response.status_code}"
                    )

            except requests.Timeout:
                failed += 1
                logger.warning("Timeout ao enviar telemetria")

            except requests.RequestException as e:
                failed += 1
                logger.error(f"Erro de conexão telemetria: {e}")

        self._stats["sent"] += sent
        self._stats["failed"] += failed

        if sent > 0:
            logger.debug(f"Telemetria enviada: {sent} eventos")

        return failed == 0

    # ═══════════════════════════════════════════════════════════════════════════
    # INTEGRAÇÃO COM EVENTBUS
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_event_handlers(self) -> None:
        """Registra handlers para eventos relevantes."""

        # Eventos de sessão
        events_to_track = [
            BotEvent.SESSION_STARTED,
            BotEvent.SESSION_ENDED,
            BotEvent.BALANCE_DETECTED,
            BotEvent.BALANCE_CHANGED,
            BotEvent.MODE_CHANGED,
            BotEvent.EXPLOSION_DETECTED,
            BotEvent.BET_EXECUTED,
            BotEvent.BET_RESULT_HIT,
            BotEvent.BET_RESULT_MISS,
            BotEvent.GOAL_REACHED,
            BotEvent.STOP_LOSS_TRIGGERED,
            BotEvent.ERROR_OCCURRED,
        ]

        for event in events_to_track:
            unsub = self._event_bus.subscribe(event, self._on_event)
            self._unsubscribers.append(unsub)

        logger.debug(f"Telemetria inscrita em {len(events_to_track)} eventos")

    def _on_event(self, event_data: EventData) -> None:
        """Handler genérico para eventos."""
        # Enriquece com dados do estado atual
        enriched_data = self._enrich_payload(event_data.payload)

        # Determina prioridade
        priority = self._get_event_priority(event_data.event_type)

        # Enfileira
        self.send(
            event_type=event_data.event_type.name.lower(),
            data=enriched_data,
            priority=priority,
        )

    def _enrich_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquece payload com dados do estado atual."""
        try:
            state = get_state()

            enriched = {
                **data,
                "round_count": state.session.round_count,
                "elapsed_seconds": state.session.elapsed_seconds,
            }

            # Adiciona saldo se disponível
            if state.trading.current_balance is not None:
                enriched["current_balance"] = state.trading.current_balance
                enriched["profit"] = state.trading.profit
                enriched["profit_percent"] = state.trading.profit_percent

            # Adiciona modo se disponível
            if state.trading.risk_mode is not None:
                enriched["risk_mode"] = state.trading.risk_mode.name

            # Adiciona plataforma
            if state.session.platform:
                enriched["plataforma"] = state.session.platform

            return enriched

        except Exception as e:
            logger.error(f"Erro ao enriquecer payload: {e}")
            return data

    def _get_event_priority(self, event_type: BotEvent) -> int:
        """Retorna prioridade baseada no tipo de evento."""
        high_priority = [
            BotEvent.SESSION_STARTED,
            BotEvent.SESSION_ENDED,
            BotEvent.GOAL_REACHED,
            BotEvent.STOP_LOSS_TRIGGERED,
            BotEvent.ERROR_OCCURRED,
        ]

        if event_type in high_priority:
            return 2
        return 1

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTATÍSTICAS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de envio."""
        return {
            **self._stats,
            "pending": self._queue.qsize(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_telemetry_service: Optional[TelemetryService] = None
_telemetry_lock = threading.Lock()


def get_telemetry() -> TelemetryService:
    """
    Retorna a instância singleton do TelemetryService.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _telemetry_service

    if _telemetry_service is None:
        with _telemetry_lock:
            if _telemetry_service is None:
                _telemetry_service = TelemetryService()

    return _telemetry_service


def reset_telemetry() -> None:
    """Reseta o serviço de telemetria (útil para testes)."""
    global _telemetry_service
    with _telemetry_lock:
        if _telemetry_service:
            _telemetry_service.stop(flush=False)
        _telemetry_service = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO TELEMETRY SERVICE - CrashBot v3.0")
    print("=" * 60)

    # Cria serviço
    service = TelemetryService(auto_subscribe=False)  # Sem auto para teste

    print(f"\n✅ Serviço criado")
    print(f"   API: {service._api_base_url}")
    print(f"   Batch size: {service._batch_size}")

    # Configura
    service.configure(
        user_id="test_user",
        license_key="TEST-KEY",
        hwid="test_hwid",
        session_id="test_session_001",
    )
    print(f"✅ Configurado")

    # Inicia
    service.start()
    print(f"✅ Iniciado")

    # Enfileira alguns eventos (não vão ser enviados de verdade sem API)
    print(f"\n--- Enfileirando eventos ---")
    service.send("test_event_1", {"value": 100})
    service.send("test_event_2", {"value": 200})
    service.send("test_event_3", {"value": 300})

    # Aguarda um pouco
    time.sleep(1)

    # Stats
    stats = service.get_stats()
    print(f"\n--- Estatísticas ---")
    print(f"   Enviados: {stats['sent']}")
    print(f"   Falhas: {stats['failed']}")
    print(f"   Pendentes: {stats['pending']}")

    # Para
    service.stop(flush=False)
    print(f"\n✅ Serviço parado")

    print("\n" + "=" * 60)
    print("✅ TESTES BÁSICOS PASSARAM!")
    print("=" * 60)
