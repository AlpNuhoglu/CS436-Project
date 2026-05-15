#!/bin/bash
# ECS Fargate container entrypoint.
# Uvicorn başlamadan önce Alembic migration'larını çalıştırır.
# set -e: herhangi bir komut hata verirse container hemen durur (ECS yeniden başlatır).
set -e

echo "[entrypoint] Alembic migration başlatılıyor..."
alembic upgrade head
echo "[entrypoint] Migration tamamlandı ✓"

echo "[entrypoint] Uvicorn başlatılıyor (workers=2)..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --no-access-log
