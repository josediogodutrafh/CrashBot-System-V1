"""
Modelo: LogBot
Tabela que armazena logs de telemetria dos bots.
"""

from datetime import datetime
from typing import cast

from app.database import Base
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func


class LogBot(Base):
    """
    Modelo da tabela 'log_bot'.
    Armazena telemetria enviada pelos bots em operação.
    """

    __tablename__ = "log_bot"

    # Campos principais
    id = Column(Integer, primary_key=True, index=True)
    sessao_id = Column(String(100), nullable=False, index=True)
    hwid = Column(String(100), nullable=True, index=True)

    # Timestamp
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Dados do log
    tipo = Column(
        String(50), nullable=False, index=True
    )  # sessao_inicio, aposta, sessao_fim, erro, modo_alterado, alerta
    dados = Column(Text, nullable=True)  # JSON com dados extras
    lucro = Column(Float, default=0.0, nullable=False)

    # === NOVOS CAMPOS DE TELEMETRIA ===
    # Vínculo direto com licença
    licenca_id = Column(Integer, nullable=True, index=True)

    # Dados financeiros
    saldo = Column(Float, nullable=True)
    valor_aposta = Column(Float, nullable=True)
    banca_inicial = Column(Float, nullable=True)
    banca_final = Column(Float, nullable=True)

    # Dados de jogo
    modo_risco = Column(
        String(20), nullable=True, index=True
    )  # CONSERVADOR, MODERADO, AGRESSIVO
    estrategia = Column(String(100), nullable=True)
    target = Column(Float, nullable=True)
    explosao = Column(Float, nullable=True)
    resultado = Column(String(10), nullable=True, index=True)  # hit, miss
    sequencia_perdas = Column(Integer, nullable=True)  # Contador de perdas consecutivas
    dobra_atual = Column(Integer, nullable=True)  # Nível do Martingale (1-4)

    # Dados de sessão
    total_rodadas = Column(Integer, nullable=True)
    tempo_sessao_segundos = Column(Integer, nullable=True)

    # Alertas
    stop_loss_atingido = Column(String(1), nullable=True, default="N")  # S ou N
    meta_atingida = Column(String(1), nullable=True, default="N")  # S ou N

    # Metadados
    versao_bot = Column(String(20), nullable=True)
    sistema_operacional = Column(String(50), nullable=True)
    ip_cliente = Column(String(45), nullable=True)  # Suporta IPv6

    def __repr__(self):
        """Representação string do objeto."""
        return f"<LogBot(tipo='{self.tipo}', lucro={self.lucro}, modo='{self.modo_risco}')>"

    def to_dict(self) -> dict:
        """
        Converte o modelo para dicionário.

        Returns:
            dict: Representação em dicionário do modelo
        """
        ts = cast(datetime, self.timestamp) if self.timestamp is not None else None

        return {
            "id": self.id,
            "sessao_id": self.sessao_id,
            "hwid": self.hwid,
            "timestamp": ts.isoformat() if ts else None,
            "tipo": self.tipo,
            "dados": self.dados,
            "lucro": self.lucro,
            # Novos campos
            "licenca_id": self.licenca_id,
            "saldo": self.saldo,
            "valor_aposta": self.valor_aposta,
            "banca_inicial": self.banca_inicial,
            "banca_final": self.banca_final,
            "modo_risco": self.modo_risco,
            "estrategia": self.estrategia,
            "target": self.target,
            "explosao": self.explosao,
            "resultado": self.resultado,
            "sequencia_perdas": self.sequencia_perdas,
            "dobra_atual": self.dobra_atual,
            "total_rodadas": self.total_rodadas,
            "tempo_sessao_segundos": self.tempo_sessao_segundos,
            "stop_loss_atingido": self.stop_loss_atingido,
            "meta_atingida": self.meta_atingida,
            "versao_bot": self.versao_bot,
            "sistema_operacional": self.sistema_operacional,
            "ip_cliente": self.ip_cliente,
        }
