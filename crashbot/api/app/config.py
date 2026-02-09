"""
Configurações da API
Usa Pydantic Settings para validação e carregamento de .env
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações da aplicação.
    Valores são carregados de variáveis de ambiente ou .env
    """

    # ========================================================================
    # APLICAÇÃO
    # ========================================================================
    APP_NAME: str = "CrashBot API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ========================================================================
    # SEGURANÇA
    # ========================================================================
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"  # Para JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ========================================================================
    # BANCO DE DADOS
    # ========================================================================
    # PostgreSQL no Render (igual ao antigo)
    DATABASE_URL: str = (
        "postgresql://crash_db_user:BQudpCSoH52uCJ1Nn7qDT9bHyxeUllSU@"
        "dpg-d4i9h3re5dus73egah5g-a.oregon-postgres.render.com/crash_db"
    )

    # ========================================================================
    # REDIS (opcional - para cache e sessions)
    # ========================================================================
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_ENABLED: bool = False

    # ========================================================================
    # CORS
    # ========================================================================
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Next.js dev
        "http://localhost:8501",  # Streamlit temporário
        "https://*.vercel.app",  # Vercel
    ]

    # ========================================================================
    # MERCADO PAGO
    # ========================================================================
    MERCADOPAGO_ACCESS_TOKEN: str = ""  # TODO: Adicionar token real
    MERCADOPAGO_PUBLIC_KEY: str = ""

    # ========================================================================
    # EMAIL (Resend ou outro serviço)
    # ========================================================================
    EMAIL_PROVIDER: str = "resend"  # resend | sendgrid | smtp
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "TucunaréBot <contato@tucunarebot.com.br>"

    # ========================================================================
    # TELEGRAM
    # ========================================================================
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    # ========================================================================
    # CONFIGURAÇÃO DO PYDANTIC
    # ========================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.
    Usa cache para evitar recarregar o .env toda vez.
    """
    return Settings()


# Instância global (use esta para importar)
settings = get_settings()
