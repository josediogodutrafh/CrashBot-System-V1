"""
Modelo: Usuario
Tabela que armazena usuários admin do sistema.
"""

from datetime import datetime
from typing import cast

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func


class Usuario(Base):
    """
    Modelo da tabela 'usuario'.
    Armazena usuários admin que acessam o dashboard.
    """

    __tablename__ = "usuario"

    # Campos principais
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=True)

    # Permissões
    is_admin = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Datas
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_login = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        """Representação string do objeto."""
        return f"<Usuario(email='{self.email}', is_admin={self.is_admin})>"

    def to_dict(self) -> dict:
        """
        Converte o modelo para dicionário.
        IMPORTANTE: Não inclui senha_hash por segurança.

        Returns:
            dict: Representação em dicionário do modelo
        """
        created = (
            cast(datetime, self.created_at) if self.created_at is not None else None
        )
        last_log = (
            cast(datetime, self.last_login) if self.last_login is not None else None
        )

        return {
            "id": self.id,
            "email": self.email,
            "nome": self.nome,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": created.isoformat() if created else None,
            "last_login": last_log.isoformat() if last_log else None,
        }
