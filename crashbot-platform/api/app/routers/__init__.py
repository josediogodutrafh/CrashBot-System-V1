"""
Routers - Exporta todos os routers da API
"""

from app.routers.auth import router as auth_router
from app.routers.licencas import router as licencas_router
from app.routers.websocket import router as websocket_router

__all__ = ["licencas_router", "auth_router", "websocket_router"]
