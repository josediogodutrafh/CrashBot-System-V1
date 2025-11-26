#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DATABASE MANAGER - Sistema de coleta e análise histórica
Módulo não intrusivo para salvar e analisar dados do bot
Integração mínima: apenas 2-3 linhas no bot principal
"""

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from config import DB_PATH

# Constantes para evitar "Magic Strings" e erros de digitação
RESULTADO_HIT = "hit"
RESULTADO_MISS = "miss"


@dataclass
class RoundData:
    """Dados de uma rodada"""

    timestamp: str
    multiplicador: float
    duracao_rodada: float
    fase_detectada: str
    saldo_momento: float
    sessao_id: str
    estrategia_ativada: Optional[str] = None
    observacoes: Optional[str] = None


@dataclass
class BetData:
    """Dados de uma aposta executada"""

    rodada_id: int
    estrategia: str
    aposta_1: float
    target_1: float
    aposta_2: float
    target_2: float
    resultado_1: str  # 'hit', 'miss'
    resultado_2: str  # 'hit', 'miss'
    lucro_liquido: float
    timestamp: str


@dataclass
class SessionStats:
    """Estatísticas da sessão"""

    total_rounds: int = 0
    total_bets: int = 0
    hit_rate: float = 0.0
    profit_loss: float = 0.0
    avg_multiplier: float = 0.0
    session_duration: str = "00:00:00"
    best_strategy: str = "N/A"


class DatabaseManager:
    """Gerenciador de banco de dados para histórico do bot"""

    def __init__(self, db_filename: str = "crash_bot_historico.db"):
        self.db_lock = threading.Lock()
        self.db_path = Path(DB_PATH)
        self.session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_start = datetime.now()

        self.logger = logging.getLogger(f"{__name__}.{self.session_id}")
        self.logger.setLevel(logging.INFO)

        # Configuração do Logger
        if not self.logger.handlers:
            handler = logging.FileHandler("database_manager.log")
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Chama a inicialização (criação de tabelas) de forma thread-safe
        try:
            with self._get_db_cursor(commit_on_exit=True) as cursor:
                self._create_tables(cursor)
                self._create_indexes(cursor)
                self._ensure_session_record(cursor)
            self.logger.info("Base de dados inicializada com sucesso")
        except Exception as e:
            self.logger.error(f"Erro CRÍTICO ao inicializar BD: {e}")
            raise

        print("✅ DatabaseManager inicializado")
        print(f"📁 Arquivo: {self.db_path}")
        print(f"🆔 Sessão: {self.session_id}")

    def _connect_db(self):
        """Abre e retorna uma nova conexão com o banco de dados."""
        try:
            # Garante que o diretório exista
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            # Conecta (com timeout para evitar problemas de concorrência)
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")  # Bom para concorrência
            return conn
        except Exception as e:
            self.logger.error(f"Erro CRÍTICO ao conectar ao DB: {e}", exc_info=True)
            raise  # Se não puder conectar, o bot não pode funcionar.

    @contextmanager
    def _get_db_cursor(self, commit_on_exit: bool = False):
        """
        Gerenciador de contexto que ABRE e FECHA sua própria conexão
        para ser 100% thread-safe.
        """
        conn = None
        cursor = None
        try:
            # 1. Abre uma nova conexão CADA VEZ
            conn = self._connect_db()
            cursor = conn.cursor()
            yield cursor

            # 2. Se o 'with' terminou sem erro, faz o commit (se solicitado)
            if commit_on_exit:
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erro no cursor do DB: {e}")
            if conn:
                conn.rollback()  # Desfaz alterações em caso de erro
            raise  # Propaga o erro
        finally:
            # 3. Garante que tudo seja fechado
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def _execute_sql(self, cursor: sqlite3.Cursor, sql_command: str):
        """Helper para executar um comando SQL."""
        try:
            cursor.execute(sql_command)
        except Exception as e:
            self.logger.error(f"Erro ao executar SQL: {e}\nComando: {sql_command}")
            raise

    def _create_tables(self, cursor: sqlite3.Cursor):
        """Cria as tabelas do banco de dados, se não existirem."""

        # Tabela 1: Sessoes
        sql_sessoes = """
        CREATE TABLE IF NOT EXISTS sessoes (
            sessao_id TEXT PRIMARY KEY,
            inicio TEXT NOT NULL,
            fim TEXT,
            saldo_inicial REAL,
            saldo_final REAL,
            lucro_liquido REAL DEFAULT 0.0,
            total_rodadas INTEGER DEFAULT 0,
            total_apostas INTEGER DEFAULT 0
        )
        """
        self._execute_sql(cursor, sql_sessoes)

        # Tabela 2: Multiplicadores (Rodadas)
        sql_multiplicadores = """
        CREATE TABLE IF NOT EXISTS multiplicadores_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            multiplicador REAL NOT NULL,
            duracao_rodada REAL,
            fase_detectada TEXT,
            saldo_momento REAL,
            sessao_id TEXT NOT NULL,
            estrategia_ativada TEXT,
            observacoes TEXT,
            FOREIGN KEY (sessao_id) REFERENCES sessoes (sessao_id)
        )
        """
        self._execute_sql(cursor, sql_multiplicadores)

        # Tabela 3: Apostas
        sql_apostas = """
        CREATE TABLE IF NOT EXISTS apostas_executadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rodada_id INTEGER NOT NULL,
            estrategia TEXT NOT NULL,
            aposta_1 REAL,
            target_1 REAL,
            aposta_2 REAL,
            target_2 REAL,
            resultado_1 TEXT,
            resultado_2 TEXT,
            lucro_liquido REAL,
            timestamp TEXT NOT NULL,
            sessao_id TEXT NOT NULL,
            FOREIGN KEY (rodada_id) REFERENCES multiplicadores_historico (id),
            FOREIGN KEY (sessao_id) REFERENCES sessoes (sessao_id)
        )
        """
        self._execute_sql(cursor, sql_apostas)

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Cria índices para acelerar as consultas."""
        try:
            # Índice para buscar rodadas por sessão
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_mult_sessao_id ON multiplicadores_historico (sessao_id)"
            )
            # Índice para buscar apostas por sessão
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_apostas_sessao_id ON apostas_executadas (sessao_id)"
            )
            # Índice para buscar apostas por rodada
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_apostas_rodada_id ON apostas_executadas (rodada_id)"
            )
        except Exception as e:
            self.logger.warning(f"Erro ao criar índices: {e}")

    def _ensure_session_record(self, cursor: sqlite3.Cursor):
        """Garante o registro para a sessão atual na tabela de sessoes."""
        cursor.execute(
            """
            INSERT OR IGNORE INTO sessoes (sessao_id, inicio)
            VALUES (?, ?)
            """,
            (self.session_id, self.session_start.isoformat()),
        )

    def _update_session_bet_count(self, cursor: sqlite3.Cursor):
        """(Novo) Atualiza o contador de apostas da sessão atual."""
        try:
            cursor.execute(
                "UPDATE sessoes SET total_apostas = total_apostas + 1 WHERE sessao_id = ?",
                (self.session_id,),
            )
        except Exception as e:
            self.logger.error(f"Erro ao atualizar contador de apostas: {e}")
            raise

    def save_round(self, round_data: RoundData) -> Optional[int]:
        """Salva os dados de uma rodada no banco."""
        try:
            # Pede para fazer commit ao sair
            with self._get_db_cursor(commit_on_exit=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO multiplicadores_historico (
                        timestamp, multiplicador, duracao_rodada, fase_detectada,
                        saldo_momento, sessao_id, estrategia_ativada, observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        round_data.timestamp,
                        round_data.multiplicador,
                        round_data.duracao_rodada,
                        round_data.fase_detectada,
                        round_data.saldo_momento,
                        round_data.sessao_id,
                        round_data.estrategia_ativada,
                        round_data.observacoes,
                    ),
                )

                # Atualiza o contador de rodadas da sessão
                cursor.execute(
                    "UPDATE sessoes SET total_rodadas = total_rodadas + 1 WHERE sessao_id = ?",
                    (self.session_id,),
                )

                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Erro ao salvar rodada: {e}")
            return None

    def save_bet(self, bet_data: BetData) -> Optional[int]:
        """Salva uma aposta executada no banco."""
        try:
            # Pede para fazer commit ao sair
            with self._get_db_cursor(commit_on_exit=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO apostas_executadas (
                        rodada_id, estrategia, aposta_1, target_1, aposta_2, target_2,
                        resultado_1, resultado_2, lucro_liquido, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bet_data.rodada_id,
                        bet_data.estrategia,
                        bet_data.aposta_1,
                        bet_data.target_1,
                        bet_data.aposta_2,
                        bet_data.target_2,
                        bet_data.resultado_1,
                        bet_data.resultado_2,
                        bet_data.lucro_liquido,
                        bet_data.timestamp,
                    ),
                )

                # CHAMA O HELPER PARA ATUALIZAR O CONTADOR DE APOSTAS
                self._update_session_bet_count(cursor)

                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Erro ao salvar aposta: {e}")
            return None

    def _process_stats_results(
        self, round_stats, bet_stats, session_start_row
    ) -> SessionStats:
        """Processa os resultados brutos das queries e retorna um objeto SessionStats."""
        duration_str = "00:00:00"
        try:
            if session_start_row and session_start_row[0]:
                start_time = datetime.fromisoformat(session_start_row[0])
                duration = datetime.now() - start_time
                duration_str = str(duration).split(".")[0]
        except Exception as e:
            self.logger.error(f"Erro ao calcular duracao da sessao: {e}")

        # --- LÓGICA DE SEGURANÇA PARA round_stats ---
        total_rounds = (
            round_stats[0] if round_stats and round_stats[0] is not None else 0
        )
        avg_multiplier = (
            round_stats[1] if round_stats and round_stats[1] is not None else 0.0
        )

        # --- LÓGICA DE SEGURANÇA PARA bet_stats ---
        total_bets = bet_stats[0] if bet_stats and bet_stats[0] is not None else 0
        hits = bet_stats[1] if bet_stats and bet_stats[1] is not None else 0
        profit_loss = bet_stats[2] if bet_stats and bet_stats[2] is not None else 0.0
        best_strategy = bet_stats[3] if bet_stats and bet_stats[3] else "Nenhuma"

        hit_rate = (hits / total_bets * 100) if total_bets > 0 else 0.0

        return SessionStats(
            total_rounds=total_rounds,
            total_bets=total_bets,
            hit_rate=hit_rate,
            profit_loss=profit_loss,
            avg_multiplier=avg_multiplier,
            session_duration=duration_str,
            best_strategy=best_strategy,
        )

    def get_session_stats(self, sessao_id: Optional[str] = None) -> SessionStats:
        """Obtém estatísticas da sessão atual ou especificada."""
        if not sessao_id:
            sessao_id = self.session_id

        try:
            # Usa o cursor thread-safe (sem commit)
            with self._get_db_cursor() as cursor:
                # Query 1: Estatísticas das rodadas
                cursor.execute(
                    """
                    SELECT COUNT(*), AVG(multiplicador)
                    FROM multiplicadores_historico WHERE sessao_id = ?
                    """,
                    (sessao_id,),
                )
                round_stats = cursor.fetchone()

                # Query 2: Estatísticas das apostas
                cursor.execute(
                    """
                    SELECT COUNT(*),
                        SUM(CASE WHEN resultado_1 = 'hit' THEN 1 ELSE 0 END),
                        SUM(lucro_liquido),
                        estrategia
                    FROM apostas_executadas
                    WHERE sessao_id = ?
                    GROUP BY estrategia ORDER BY COUNT(*) DESC LIMIT 1
                    """,
                    (sessao_id,),
                )
                bet_stats = cursor.fetchone()

                # Query 3: Duração da sessão
                cursor.execute(
                    "SELECT inicio FROM sessoes WHERE sessao_id = ?", (sessao_id,)
                )
                session_start_row = cursor.fetchone()

            # Delega o processamento para o novo método
            return self._process_stats_results(
                round_stats, bet_stats, session_start_row
            )

        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return SessionStats()

    def _process_performance_results(self, results: List[tuple]) -> Dict:
        """Processa os resultados da query de performance e retorna um dicionário formatado."""
        performance = {}
        for row in results:
            estrategia, total_bets, hits = row[0], row[1], row[2]
            if total_bets > 0:
                performance[estrategia] = {
                    "total_bets": total_bets,
                    "hits": hits,
                    "hit_rate": round((hits / total_bets * 100), 1),
                    "total_profit": round(row[3] or 0.0, 2),
                    "avg_profit": round(row[4] or 0.0, 2),
                    "min_profit": round(row[5] or 0.0, 2),
                    "max_profit": round(row[6] or 0.0, 2),
                }
        return performance

    def get_strategy_performance(self, days: int = 30) -> Dict:
        """Analisa a performance das estratégias buscando dados e processando-os."""
        try:
            # Usa o cursor thread-safe (sem commit)
            with self._get_db_cursor() as cursor:
                date_limit = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(
                    """
                    SELECT
                        estrategia, COUNT(*),
                        SUM(CASE WHEN resultado_1 = 'hit' THEN 1 ELSE 0 END),
                        SUM(lucro_liquido), AVG(lucro_liquido),
                        MIN(lucro_liquido), MAX(lucro_liquido)
                    FROM apostas_executadas
                    WHERE timestamp >= ?
                    GROUP BY estrategia
                    ORDER BY COUNT(*) DESC
                    """,
                    (date_limit,),
                )
                results = cursor.fetchall()

            # Delega o processamento e formatação para o novo método
            return self._process_performance_results(results)

        except Exception as e:
            self.logger.error(f"Erro na análise de estratégias: {e}")
            return {}

    @contextmanager
    def _get_db_connection(self):
        """Gerenciador de contexto para obter a CONEXÃO com o banco de dados (para Pandas)."""
        conn = None
        try:
            # Usa o db_lock para garantir que a conexão/commit/close seja atômica
            with self.db_lock:
                conn = self._connect_db()  # Abre uma nova conexão
                yield conn  # Retorna a conexão
                conn.commit()  # Salva quaisquer alterações feitas pelo usuário
        except Exception as e:
            self.logger.error(f"Erro na conexão com o banco de dados: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def export_data(
        self, format: str = "csv", days: int = 30, output_dir: str = "exports"
    ) -> str:
        """Exporta dados para CSV ou JSON"""
        try:
            Path(output_dir).mkdir(exist_ok=True)
            date_limit = (datetime.now() - timedelta(days=days)).isoformat()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Pandas (pd.read_sql_query) precisa de um objeto de CONEXÃO,
            # por isso usamos _get_db_connection() aqui.
            with self._get_db_connection() as conn:
                query = """
                    SELECT
                        h.id as rodada_id, h.timestamp, h.multiplicador,
                        h.duracao_rodada, h.fase_detectada, h.saldo_momento,
                        h.sessao_id, h.estrategia_ativada,
                        a.estrategia as aposta_estrategia, a.aposta_1,
                        a.target_1, a.aposta_2, a.target_2, a.resultado_1,
                        a.resultado_2, a.lucro_liquido
                    FROM multiplicadores_historico h
                    LEFT JOIN apostas_executadas a ON h.id = a.rodada_id
                    WHERE h.timestamp >= ?
                    ORDER BY h.timestamp DESC
                    """
                df = pd.read_sql_query(query, conn, params=(date_limit,))

            filepath = ""
            if format.lower() == "csv":
                filename = f"crash_bot_data_{timestamp}.csv"
                filepath = os.path.join(output_dir, filename)
                df.to_csv(filepath, index=False, encoding="utf-8")
            elif format.lower() == "json":
                filename = f"crash_bot_data_{timestamp}.json"
                filepath = os.path.join(output_dir, filename)
                df.to_json(filepath, orient="records", indent=2, date_format="iso")
            else:
                raise ValueError(f"Formato não suportado: {format}")

            self.logger.info(f"Dados exportados: {filepath} ({len(df)} registros)")
            return filepath
        except Exception as e:
            self.logger.error(f"Erro na exportação: {e}")
            return ""

    def get_recent_rounds(self, limit: int = 10) -> List[Dict]:
        """Obtém rodadas recentes"""
        try:
            # Usa o cursor thread-safe (sem commit)
            with self._get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT timestamp, multiplicador, fase_detectada,
                            saldo_momento, estrategia_ativada
                    FROM multiplicadores_historico
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                results = cursor.fetchall()
                return [
                    {
                        "timestamp": row[0],
                        "multiplicador": row[1],
                        "fase": row[2],
                        "saldo": row[3],
                        "estrategia": row[4],
                    }
                    for row in results
                ]
        except Exception as e:
            self.logger.error(f"Erro ao buscar rodadas recentes: {e}")
            return []

    def close_session(self, saldo_final: Optional[float] = None):
        """Fecha a sessão atual e salva estatísticas finais."""
        try:
            # Usa o cursor thread-safe (com commit)
            with self._get_db_cursor(commit_on_exit=True) as cursor:
                fim = datetime.now().isoformat()

                # Calcular lucro total
                cursor.execute(
                    "SELECT SUM(lucro_liquido) FROM apostas_executadas WHERE sessao_id = ?",
                    (self.session_id,),
                )
                lucro_total_row = cursor.fetchone()
                # Adiciona verificação de segurança
                lucro_total = (
                    lucro_total_row[0]
                    if lucro_total_row and lucro_total_row[0] is not None
                    else 0.0
                )

                # Atualizar a tabela de sessões
                cursor.execute(
                    """
                    UPDATE sessoes
                    SET fim = ?, saldo_final = ?, lucro_liquido = ?
                    WHERE sessao_id = ?
                    """,
                    (fim, saldo_final, lucro_total, self.session_id),
                )

            self.logger.info(
                f"Sessão {self.session_id} encerrada | Lucro: R${lucro_total:.2f}"
            )

        except Exception as e:
            self.logger.error(f"Erro ao salvar dados ao fechar sessão: {e}")

        self.logger.info("Solicitação de fechamento de sessão concluída.")

    def _process_database_stats(
        self, total_rounds, total_bets, total_sessions, first_round, last_round
    ) -> Dict:
        """Processa os dados brutos e monta o dicionário de estatísticas do banco de dados."""
        return {
            "total_rounds": total_rounds or 0,
            "total_bets": total_bets or 0,
            "total_sessions": total_sessions or 0,
            "first_round": first_round,
            "last_round": last_round,
            "database_size_mb": round(os.path.getsize(self.db_path) / (1024 * 1024), 2),
        }

    def get_database_stats(self) -> Dict:
        """Busca e retorna estatísticas gerais do banco de dados."""
        try:
            # Usa o cursor thread-safe (sem commit)
            with self._get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM multiplicadores_historico")
                total_rounds = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM apostas_executadas")
                total_bets = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(DISTINCT sessao_id) FROM multiplicadores_historico"
                )
                total_sessions = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT MIN(timestamp), MAX(timestamp) FROM multiplicadores_historico"
                )
                first_round, last_round = cursor.fetchone()

            # Delega a formatação para o novo método
            return self._process_database_stats(
                total_rounds, total_bets, total_sessions, first_round, last_round
            )

        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas do BD: {e}")
            return {}


