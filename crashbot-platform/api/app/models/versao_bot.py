from datetime import datetime

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func


class VersaoBot(Base):
    __tablename__ = "versao_bot"

    id = Column(Integer, primary_key=True, index=True)
    versao = Column(String(20), nullable=False, unique=True)
    download_url = Column(Text, nullable=False)
    changelog = Column(Text, nullable=True)
    obrigatoria = Column(Boolean, default=False)
    ativa = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "versao": self.versao,
            "download_url": self.download_url,
            "changelog": self.changelog,
            "obrigatoria": self.obrigatoria,
            "ativa": self.ativa,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
