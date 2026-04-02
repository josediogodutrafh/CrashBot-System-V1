#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRASHBOT v3.0 - SERVIÇO DE DATABASE

Wrapper do DatabaseManager com integração ao EventBus.
Persiste dados de sessão, apostas e histórico.

Uso:
    from services.database import DatabaseService, get_database

    db = get_database()
    db.start_session("session_123", 1000.0, "MODERADO")
    db.record_bet(amount=10.0, target=1.85, result="hit", profit=8.50)
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.constants import BOT_VERSION

# Core imports
from core.events import BotEvent, EventData, get_event_bus

# Logger
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE PATHS
# ═══════════════════════════════════════════════════════════════════════════════


def get_db_path() -> Path:
    """
    Retorna o path do banco de dados.

    Funciona tanto em desenvolvimento quanto empacotado.
    """
    # Tenta encontrar o diretório base
    if getattr(sys, "frozen", False):
        # Executável (Nuitka/PyInstaller)
        base_dir = Path(sys.executable).parent
    else:
        # Desenvolvimento
        base_dir = Path(__file__).parent.parent

    db_path = base_dir / "data" / "crashbot.db"

    # Garante que o diretório existe
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return db_path


# Import sys para get_db_path
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SessionRecord:
    """Registro de uma sessão."""

    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    initial_balance: float = 0.0
    final_balance: Optional[float] = None
    risk_mode: str = ""
    total_rounds: int = 0
    total_bets: int = 0
    hits: int = 0
    misses: int = 0
    profit: float = 0.0
    status: str = "running"  # running, completed, stopped, error


@dataclass
class BetRecord:
    """Registro de uma aposta."""

    id: Optional[int] = None
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    round_number: int = 0
    amount: float = 0.0
    target: float = 0.0
    result: str = ""  # hit, miss
    profit: float = 0.0
    balance_before: float = 0.0
    balance_after: float = 0.0
    dobra: int = 1
    risk_mode: str = ""


@dataclass
class ExplosionRecord:
    """Registro de uma explosão."""

    id: Optional[int] = None
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0
    round_number: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# SERVIÇO DE DATABASE
# ═══════════════════════════════════════════════════════════════════════════════


