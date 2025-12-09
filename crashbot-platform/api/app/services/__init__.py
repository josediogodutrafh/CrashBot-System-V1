"""
Services - Lógica de negócio da aplicação.
ATUALIZADO: Inclui serviço de notificação para clientes
"""

# Admin Notifications (Item 2 - já implementado)
from app.services.admin_notification_service import admin_notifications

# Client Notifications (Item 1 - NOVO)
from app.services.client_notification_service import (
    AlertType,
    notify_hit,
    notify_meta_atingida,
    notify_miss,
    notify_stop_loss,
    send_client_notification,
)
from app.services.promocao_service import (
    obter_preco_plano,
    verificar_elegibilidade_primeira_adesao,
    verificar_elegibilidade_trial,
)

__all__ = [
    # Promoções
    "verificar_elegibilidade_trial",
    "verificar_elegibilidade_primeira_adesao",
    "obter_preco_plano",
    # Admin Notifications
    "admin_notifications",
    # Client Notifications
    "AlertType",
    "send_client_notification",
    "notify_hit",
    "notify_miss",
    "notify_stop_loss",
    "notify_meta_atingida",
]