def main():
    """Script para consultar dados independentemente"""
    db = DatabaseManager()

    print("📊 ESTATÍSTICAS DO CRASH BOT")
    print("=" * 40)

    session_stats = db.get_session_stats()
    print("🎯 Sessão Atual:")
    print(f"   Rodadas: {session_stats.total_rounds}")
    print(f"   Apostas: {session_stats.total_bets}")
    print(f"   Taxa de acerto: {session_stats.hit_rate:.1f}%")
    print(f"   P&L: R$ {session_stats.profit_loss:.2f}")
    print(f"   Duração: {session_stats.session_duration}")
    print()

    if strategy_perf := db.get_strategy_performance():
        print("🎲 Performance das Estratégias:")
        for strategy, data in strategy_perf.items():
            print(
                f"   {strategy}: {data['hit_rate']:.1f}% | "
                f"Total: R$ {data['total_profit']:.2f}"
            )
        print()

    if recent := db.get_recent_rounds(5):
        print("🕐 Últimas 5 Rodadas:")
        for round_data in recent:
            timestamp = datetime.fromisoformat(round_data["timestamp"]).strftime(
                "%H:%M"
            )
            print(
                f"   {timestamp} | {round_data['multiplicador']:.2f}x | "
                f"{round_data['fase']} | R$ {round_data['saldo']:.2f}"
            )


if __name__ == "__main__":
    main()
