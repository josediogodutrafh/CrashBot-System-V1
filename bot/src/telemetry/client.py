"""
TelemetryClient - Envia eventos para a API do TucunareBot.

Compativel com o schema TelemetriaRequest do backend (campos flat).
Thread-safe, com fila e batch envio em background.
"""

from __future__ import annotations

import logging
import platform as py_platform
import queue
import threading
import time
import uuid
from typing import Any, Dict, Optional

import requests

from src.config import API_URL, BOT_VERSION
from src.security.hwid import get_hwid

logger = logging.getLogger(__name__)

ENDPOINT = f"{API_URL}/api/v1/telemetria/log"
TIMEOUT = 10  # segundos


class TelemetryClient:
    """Cliente de telemetria thread-safe."""

    def __init__(self) -> None:
        self._hwid = get_hwid()
        self._sessao_id = uuid.uuid4().hex[:16]
        self._sistema = f"{py_platform.system()}_{py_platform.release()}"

        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=500)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._enabled = True

        self._stats = {"sent": 0, "failed": 0, "queued": 0}

    def start(self) -> None:
        """Inicia o thread de envio em background."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
            logger.info("Telemetria iniciada (sessao=%s)", self._sessao_id)

    def stop(self) -> None:
        """Para o thread (envia eventos pendentes antes)."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def disable(self) -> None:
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True

    def send_event(
        self,
        tipo: str,
        plataforma: Optional[str] = None,
        dados: Optional[str] = None,
        lucro: Optional[float] = None,
        saldo: Optional[float] = None,
        valor_aposta: Optional[float] = None,
        banca_inicial: Optional[float] = None,
        banca_final: Optional[float] = None,
        modo_risco: Optional[str] = None,
        estrategia: Optional[str] = None,
        target: Optional[float] = None,
        explosao: Optional[float] = None,
        resultado: Optional[str] = None,
        sequencia_perdas: Optional[int] = None,
        dobra_atual: Optional[int] = None,
        total_rodadas: Optional[int] = None,
    ) -> None:
        """Enfileira um evento para envio.

        Args:
            tipo: sessao_inicio, aposta, sessao_fim, erro, modo_alterado, alerta
            plataforma: brabet, onebra, winbra, pgwin
            ...demais campos opcionais
        """
        if not self._enabled:
            return

        payload = {
            "sessao_id": self._sessao_id,
            "hwid": self._hwid,
            "tipo": tipo,
            "versao_bot": BOT_VERSION,
            "sistema_operacional": self._sistema,
            "plataforma": plataforma,
            "dados": dados,
            "lucro": lucro if lucro is not None else 0.0,
            "saldo": saldo,
            "valor_aposta": valor_aposta,
            "banca_inicial": banca_inicial,
            "banca_final": banca_final,
            "modo_risco": modo_risco,
            "estrategia": estrategia,
            "target": target,
            "explosao": explosao,
            "resultado": resultado,
            "sequencia_perdas": sequencia_perdas,
            "dobra_atual": dobra_atual,
            "total_rodadas": total_rodadas,
        }
        # Remove campos None para nao enviar lixo
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            self._queue.put_nowait(payload)
            self._stats["queued"] += 1
        except queue.Full:
            logger.warning("Fila de telemetria cheia, descartando evento")

    def _worker(self) -> None:
        """Loop de envio em background."""
        while not self._stop.is_set():
            try:
                payload = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                resp = requests.post(ENDPOINT, json=payload, timeout=TIMEOUT)
                if resp.status_code in (200, 201, 202):
                    self._stats["sent"] += 1
                else:
                    self._stats["failed"] += 1
                    logger.debug("Telemetria HTTP %d: %s", resp.status_code, resp.text[:200])
            except requests.RequestException as e:
                self._stats["failed"] += 1
                logger.debug("Erro telemetria: %s", e)
            except Exception as e:
                self._stats["failed"] += 1
                logger.error("Erro inesperado telemetria: %s", e)

        # Esvaziar fila no shutdown
        while not self._queue.empty():
            try:
                payload = self._queue.get_nowait()
                requests.post(ENDPOINT, json=payload, timeout=2)
            except Exception:
                pass

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)


# ──────────────────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────────────────

_instance: Optional[TelemetryClient] = None
_instance_lock = threading.Lock()


def get_telemetry() -> TelemetryClient:
    """Retorna o singleton do TelemetryClient (lazy init)."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = TelemetryClient()
            _instance.start()
        return _instance
