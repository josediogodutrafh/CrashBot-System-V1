"""
Modelo: VersaoBot
Tabela que armazena versões do bot para auto-update.
"""

from datetime import datetime

from typing import cast

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func


class VersaoBot(Base):
    """
    Modelo da tabela 'versao_bot'.
    Armazena informações das versões do bot.
    """

    __tablename__ = "versao_bot"

    id = Column(Integer, primary_key=True, index=True)
    versao = Column(String(20), nullable=False, unique=True)  # Ex: "2.1.0"
    download_url = Column(Text, nullable=False)  # URL do arquivo .zip ou .exe
    changelog = Column(Text, nullable=True)  # Notas da versão
    obrigatoria = Column(Boolean, default=False)  # Se o update é obrigatório
    ativa = Column(Boolean, default=True)  # Se esta versão está disponível

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<VersaoBot(versao='{self.versao}')>"

    def to_dict(self) -> dict:
        """
        Converte o modelo para dicionário.

        Returns:
            dict: Representação em dicionário do modelo
        """
        # Preparação segura: verifica se não é nulo e faz o cast para datetime
        created = (
            cast(datetime, self.created_at) if self.created_at is not None else None
        )

        return {
            "id": self.id,
            "versao": self.versao,
            "download_url": self.download_url,
            "changelog": self.changelog,
            "obrigatoria": self.obrigatoria,
            "ativa": self.ativa,
            # Usa a variável local preparada 'created'
            "created_at": created.isoformat() if created else None,
        }