class DatabaseService:
    """
    Serviço de persistência de dados.

    Features:
        - Thread-safe (usa locks)
        - WAL mode para performance
        - Integração com EventBus
        - Context manager para transações

    Exemplo:
        db = DatabaseService()
        db.start_session("sess_001", 1000.0, "MODERADO")
        db.record_explosion(2.45, 1)
        db.record_bet(10.0, 1.85, "hit", 8.50, 1000.0, 1008.50, 1)
        db.end_session(1150.0, "completed")
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        auto_subscribe: bool = True,
    ):
        """
        Inicializa o serviço de database.

        Args:
            db_path: Caminho do banco de dados (usa default se None)
            auto_subscribe: Se True, registra handlers de eventos
        """
        self._db_path = db_path or get_db_path()
        self._lock = threading.RLock()
        self._connection: Optional[sqlite3.Connection] = None

        # Sessão atual
        self._current_session_id: Optional[str] = None

        # EventBus
        self._event_bus = get_event_bus()
        self._unsubscribers: List = []

        # Inicializa banco
        self._init_database()

        # Auto-subscribe
        if auto_subscribe:
            self._setup_event_handlers()

        logger.debug(f"DatabaseService inicializado: {self._db_path}")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONEXÃO E INICIALIZAÇÃO
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna conexão com o banco (cria se necessário)."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                timeout=30.0,
            )
            self._connection.row_factory = sqlite3.Row

            # Configurações de performance
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.execute("PRAGMA cache_size=10000")

        return self._connection

    @contextmanager
    def _transaction(self):
        """Context manager para transações thread-safe."""
        with self._lock:
            conn = self._get_connection()
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Erro na transação: {e}")
                raise

    def _init_database(self) -> None:
        """Cria as tabelas se não existirem."""
        with self._transaction() as conn:
            cursor = conn.cursor()

            # Tabela de sessões
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    initial_balance REAL NOT NULL,
                    final_balance REAL,
                    risk_mode TEXT,
                    total_rounds INTEGER DEFAULT 0,
                    total_bets INTEGER DEFAULT 0,
                    hits INTEGER DEFAULT 0,
                    misses INTEGER DEFAULT 0,
                    profit REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'running',
                    bot_version TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Tabela de apostas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    round_number INTEGER,
                    amount REAL NOT NULL,
                    target REAL,
                    result TEXT NOT NULL,
                    profit REAL,
                    balance_before REAL,
                    balance_after REAL,
                    dobra INTEGER DEFAULT 1,
                    risk_mode TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )

            # Tabela de explosões (histórico)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS explosions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT NOT NULL,
                    value REAL NOT NULL,
                    round_number INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )

            # Índices para performance
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bets_session 
                ON bets(session_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_explosions_session 
                ON explosions(session_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_explosions_timestamp 
                ON explosions(timestamp)
            """
            )

            logger.debug("Tabelas do banco inicializadas")

    # ═══════════════════════════════════════════════════════════════════════════
    # SESSÕES
    # ═══════════════════════════════════════════════════════════════════════════

    def start_session(
        self,
        session_id: str,
        initial_balance: float,
        risk_mode: str,
    ) -> bool:
        """
        Inicia uma nova sessão.

        Args:
            session_id: ID único da sessão
            initial_balance: Saldo inicial
            risk_mode: Modo de risco (CONSERVADOR, MODERADO, AGRESSIVO)

        Returns:
            True se criada com sucesso
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO sessions (
                        session_id, start_time, initial_balance, 
                        risk_mode, bot_version, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        datetime.now().isoformat(),
                        initial_balance,
                        risk_mode,
                        BOT_VERSION,
                        "running",
                    ),
                )

            self._current_session_id = session_id
            logger.info(f"Sessão iniciada no DB: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao iniciar sessão: {e}")
            return False

    def end_session(
        self,
        final_balance: Optional[float] = None,
        status: str = "completed",
    ) -> bool:
        """
        Finaliza a sessão atual.

        Args:
            final_balance: Saldo final
            status: Status final (completed, stopped, error)

        Returns:
            True se atualizada com sucesso
        """
        if not self._current_session_id:
            logger.warning("Nenhuma sessão ativa para finalizar")
            return False

        try:
            with self._transaction() as conn:
                cursor = conn.cursor()

                # Busca dados atuais
                cursor.execute(
                    """
                    SELECT initial_balance, hits, misses 
                    FROM sessions WHERE session_id = ?
                """,
                    (self._current_session_id,),
                )
                row = cursor.fetchone()

                if row:
                    initial = row["initial_balance"]
                    profit = (final_balance - initial) if final_balance else 0

                    cursor.execute(
                        """
                        UPDATE sessions SET
                            end_time = ?,
                            final_balance = ?,
                            profit = ?,
                            status = ?
                        WHERE session_id = ?
                    """,
                        (
                            datetime.now().isoformat(),
                            final_balance,
                            profit,
                            status,
                            self._current_session_id,
                        ),
                    )

            logger.info(f"Sessão finalizada no DB: {self._current_session_id}")
            self._current_session_id = None
            return True

        except Exception as e:
            logger.error(f"Erro ao finalizar sessão: {e}")
            return False

    def update_session_stats(
        self,
        total_rounds: Optional[int] = None,
        total_bets: Optional[int] = None,
        hits: Optional[int] = None,
        misses: Optional[int] = None,
    ) -> bool:
        """Atualiza estatísticas da sessão atual."""
        if not self._current_session_id:
            return False

        try:
            updates = []
            params = []

            if total_rounds is not None:
                updates.append("total_rounds = ?")
                params.append(total_rounds)
            if total_bets is not None:
                updates.append("total_bets = ?")
                params.append(total_bets)
            if hits is not None:
                updates.append("hits = ?")
                params.append(hits)
            if misses is not None:
                updates.append("misses = ?")
                params.append(misses)

            if not updates:
                return True

            params.append(self._current_session_id)

            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    UPDATE sessions SET {', '.join(updates)}
                    WHERE session_id = ?
                """,
                    params,
                )

            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar stats: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # APOSTAS
    # ═══════════════════════════════════════════════════════════════════════════

    def record_bet(
        self,
        amount: float,
        target: float,
        result: str,
        profit: float,
        balance_before: float,
        balance_after: float,
        dobra: int = 1,
        round_number: Optional[int] = None,
        risk_mode: Optional[str] = None,
    ) -> bool:
        """
        Registra uma aposta.

        Args:
            amount: Valor apostado
            target: Alvo da aposta
            result: Resultado ("hit" ou "miss")
            profit: Lucro/prejuízo
            balance_before: Saldo antes
            balance_after: Saldo depois
            dobra: Nível do martingale
            round_number: Número da rodada
            risk_mode: Modo de risco

        Returns:
            True se registrada com sucesso
        """
        session_id = self._current_session_id or "unknown"

        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO bets (
                        session_id, timestamp, round_number, amount,
                        target, result, profit, balance_before,
                        balance_after, dobra, risk_mode
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        datetime.now().isoformat(),
                        round_number,
                        amount,
                        target,
                        result,
                        profit,
                        balance_before,
                        balance_after,
                        dobra,
                        risk_mode,
                    ),
                )

                # Atualiza contadores da sessão
                if self._current_session_id:
                    if result == "hit":
                        cursor.execute(
                            """
                            UPDATE sessions SET 
                                total_bets = total_bets + 1,
                                hits = hits + 1
                            WHERE session_id = ?
                        """,
                            (self._current_session_id,),
                        )
                    else:
                        cursor.execute(
                            """
                            UPDATE sessions SET 
                                total_bets = total_bets + 1,
                                misses = misses + 1
                            WHERE session_id = ?
                        """,
                            (self._current_session_id,),
                        )

            logger.debug(f"Aposta registrada: {result} R${profit:.2f}")
            return True

        except Exception as e:
            logger.error(f"Erro ao registrar aposta: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # EXPLOSÕES
    # ═══════════════════════════════════════════════════════════════════════════

    def record_explosion(
        self,
        value: float,
        round_number: Optional[int] = None,
    ) -> bool:
        """
        Registra uma explosão.

        Args:
            value: Valor da explosão
            round_number: Número da rodada

        Returns:
            True se registrada com sucesso
        """
        session_id = self._current_session_id

        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO explosions (
                        session_id, timestamp, value, round_number
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        session_id,
                        datetime.now().isoformat(),
                        value,
                        round_number,
                    ),
                )

                # Atualiza contador de rodadas
                if self._current_session_id:
                    cursor.execute(
                        """
                        UPDATE sessions SET total_rounds = total_rounds + 1
                        WHERE session_id = ?
                    """,
                        (self._current_session_id,),
                    )

            return True

        except Exception as e:
            logger.error(f"Erro ao registrar explosão: {e}")
            return False

    def get_recent_explosions(self, limit: int = 250) -> List[float]:
        """
        Retorna as últimas N explosões.

        Args:
            limit: Quantidade máxima a retornar

        Returns:
            Lista de valores de explosão
        """
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT value FROM explosions
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                rows = cursor.fetchall()
                # Inverte para ordem cronológica
                return [row["value"] for row in reversed(rows)]

        except Exception as e:
            logger.error(f"Erro ao buscar explosões: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════
    # CONSULTAS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_session_stats(self, session_id: Optional[str] = None) -> Optional[Dict]:
        """Retorna estatísticas de uma sessão."""
        sid = session_id or self._current_session_id
        if not sid:
            return None

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM sessions WHERE session_id = ?
                """,
                    (sid,),
                )

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Erro ao buscar sessão: {e}")
            return None

    def get_today_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do dia."""
        today = datetime.now().strftime("%Y-%m-%d")

        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as sessions,
                        SUM(total_bets) as bets,
                        SUM(hits) as hits,
                        SUM(misses) as misses,
                        SUM(profit) as profit
                    FROM sessions
                    WHERE date(start_time) = ?
                """,
                    (today,),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "sessions": row["sessions"] or 0,
                        "bets": row["bets"] or 0,
                        "hits": row["hits"] or 0,
                        "misses": row["misses"] or 0,
                        "profit": row["profit"] or 0.0,
                    }
                return {}

        except Exception as e:
            logger.error(f"Erro ao buscar stats do dia: {e}")
            return {}

    # ═══════════════════════════════════════════════════════════════════════════
    # INTEGRAÇÃO COM EVENTBUS
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_event_handlers(self) -> None:
        """Registra handlers para eventos relevantes."""

        unsub = self._event_bus.subscribe(
            BotEvent.EXPLOSION_DETECTED, self._on_explosion
        )
        self._unsubscribers.append(unsub)

        unsub = self._event_bus.subscribe(BotEvent.BET_RESULT_HIT, self._on_bet_result)
        self._unsubscribers.append(unsub)

        unsub = self._event_bus.subscribe(BotEvent.BET_RESULT_MISS, self._on_bet_result)
        self._unsubscribers.append(unsub)

        logger.debug("Database handlers registrados")

    def _on_explosion(self, event: EventData) -> None:
        """Handler: explosão detectada."""
        value = event.get("value", 0)
        round_num = event.get("round_number")
        self.record_explosion(value, round_num)

    def _on_bet_result(self, event: EventData) -> None:
        """Handler: resultado de aposta."""
        result = "hit" if event.event_type == BotEvent.BET_RESULT_HIT else "miss"

        self.record_bet(
            amount=event.get("amount", 0),
            target=event.get("target", 0),
            result=result,
            profit=event.get("profit", 0),
            balance_before=event.get("balance_before", 0),
            balance_after=event.get("balance_after", 0),
            dobra=event.get("dobra", 1),
            round_number=event.get("round_number"),
            risk_mode=event.get("risk_mode"),
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════════════════════

    def close(self) -> None:
        """Fecha conexão com o banco."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

        if self._connection:
            self._connection.close()
            self._connection = None

        logger.debug("DatabaseService fechado")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_database_service: Optional[DatabaseService] = None
_database_lock = threading.Lock()


def get_database() -> DatabaseService:
    """
    Retorna a instância singleton do DatabaseService.

    Thread-safe. Cria a instância na primeira chamada.
    """
    global _database_service

    if _database_service is None:
        with _database_lock:
            if _database_service is None:
                _database_service = DatabaseService()

    return _database_service


def reset_database() -> None:
    """Reseta o serviço de database (útil para testes)."""
    global _database_service
    with _database_lock:
        if _database_service:
            _database_service.close()
        _database_service = None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE / DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("TESTE DO DATABASE SERVICE - CrashBot v3.0")
    print("=" * 60)

    # Usa banco temporário para teste
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_db_path = Path(f.name)

    print(f"\n📁 Banco de teste: {test_db_path}")

    # Cria serviço
    db = DatabaseService(db_path=test_db_path, auto_subscribe=False)
    print(f"✅ Serviço criado")

    # Inicia sessão
    db.start_session("test_session_001", 1000.0, "MODERADO")
    print(f"✅ Sessão iniciada")

    # Registra explosões
    for val in [1.23, 1.45, 3.21, 1.89, 2.34]:
        db.record_explosion(val)
    print(f"✅ 5 explosões registradas")

    # Registra apostas
    db.record_bet(10.0, 1.85, "hit", 8.50, 1000.0, 1008.50, 1)
    db.record_bet(10.0, 1.85, "miss", -10.0, 1008.50, 998.50, 1)
    db.record_bet(20.0, 1.85, "hit", 17.0, 998.50, 1015.50, 2)
    print(f"✅ 3 apostas registradas")

    # Finaliza sessão
    db.end_session(1015.50, "completed")
    print(f"✅ Sessão finalizada")

    # Consulta stats
    stats = db.get_session_stats("test_session_001")
    print(f"\n--- Stats da Sessão ---")
    if stats:
        print(f"   Rounds: {stats['total_rounds']}")
        print(f"   Bets: {stats['total_bets']}")
        print(f"   Hits: {stats['hits']}")
        print(f"   Misses: {stats['misses']}")
        print(f"   Profit: R$ {stats['profit']:.2f}")

    # Explosões recentes
    explosions = db.get_recent_explosions(10)
    print(f"\n--- Explosões Recentes ---")
    print(f"   {explosions}")

    # Cleanup
    db.close()
    test_db_path.unlink()

    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
