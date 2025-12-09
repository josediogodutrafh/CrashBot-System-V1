"""
Services - Lógica de negócio da aplicação.
"""

from app.services.admin_notification_service import admin_notifications
from app.services.promocao_service import (
    obter_preco_plano,
    verificar_elegibilidade_primeira_adesao,
    verificar_elegibilidade_trial,
)

__all__ = [
    "admin_notifications",
    "verificar_elegibilidade_trial",
    "verificar_elegibilidade_primeira_adesao",
    "obter_preco_plano",
]
