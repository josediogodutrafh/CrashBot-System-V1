"""
CrashBot API - FastAPI
Versão 2.0

API moderna para gestão do CrashBot.
"""

from app.routers.auth import router as auth_router
from app.routers.licencas import router as licencas_router
from app.routers.pagamento import router as pagamento_router
from app.routers.versao import router as versao_router
from app.routers.websocket import router as websocket_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

# ============================================================================
# MIDDLEWARES
# ============================================================================

# CORS - Permite acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:8501",  # Streamlit (temporário)
        "https://*.vercel.app",  # Vercel preview/production
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
        "database": "connected",  # TODO: verificar conexão real
        "redis": "connected",  # TODO: adicionar Redis
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
        },
        "features": {
            "websocket": True,
            "real_time": True,
            "authentication": "JWT",
        },
    }


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
    print("🚀 CrashBot API iniciando...")
    print("📚 Documentação: http://localhost:8000/api/docs")
    # TODO: Conectar ao banco
    # TODO: Inicializar Redis
    # TODO: Carregar configurações


@app.on_event("shutdown")
async def shutdown_event():
    """Executado quando a API desliga."""
    print("👋 CrashBot API encerrando...")
    # TODO: Fechar conexões do banco
    # TODO: Fechar conexão Redis


# ============================================================================
# RODAR A API
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload em desenvolvimento
        log_level="info",
    )
