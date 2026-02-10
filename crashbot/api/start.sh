#!/bin/bash
# =============================================================================
# CrashBot API - Startup Script (Render)
# Roda migrations e inicia o servidor
# =============================================================================

set -e

echo "=== CrashBot API Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Running Alembic migrations..."

# Rodar migrations
alembic upgrade head

echo "Migrations OK!"
echo "Starting uvicorn..."

# Iniciar servidor
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --log-level info
