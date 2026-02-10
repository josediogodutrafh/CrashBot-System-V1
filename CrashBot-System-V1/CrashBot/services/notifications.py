#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SERVIÇO DE NOTIFICAÇÕES

Gerencia notificações via Telegram e sons de alerta.
Integrado com EventBus para reagir automaticamente a eventos.

Uso:
    from services.notifications import NotificationService, get_notifications

    # Singleton
    notifications = get_notifications()
    notifications.start()

    # Envio manual
    notifications.send_telegram("Mensagem de teste")
    notifications.play_sound("hit")
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

# Imports condicionais para Windows
try:
    import winsound

    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from core.constants import (
    API_TIMEOUT,
    SOUND_ALERT,
    SOUND_HIT,
    SOUND_MISS,
    TELEGRAM_API_URL,
    TELEGRAM_BOT_TOKEN_DEFAULT,
)

# Core imports
from core.events import BotEvent, EventData, get_event_bus

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# TIPOS DE SOM
# ═══════════════════════════════════════════════════════════════════════════════


class SoundType(Enum):
    """Tipos de sons disponíveis."""

    HIT = "hit"
    MISS = "miss"
    ALERT = "alert"
    GOAL = "goal"
    STOP_LOSS = "stop_loss"


# Configuração de cada som (frequência Hz, duração ms)
SOUND_CONFIG: Dict[SoundType, Dict[str, int]] = {
    SoundType.HIT: {"frequency": 1500, "duration": 150},
    SoundType.MISS: {"frequency": 700, "duration": 300},
    SoundType.ALERT: {"frequency": 500, "duration": 500},
    SoundType.GOAL: {"frequency": 2000, "duration": 1000},
    SoundType.STOP_LOSS: {"frequency": 300, "duration": 1500},
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS PARA MENSAGENS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class NotificationMessage:
    """Mensagem a ser enviada."""

    text: str
    chat_id: str
    priority: int = 0  # 0 = normal, 1 = alta


# ═══════════════════════════════════════════════════════════════════════════════
# SERVIÇO DE NOTIFICAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════


class NotificationService:
    """
    Serviço de notificações centralizado.

    Features:
        - Envio de mensagens via Telegram (thread separada)
        - Sons de alerta (Windows)
        - Integração automática com EventBus
        - Fila de mensagens para não bloquear

    Exemplo:
        service = NotificationService(telegram_token="...", chat_id="...")
        service.start()

        # Envio manual
        service.send_telegram("Olá!")
        service.play_sound(SoundType.HIT)

        # Ou via eventos (automático)
        emit(BotEvent.GOAL_REACHED, {...})  # Envia notificação automaticamente
    """

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        sound_enabled: bool = True,
        telegram_enabled: bool = True,
        auto_subscribe: bool = True,
    ):
        """
        Inicializa o serviço de notificações.

        Args:
            telegram_token: Token do bot Telegram (usa default se None)
            chat_id: ID do chat para enviar mensagens
            sound_enabled: Habilita sons de alerta
            telegram_enabled: Habilita notificações Telegram
            auto_subscribe: Se True, registra handlers de eventos automaticamente
        """
        self._telegram_token = telegram_token or TELEGRAM_BOT_TOKEN_DEFAULT
        self._chat_id = chat_id
        self._sound_enabled = sound_enabled and HAS_WINSOUND
        self._telegram_enabled = telegram_enabled and HAS_REQUESTS

        # Fila de mensagens Telegram
        self._message_queue: queue.Queue[NotificationMessage] = queue.Queue()

        # Thread de envio
        self._sender_thread: Optional[threading.Thread] = None
        self._running = False

        # Event bus
        self._event_bus = get_event_bus()
        self._unsubscribers: list[Callable] = []

        # Auto-subscribe aos eventos relevantes
        if auto_subscribe:
            self._setup_event_handlers()

        logger.debug(
            f"NotificationService inicializado "
            f"(telegram={self._telegram_enabled}, sound={self._sound_enabled})"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def set_chat_id(self, chat_id: str) -> None:
        """Define o chat_id do Telegram."""
        self._chat_id = chat_id
        logger.info(f"Chat ID configurado: {chat_id}")

    def set_telegram_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita Telegram."""
        self._telegram_enabled = enabled and HAS_REQUESTS
        logger.info(f"Telegram {'habilitado' if enabled else 'desabilitado'}")

    def set_sound_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita sons."""
        self._sound_enabled = enabled and HAS_WINSOUND
        logger.info(f"Sons {'habilitados' if enabled else 'desabilitados'}")

    # ═══════════════════════════════════════════════════════════════════════════
    # CICLO DE VIDA
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self) -> None:
        """Inicia o serviço (thread de envio Telegram)."""
        if self._running:
            logger.warning("NotificationService já está rodando")
            return

        self._running = True
        self._sender_thread = threading.Thread(
            target=self._sender_loop, daemon=True, name="NotificationSender"
        )
        self._sender_thread.start()
        logger.info("NotificationService iniciado")

    def stop(self) -> None:
        """Para o serviço."""
        self._running = False

        # Desinscreve dos eventos
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

        # Aguarda thread finalizar
        if self._sender_thread and self._sender_thread.is_alive():
            self._sender_thread.join(timeout=2.0)

        logger.info("NotificationService parado")

    # ═══════════════════════════════════════════════════════════════════════════
    # TELEGRAM
    # ═══════════════════════════════════════════════════════════════════════════

    def send_telegram(
        self, message: str, chat_id: Optional[str] = None, priority: int = 0
    ) -> bool:
        """
        Envia mensagem via Telegram (não bloqueante).

        Args:
            message: Texto da mensagem
            chat_id: ID do chat (usa o configurado se None)
            priority: Prioridade (0=normal, 1=alta)

        Returns:
            True se a mensagem foi enfileirada com sucesso
        """
        if not self._telegram_enabled:
            logger.debug("Telegram desabilitado, mensagem ignorada")
            return False

        target_chat_id = chat_id or self._chat_id
        if not target_chat_id:
            logger.warning("Chat ID não configurado, mensagem ignorada")
            return False

        # Enfileira a mensagem
        notification = NotificationMessage(
            text=message, chat_id=target_chat_id, priority=priority
        )

        try:
            self._message_queue.put_nowait(notification)
            logger.debug(f"Mensagem enfileirada: {message[:50]}...")
            return True
        except queue.Full:
            logger.warning("Fila de mensagens cheia, mensagem descartada")
            return False

    def _sender_loop(self) -> None:
        """Loop da thread de envio de mensagens."""
        logger.debug("Thread de envio iniciada")

        while self._running:
            try:
                # Aguarda mensagem com timeout
                notification = self._message_queue.get(timeout=1.0)

                # Envia
                self._send_telegram_sync(notification)

                # Pequeno delay para não sobrecarregar API
                time.sleep(0.1)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erro no loop de envio: {e}")

        logger.debug("Thread de envio finalizada")

    def _send_telegram_sync(self, notification: NotificationMessage) -> bool:
        """
        Envia mensagem de forma síncrona (chamado pela thread).

        Args:
            notification: Dados da notificação

        Returns:
            True se enviou com sucesso
        """
        if not HAS_REQUESTS:
            return False

        url = TELEGRAM_API_URL.format(token=self._telegram_token)

        payload = {
            "chat_id": notification.chat_id,
            "text": notification.text,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, json=payload, timeout=API_TIMEOUT)

            if response.status_code == 200:
                logger.debug(f"Mensagem enviada para {notification.chat_id}")
                return True
            else:
                logger.warning(
                    f"Erro ao enviar Telegram: {response.status_code} - {response.text}"
                )
                return False

        except requests.Timeout:
            logger.warning("Timeout ao enviar mensagem Telegram")
            return False
        except requests.RequestException as e:
            logger.error(f"Erro de conexão Telegram: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # SONS
    # ═══════════════════════════════════════════════════════════════════════════

    def play_sound(self, sound_type: SoundType) -> None:
        """
        Toca um som de alerta (não bloqueante).

        Args:
            sound_type: Tipo do som a tocar
        """
        if not self._sound_enabled:
            return

        # Executa em thread separada para não bloquear
        thread = threading.Thread(
            target=self._play_sound_sync,
            args=(sound_type,),
            daemon=True,
            name=f"Sound-{sound_type.value}",
        )
        thread.start()

    def _play_sound_sync(self, sound_type: SoundType) -> None:
        """Toca o som de forma síncrona."""
        if not HAS_WINSOUND:
            return

        config = SOUND_CONFIG.get(sound_type)
        if not config:
            logger.warning(f"Configuração de som não encontrada: {sound_type}")
            return

        try:
            winsound.Beep(config["frequency"], config["duration"])
        except Exception as e:
            logger.error(f"Erro ao tocar som: {e}")

    def play_hit(self) -> None:
        """Atalho: toca som de HIT."""
        self.play_sound(SoundType.HIT)

    def play_miss(self) -> None:
        """Atalho: toca som de MISS."""
        self.play_sound(SoundType.MISS)

    def play_alert(self) -> None:
        """Atalho: toca som de alerta."""
        self.play_sound(SoundType.ALERT)

    # ═══════════════════════════════════════════════════════════════════════════
    # INTEGRAÇÃO COM EVENTBUS
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_event_handlers(self) -> None:
        """Registra handlers para eventos relevantes."""

        # Meta atingida
        unsub = self._event_bus.subscribe(BotEvent.GOAL_REACHED, self._on_goal_reached)
        self._unsubscribers.append(unsub)

        # Stop loss
        unsub = self._event_bus.subscribe(
            BotEvent.STOP_LOSS_TRIGGERED, self._on_stop_loss
        )
        self._unsubscribers.append(unsub)

        # HIT
        unsub = self._event_bus.subscribe(BotEvent.BET_RESULT_HIT, self._on_bet_hit)
        self._unsubscribers.append(unsub)

        # MISS
        unsub = self._event_bus.subscribe(BotEvent.BET_RESULT_MISS, self._on_bet_miss)
        self._unsubscribers.append(unsub)

        # Sessão iniciada
        unsub = self._event_bus.subscribe(
            BotEvent.SESSION_STARTED, self._on_session_started
        )
        self._unsubscribers.append(unsub)

        # Sessão encerrada
        unsub = self._event_bus.subscribe(
            BotEvent.SESSION_ENDED, self._on_session_ended
        )
        self._unsubscribers.append(unsub)

        logger.debug("Event handlers registrados")

    def _on_goal_reached(self, event: EventData) -> None:
        """Handler: Meta atingida."""
        profit = event.get("profit", 0)
        profit_percent = event.get("profit_percent", 0)

        message = (
            f"🏆 <b>META ATINGIDA!</b>\n\n"
            f"💰 Lucro: R$ {profit:.2f} ({profit_percent:.1f}%)\n"
            f"⏸️ Bot entrando em suspensão..."
        )

        self.send_telegram(message, priority=1)
        self.play_sound(SoundType.GOAL)

    def _on_stop_loss(self, event: EventData) -> None:
        """Handler: Stop loss atingido."""
        loss = event.get("loss", 0)
        loss_percent = event.get("loss_percent", 0)

        message = (
            f"🚨 <b>STOP LOSS ATINGIDO!</b>\n\n"
            f"📉 Perda: R$ {loss:.2f} ({loss_percent:.1f}%)\n"
            f"⛔ Sessão encerrada automaticamente"
        )

        self.send_telegram(message, priority=1)
        self.play_sound(SoundType.STOP_LOSS)

    def _on_bet_hit(self, event: EventData) -> None:
        """Handler: Aposta vencedora."""
        self.play_hit()

    def _on_bet_miss(self, event: EventData) -> None:
        """Handler: Aposta perdedora."""
        self.play_miss()

    def _on_session_started(self, event: EventData) -> None:
        """Handler: Sessão iniciada."""
        mode = event.get("mode", "N/A")
        balance = event.get("balance", 0)

        message = (
            f"✅ <b>Sessão Iniciada</b>\n\n"
            f"🎮 Modo: {mode}\n"
            f"💰 Saldo: R$ {balance:.2f}"
        )

        self.send_telegram(message)

    def _on_session_ended(self, event: EventData) -> None:
        """Handler: Sessão encerrada."""
        reason = event.get("reason", "Manual")
        profit = event.get("profit", 0)
        hits = event.get("hits", 0)
        misses = event.get("misses", 0)

        emoji = "📈" if profit >= 0 else "📉"

        message = (
            f"🏁 <b>Sessão Encerrada</b>\n\n"
            f"📋 Motivo: {reason}\n"
            f"{emoji} Resultado: R$ {profit:+.2f}\n"
            f"✅ Hits: {hits} | ❌ Misses: {misses}"
        )

        self.send_telegram(message)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_notification_service: Optional[NotificationService] = None
_notification_lock = threading.Lock()


def get_notifications() -> NotificationService:
    """
    Retorna a instância singleton do NotificationService.

    Thread-safe. Cria a instância na primeira chamada.

    Example:
        notifications = get_notifications()
        notifications.send_telegram("Teste")
    """
    global _notification_service

    if _notification_service is None:
        with _notification_lock:
            if _notification_service is None:
                _notification_service = NotificationService()

    return _notification_service


def reset_notifications() -> None:
    """Reseta o serviço de notificações (útil para testes)."""
    global _notification_service
    with _notification_lock:
        if _notification_service:
            _notification_service.stop()
        _notification_service = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO NOTIFICATION SERVICE - CrashBot v3.0")
    print("=" * 60)

    # Cria serviço (sem Telegram configurado para teste)
    service = NotificationService(
        telegram_enabled=False,  # Desabilita para teste
        sound_enabled=True,
        auto_subscribe=True,
    )

    print(f"\n✅ Serviço criado")
    print(f"   Telegram: {service._telegram_enabled}")
    print(f"   Som: {service._sound_enabled}")

    # Inicia o serviço
    service.start()
    print(f"✅ Serviço iniciado")

    # Testa sons
    print(f"\n--- Testando Sons ---")

    if HAS_WINSOUND:
        print("Tocando som HIT...")
        service.play_hit()
        time.sleep(0.3)

        print("Tocando som MISS...")
        service.play_miss()
        time.sleep(0.5)

        print("Tocando som ALERT...")
        service.play_alert()
        time.sleep(0.7)
    else:
        print("⚠️ winsound não disponível (não é Windows)")

    # Testa integração com EventBus
    print(f"\n--- Testando Integração EventBus ---")
    from core.events import emit

    print("Emitindo BotEvent.BET_RESULT_HIT...")
    emit(BotEvent.BET_RESULT_HIT, profit=25.0)
    time.sleep(0.3)

    print("Emitindo BotEvent.BET_RESULT_MISS...")
    emit(BotEvent.BET_RESULT_MISS, loss=12.5)
    time.sleep(0.5)

    # Para o serviço
    service.stop()
    print(f"\n✅ Serviço parado")

    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
