"""
Health check endpoint.

Uygulamanın ayakta olup olmadığını ve veritabanı bağlantısının çalışıp
çalışmadığını doğrulamak için kullanılır.

Dönen yanıt:
  - status: "ok" | "degraded"
  - db: "ok" | "unreachable"
  - version: uygulama versiyonu
  - timestamp: sunucu saati (ISO 8601)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", summary="Uygulama ve veritabanı sağlık kontrolü")
def health_check(db: Session = Depends(get_db)):
    """
    Servisin ayakta olduğunu ve DB bağlantısının sağlıklı olduğunu doğrular.

    - **status**: Genel durum. DB erişilemezse `degraded` döner.
    - **db**: Veritabanı bağlantı durumu.
    - **version**: Uygulama versiyonu.
    - **timestamp**: Yanıtın üretildiği UTC zamanı.
    """
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    overall = "ok" if db_status == "ok" else "degraded"

    return {
        "status": overall,
        "db": db_status,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
