"""
Modelo: Licenca
Tabela que armazena as licenças dos clientes.
"""

from datetime import datetime, timezone
from typing import Optional, cast

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func


class Licenca(Base):
    """
    Modelo da tabela 'licenca'.
    Armazena informações das licenças vendidas.
    """

    __tablename__ = "licenca"

    # Campos principais
    id = Column(Integer, primary_key=True, index=True)
    chave = Column(String(50), unique=True, nullable=False, index=True)
    hwid = Column(String(100), nullable=True, index=True)
    ativa = Column(Boolean, default=True, nullable=False)

    # Datas
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    data_expiracao = Column(DateTime(timezone=True), nullable=True)

    # Informações do cliente
    cliente_nome = Column(String(255), nullable=True)
    email_cliente = Column(String(255), nullable=True, index=True)
    whatsapp = Column(String(20), nullable=True)
    telegram_chat_id = Column(String(100), nullable=True)

    # Informações do plano
    plano_tipo = Column(String(50), nullable=True)  # experimental, semanal, mensal
    payment_id = Column(String(100), nullable=True)

    def __repr__(self):
        """Representação string do objeto."""
        return f"<Licenca(chave='{self.chave}', ativa={self.ativa})>"

    @property
    def esta_expirada(self) -> bool:
        """
        Verifica se a licença está expirada.

        Returns:
            bool: True se expirada, False caso contrário
        """
        if self.data_expiracao is None:
            return False
        now = datetime.now(timezone.utc)
        # Garantir que data_expiracao tenha timezone
        exp = cast(datetime, self.data_expiracao)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp

    @property
    def dias_restantes(self) -> Optional[int]:
        """
        Calcula quantos dias faltam para a licença expirar.

        Returns:
            int | None: Número de dias restantes ou None se não tiver data_expiracao
        """
        if self.data_expiracao is None:
            return None
        now = datetime.now(timezone.utc)
        # Garantir que data_expiracao tenha timezone
        exp = cast(datetime, self.data_expiracao)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        delta = exp - now
        return max(0, delta.days)

    def to_dict(self) -> dict:
        """
        Converte o modelo para dicionário.

        Returns:
            dict: Representação em dicionário do modelo
        """
        data_exp = (
            cast(datetime, self.data_expiracao)
            if self.data_expiracao is not None
            else None
        )
        created = (
            cast(datetime, self.created_at) if self.created_at is not None else None
        )

        return {
            "id": self.id,
            "chave": self.chave,
            "hwid": self.hwid,
            "ativa": self.ativa,
            "created_at": created.isoformat() if created else None,
            "data_expiracao": data_exp.isoformat() if data_exp else None,
            "cliente_nome": self.cliente_nome,
            "email_cliente": self.email_cliente,
            "whatsapp": self.whatsapp,
            "telegram_chat_id": self.telegram_chat_id,
            "plano_tipo": self.plano_tipo,
            "payment_id": self.payment_id,
            "esta_expirada": self.esta_expirada,
            "dias_restantes": self.dias_restantes,
        }
