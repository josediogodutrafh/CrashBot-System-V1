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
    tipo = Column(String(50), nullable=False, index=True)  # bet, win, loss, error, etc
    dados = Column(Text, nullable=True)
    lucro = Column(Float, default=0.0, nullable=False)

    def __repr__(self):
        """Representação string do objeto."""
        return f"<LogBot(tipo='{self.tipo}', lucro={self.lucro})>"

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
        }
