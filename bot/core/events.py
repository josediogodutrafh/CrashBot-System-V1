#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SISTEMA DE EVENTOS (EventBus)

Este módulo implementa o padrão Observer/Pub-Sub para comunicação
desacoplada entre componentes do sistema.

Uso:
    from core.events import get_event_bus, BotEvent

    # Publicar evento
    event_bus = get_event_bus()
    event_bus.publish(BotEvent.BALANCE_CHANGED, {"old": 100, "new": 150})

    # Observar evento
    @event_bus.on(BotEvent.BALANCE_CHANGED)
    def handle_balance(data):
        print(f"Novo saldo: {data.payload['new']}")
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

# Configuração do logger
logger = logging.getLogger(__name__)


class BotEvent(Enum):
    """
    Catálogo de todos os eventos do sistema.
    Usar Enum garante type-safety e autocomplete.
    """

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE SESSÃO
    # ═══════════════════════════════════════════════════════════════
    SESSION_STARTING = auto()  # Sessão iniciando (antes de validar licença)
    SESSION_STARTED = auto()  # Sessão iniciada com sucesso
    SESSION_STOPPING = auto()  # Sessão parando
    SESSION_ENDED = auto()  # Sessão finalizada
    SESSION_ERROR = auto()  # Erro crítico na sessão

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE LICENÇA
    # ═══════════════════════════════════════════════════════════════
    LICENSE_VALIDATING = auto()  # Validando licença
    LICENSE_VALID = auto()  # Licença válida
    LICENSE_INVALID = auto()  # Licença inválida
    LICENSE_EXPIRED = auto()  # Licença expirada

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE SALDO
    # ═══════════════════════════════════════════════════════════════
    BALANCE_DETECTING = auto()  # Detectando saldo
    BALANCE_DETECTED = auto()  # Saldo inicial detectado
    BALANCE_CHANGED = auto()  # Saldo alterou
    BALANCE_ERROR = auto()  # Erro ao ler saldo

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE JOGO
    # ═══════════════════════════════════════════════════════════════
    ROUND_STARTED = auto()  # Nova rodada iniciou
    MULTIPLIER_UPDATE = auto()  # Multiplicador atualizou (em tempo real)
    EXPLOSION_DETECTED = auto()  # Explosão detectada (fim da rodada)
    BET_WINDOW_OPEN = auto()  # Janela de apostas aberta ("BET 8s")

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE ESTRATÉGIA
    # ═══════════════════════════════════════════════════════════════
    STRATEGY_ANALYZING = auto()  # Analisando estratégia
    TRIGGER_PROGRESS = auto()  # Progresso do gatilho (ex: 5/8 velas)
    TRIGGER_ACTIVATED = auto()  # Gatilho ativado (vai apostar)
    TRIGGER_SKIPPED = auto()  # Gatilho pulou (fase arrecadatória, etc)
    TRIGGER_RESET = auto()  # Gatilho resetado

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE APOSTA
    # ═══════════════════════════════════════════════════════════════
    BET_PREPARING = auto()  # Preparando aposta
    BET_PREPARED = auto()  # Aposta preparada (valores definidos)
    BET_EXECUTING = auto()  # Executando aposta (clicando)
    BET_EXECUTED = auto()  # Aposta executada com sucesso
    BET_FAILED = auto()  # Falha ao executar aposta
    BET_RESULT_HIT = auto()  # Resultado: HIT (ganhou)
    BET_RESULT_MISS = auto()  # Resultado: MISS (perdeu)

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE MARTINGALE
    # ═══════════════════════════════════════════════════════════════
    MARTINGALE_STARTED = auto()  # Ciclo martingale iniciou
    MARTINGALE_DOBRA_UP = auto()  # Subiu de dobra
    MARTINGALE_RESET = auto()  # Ciclo martingale resetou
    MARTINGALE_MAX_REACHED = auto()  # Atingiu dobra máxima

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE MODO/CONFIGURAÇÃO
    # ═══════════════════════════════════════════════════════════════
    MODE_CHANGING = auto()  # Modo de risco mudando
    MODE_CHANGED = auto()  # Modo de risco alterado
    CONFIG_UPDATED = auto()  # Configuração atualizada
    PROFILE_LOADED = auto()  # Perfil de tela carregado

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE META/STOP
    # ═══════════════════════════════════════════════════════════════
    GOAL_PROGRESS = auto()  # Progresso da meta
    GOAL_REACHED = auto()  # Meta atingida
    STOP_LOSS_WARNING = auto()  # Alerta de stop loss
    STOP_LOSS_TRIGGERED = auto()  # Stop loss atingido
    SUSPENSION_STARTED = auto()  # Suspensão iniciada
    SUSPENSION_ENDED = auto()  # Suspensão terminou

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE ML
    # ═══════════════════════════════════════════════════════════════
    ML_PREDICTING = auto()  # ML fazendo predição
    ML_PREDICTION_READY = auto()  # Predição pronta
    ML_CONFIDENCE_UPDATE = auto()  # Confiança do ML atualizou
    ML_ERROR = auto()  # Erro no ML

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE SISTEMA
    # ═══════════════════════════════════════════════════════════════
    ERROR_OCCURRED = auto()  # Erro genérico
    WARNING_RAISED = auto()  # Aviso genérico
    LOG_MESSAGE = auto()  # Mensagem de log para UI
    TELEMETRY_SENT = auto()  # Telemetria enviada
    UPDATE_AVAILABLE = auto()  # Nova versão disponível

    # ═══════════════════════════════════════════════════════════════
    # EVENTOS DE UI
    # ═══════════════════════════════════════════════════════════════
    UI_REFRESH_REQUEST = auto()  # Solicita refresh da UI
    UI_NOTIFICATION = auto()  # Notificação para exibir
    UI_SOUND_ALERT = auto()  # Tocar som de alerta


