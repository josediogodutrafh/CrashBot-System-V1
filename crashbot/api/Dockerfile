FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias de sistema para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (cache de layers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo da aplicacao
COPY . .

# Tornar script de startup executavel
RUN chmod +x start.sh

# Porta exposta
EXPOSE 8000

# Startup: roda migrations + inicia uvicorn
CMD ["./start.sh"]
