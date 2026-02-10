"""
Services - Lógica de negócio da aplicação.
ATUALIZADO: Inclui serviço de verificação WhatsApp
"""
# Admin Notifications (Item 2 - já implementado)
from app.services.admin_notification_service import admin_notifications

# Client Notifications (Item 1)
from app.services.client_notification_service import (
    AlertType,
    notify_hit,
    notify_meta_atingida,
    notify_miss,
    notify_stop_loss,
    send_client_notification,
)

# Promoções e elegibilidade
from app.services.promocao_service import (
    obter_preco_plano,
    verificar_elegibilidade_trial,
)

# WhatsApp Verification (NOVO)
from app.services.whatsapp_verification_service import whatsapp_verification

__all__ = [
    # Promoções
    "verificar_elegibilidade_trial",
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
    # WhatsApp Verification
    "whatsapp_verification",
]
