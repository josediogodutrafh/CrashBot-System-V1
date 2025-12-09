"""
Routers - Exporta todos os routers da API
ATUALIZADO: Inclui routers de notificação para clientes (Item 1)
"""

from app.routers.auth import router as auth_router
from app.routers.licencas import router as licencas_router
from app.routers.notify import router as notify_router

# NOVOS - Item 1: Notificações para Clientes
from app.routers.webhook import router as webhook_router
from app.routers.websocket import router as websocket_router

__all__ = [
    "licencas_router",
    "auth_router",
    "websocket_router",
    "webhook_router",  # NOVO
    "notify_router",  # NOVO
]
