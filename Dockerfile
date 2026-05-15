# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Sistem bağımlılıklarını kur (psycopg2 için libpq gerekli)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Sadece çalışma zamanı için gereken libpq + curl (ECS health check için)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Builder stage'den kurulu paketleri kopyala
COPY --from=builder /install /usr/local

# Uygulama kodunu kopyala
COPY . .

# Güvenlik: root olmayan kullanıcı
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Prodüksiyon: alembic migrate → uvicorn
# Lokal geliştirme için docker-compose.yml'de command: override kullanılır
ENTRYPOINT ["./start.sh"]
