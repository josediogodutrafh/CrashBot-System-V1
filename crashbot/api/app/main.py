"""
CrashBot API - FastAPI
Versão 2.0

API moderna para gestão do CrashBot.
ATUALIZADO: Inclui router de agendamento Google Calendar (Item 5)
"""

from app.database import get_db
from app.routers.auth import router as auth_router
from app.routers.calendar import router as calendar_router
from app.routers.licencas import router as licencas_router
from app.routers.licencas import validar_licenca
from app.routers.notify import router as notify_router
from app.routers.pagamento import router as pagamento_router
from app.routers.telemetria import router as telemetria_router
from app.routers.versao import router as versao_router

# NOVOS ROUTERS - Item 1: Notificações para Clientes
from app.routers.webhook import router as webhook_router
from app.routers.websocket import router as websocket_router
from app.schemas.licenca import ValidarLicencaRequest
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ============================================================================
# RATE LIMITING
# ============================================================================
limiter = Limiter(key_func=get_remote_address)

# ============================================================================
# CONFIGURAÇÃO DA APP
# ============================================================================

app = FastAPI(
    title="CrashBot API",
    description="API moderna para gestão, vendas e telemetria do CrashBot",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Adiciona rate limiter à app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# ============================================================================
# MIDDLEWARES
# ============================================================================

# CORS - Permite acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:8501",  # Streamlit (temporário)
        "https://crashbot-loja.vercel.app",  # Vercel production
        "https://crashbot-loja-git-main-crash-bot.vercel.app",  # Vercel preview
        "https://tucunarebot.com.br",  # Domínio principal
        "https://www.tucunarebot.com.br",  # Domínio com www
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(licencas_router)
app.include_router(auth_router)
app.include_router(websocket_router)
app.include_router(pagamento_router)
app.include_router(versao_router)
app.include_router(telemetria_router)
app.include_router(calendar_router)  # NOVO - Item 5: Agendamentos

# NOVOS ROUTERS - Item 1: Notificações para Clientes
app.include_router(webhook_router)
app.include_router(notify_router)

# ============================================================================
# ROTAS BÁSICAS
# ============================================================================


@app.get("/")
async def root():
    """Rota raiz - Informações da API."""
    return {
        "name": "CrashBot API",
        "version": "2.0.0",
        "status": "online",
        "docs": "/api/docs",
    }


@app.get("/health")
async def health_check():
    """Health check - Verifica se a API está funcionando."""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
    }


@app.get("/api/v1/status")
async def api_status():
    """Status detalhado da API."""
    return {
        "api_version": "2.0.0",
        "endpoints": {
            "auth": "/api/v1/auth",
            "licenses": "/api/v1/licencas",
            "telemetry": "/api/v1/telemetria",
            "payments": "/api/v1/pagamentos",
            "telegram": "/api/v1/telegram",
            "notify": "/api/v1/notify",
            "calendar": "/api/v1/calendar",  # NOVO
        },
        "features": {
            "websocket": True,
            "real_time": True,
            "authentication": "JWT",
            "client_notifications": True,
            "google_calendar": True,  # NOVO
        },
    }


# ============================================================================
# ROTAS DE COMPATIBILIDADE (para bots antigos)
# ============================================================================


@app.post("/telemetria/log")
async def telemetria_compat(request: Request):
    """Redireciona para nova rota de telemetria."""
    return RedirectResponse(url="/api/v1/telemetria/log", status_code=307)


@app.post("/validar")
async def validar_compat(
    request: Request, payload: ValidarLicencaRequest, db=Depends(get_db)
):
    """Rota de compatibilidade - chama diretamente a função de validação."""
    return await validar_licenca(request=request, payload=payload, db=db)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handler para 404 - Rota não encontrada."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": "Rota não encontrada",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handler para 500 - Erro interno."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Erro interno do servidor",
        },
    )


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Executado quando a API inicia."""
    print(" CrashBot API iniciando...")
    print(" Documentação: http://localhost:8000/api/docs")
    print(" Telegram Webhook: /api/v1/telegram/webhook")
    print(" Client Notifications: /api/v1/notify")
    print(" Google Calendar: /api/v1/calendar")


@app.on_event("shutdown")
async def shutdown_event():
    """Executado quando a API desliga."""
    print(" CrashBot API encerrando...")


# ============================================================================
# RODAR A API
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