@dataclass
class EventData:
    """
    Container imutável para dados de um evento.

    Attributes:
        event_type: Tipo do evento (BotEvent)
        payload: Dados do evento (dicionário flexível)
        timestamp: Momento em que o evento foi criado
        source: Componente que gerou o evento (opcional)
    """

    event_type: BotEvent
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None

    def __post_init__(self):
        """Garante que payload é sempre um dict."""
        if self.payload is None:
            self.payload = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Atalho para acessar dados do payload."""
        return self.payload.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Permite acesso via event_data['key']."""
        return self.payload[key]


# Type alias para callbacks
EventCallback = Callable[[EventData], None]


class EventBus:
    """
    Barramento de eventos thread-safe.

    Implementa o padrão Observer permitindo comunicação
    desacoplada entre componentes do sistema.

    Features:
        - Thread-safe (usa locks)
        - Suporte a wildcards (observar todos os eventos)
        - Execução síncrona ou assíncrona
        - Decorador @on() para registrar handlers
        - Histórico de eventos recentes (para debug)

    Exemplo:
        bus = EventBus()

        # Método 1: subscribe direto
        bus.subscribe(BotEvent.BALANCE_CHANGED, my_handler)

        # Método 2: decorador
        @bus.on(BotEvent.BALANCE_CHANGED)
        def handle_balance(data: EventData):
            print(data.payload)

        # Publicar
        bus.publish(BotEvent.BALANCE_CHANGED, {"new": 150})
    """

    def __init__(self, keep_history: int = 100):
        """
        Inicializa o EventBus.

        Args:
            keep_history: Quantidade de eventos recentes a manter
                          (0 = desabilitado)
        """
        self._subscribers: Dict[BotEvent, List[EventCallback]] = {}
        self._global_subscribers: List[EventCallback] = []
        self._lock = threading.RLock()
        self._history: List[EventData] = []
        self._history_limit = keep_history
        self._paused = False

        logger.debug("EventBus inicializado")

    def subscribe(
        self,
        event: BotEvent,
        callback: EventCallback,
        priority: int = 0,
    ) -> Callable[[], None]:
        """
        Registra um callback para um tipo de evento.

        Args:
            event: Tipo de evento a observar
            callback: Função a ser chamada quando evento ocorrer
            priority: Prioridade (maior = executa primeiro)
                      [não implementado ainda]

        Returns:
            Função para cancelar a inscrição (unsubscribe)
        """
        with self._lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            self._subscribers[event].append(callback)

        logger.debug(f"Subscriber adicionado para: {event.name}")

        # Retorna função de unsubscribe
        def unsubscribe():
            with self._lock:
                if event in self._subscribers:
                    try:
                        self._subscribers[event].remove(callback)
                    except ValueError:
                        pass

        return unsubscribe

    def subscribe_all(
        self,
        callback: EventCallback,
    ) -> Callable[[], None]:
        """
        Registra callback para TODOS os eventos (wildcard).

        Útil para logging, telemetria, debug.

        Args:
            callback: Função a ser chamada para qualquer evento

        Returns:
            Função para cancelar a inscrição
        """
        with self._lock:
            self._global_subscribers.append(callback)

        logger.debug("Global subscriber adicionado")

        def unsubscribe():
            with self._lock:
                try:
                    self._global_subscribers.remove(callback)
                except ValueError:
                    pass

        return unsubscribe

    def on(
        self,
        event: BotEvent,
    ) -> Callable[[EventCallback], EventCallback]:
        """
        Decorador para registrar handler de evento.

        Example:
            @bus.on(BotEvent.BALANCE_CHANGED)
            def handle_balance(data: EventData):
                print(data.payload)
        """

        def decorator(func: EventCallback) -> EventCallback:
            self.subscribe(event, func)
            return func

        return decorator

    def publish(
        self,
        event: BotEvent,
        payload: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> Optional[EventData]:
        """
        Publica um evento no barramento.

        Args:
            event: Tipo do evento
            payload: Dados do evento (dict)
            source: Identificador do componente que gerou o evento

        Returns:
            EventData criado ou None se pausado

        Example:
            bus.publish(BotEvent.BALANCE_CHANGED, {"old": 100, "new": 150})
        """
        if self._paused:
            logger.debug(f"EventBus pausado, ignorando: {event.name}")
            return None

        event_data = EventData(
            event_type=event,
            payload=payload or {},
            timestamp=time.time(),
            source=source,
        )

        # Adiciona ao histórico
        if self._history_limit > 0:
            with self._lock:
                self._history.append(event_data)
                # Limita tamanho do histórico
                if len(self._history) > self._history_limit:
                    self._history = self._history[-self._history_limit :]

        # Coleta subscribers (com lock)
        with self._lock:
            specific_subscribers = self._subscribers.get(event, []).copy()
            global_subscribers = self._global_subscribers.copy()

        # Executa callbacks (sem lock para evitar deadlocks)
        all_subscribers = specific_subscribers + global_subscribers

        for callback in all_subscribers:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(
                    f"Erro no handler {callback.__name__} " f"para {event.name}: {e}",
                    exc_info=True,
                )

        logger.debug(
            f"Evento publicado: {event.name} " f"({len(all_subscribers)} handlers)"
        )
        return event_data

    def publish_async(
        self,
        event: BotEvent,
        payload: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> None:
        """
        Publica evento em thread separada (não bloqueia).

        Útil para eventos que não precisam de resposta imediata.
        """
        thread = threading.Thread(
            target=self.publish,
            args=(event, payload, source),
            daemon=True,
            name=f"Event-{event.name}",
        )
        thread.start()

    def pause(self) -> None:
        """Pausa o EventBus (eventos são ignorados)."""
        self._paused = True
        logger.info("EventBus pausado")

    def resume(self) -> None:
        """Retoma o EventBus."""
        self._paused = False
        logger.info("EventBus retomado")

    def clear_subscribers(self, event: Optional[BotEvent] = None) -> None:
        """
        Remove todos os subscribers.

        Args:
            event: Se especificado, limpa apenas este evento.
                   Se None, limpa TODOS os subscribers.
        """
        with self._lock:
            if event:
                self._subscribers[event] = []
                logger.debug(f"Subscribers limpos para: {event.name}")
            else:
                self._subscribers.clear()
                self._global_subscribers.clear()
                logger.debug("Todos os subscribers removidos")

    def get_history(
        self,
        event_type: Optional[BotEvent] = None,
        limit: int = 50,
    ) -> List[EventData]:
        """
        Retorna histórico de eventos recentes.

        Args:
            event_type: Filtrar por tipo (None = todos)
            limit: Quantidade máxima a retornar

        Returns:
            Lista de EventData (mais recentes primeiro)
        """
        with self._lock:
            history = self._history.copy()

        if event_type:
            history = [e for e in history if e.event_type == event_type]

        return list(reversed(history[-limit:]))

    def get_subscriber_count(self, event: Optional[BotEvent] = None) -> int:
        """Retorna quantidade de subscribers."""
        with self._lock:
            if event:
                return len(self._subscribers.get(event, []))
            return sum(len(subs) for subs in self._subscribers.values())


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_event_bus: Optional[EventBus] = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """
    Retorna a instância singleton do EventBus.

    Thread-safe. Cria a instância na primeira chamada.

    Example:
        bus = get_event_bus()
        bus.publish(BotEvent.SESSION_STARTED, {"mode": "MODERADO"})
    """
    global _event_bus

    if _event_bus is None:
        with _event_bus_lock:
            # Double-check locking
            if _event_bus is None:
                _event_bus = EventBus()

    return _event_bus


def reset_event_bus() -> None:
    """
    Reseta o EventBus global (útil para testes).
    """
    global _event_bus
    with _event_bus_lock:
        if _event_bus:
            _event_bus.clear_subscribers()
        _event_bus = None


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS E DECORADORES
# ═══════════════════════════════════════════════════════════════════════════════


def emit(event: BotEvent, **kwargs: Any) -> Optional[EventData]:
    """
    Atalho para publicar evento no bus global.

    Example:
        emit(BotEvent.BALANCE_CHANGED, old=100, new=150)
    """
    return get_event_bus().publish(event, kwargs)


def emit_async(event: BotEvent, **kwargs: Any) -> None:
    """
    Atalho para publicar evento assíncrono no bus global.

    Example:
        emit_async(BotEvent.TELEMETRY_SENT, data={...})
    """
    get_event_bus().publish_async(event, kwargs)


def on_event(event: BotEvent) -> Callable[[EventCallback], EventCallback]:
    """
    Decorador standalone para registrar handlers.

    Example:
        @on_event(BotEvent.EXPLOSION_DETECTED)
        def handle_explosion(data: EventData):
            print(f"Explosão: {data['value']}x")
    """
    return get_event_bus().on(event)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Configura logging para ver os eventos
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO EVENTBUS - CrashBot v3.0")
    print("=" * 60)

    # Obtém o bus global
    bus = get_event_bus()

    # Registra handlers
    @bus.on(BotEvent.BALANCE_CHANGED)
    def handle_balance(data: EventData):
        print(f"[HANDLER] Saldo mudou: " f"R$ {data['old']:.2f} → R$ {data['new']:.2f}")

    @bus.on(BotEvent.EXPLOSION_DETECTED)
    def handle_explosion(data: EventData):
        value = data.get("value", 0)
        emoji = "🟢" if value >= 2.0 else "🔴"
        print(f"[HANDLER] {emoji} Explosão: {value:.2f}x")

    # Usando o atalho emit()
    print("\n--- Publicando eventos ---")
    emit(BotEvent.SESSION_STARTED, mode="MODERADO", balance=1000.0)
    emit(BotEvent.BALANCE_CHANGED, old=1000.0, new=1150.0)
    emit(BotEvent.EXPLOSION_DETECTED, value=2.45)
    emit(BotEvent.EXPLOSION_DETECTED, value=1.23)
    emit(BotEvent.BALANCE_CHANGED, old=1150.0, new=1200.0)

    # Mostra histórico
    print("\n--- Histórico de Eventos ---")
    for event_data in bus.get_history(limit=5):
        print(f"  {event_data.event_type.name}: {event_data.payload}")

    print("\n--- Stats ---")
    print(f"Total de subscribers: {bus.get_subscriber_count()}")
    print(
        f"Subscribers BALANCE_CHANGED: "
        f"{bus.get_subscriber_count(BotEvent.BALANCE_CHANGED)}"
    )

    print("\n✅ EventBus funcionando corretamente!")
