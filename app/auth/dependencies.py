"""
FastAPI auth dependency'leri.

`get_current_user` → korumalı endpoint'lerde Depends() ile kullanılır.

Local JWT (HS256) kullanır — Cognito devre dışı. Token Bearer header'ından
gelir, payload'daki `sub` (UUID) ile users tablosundan kullanıcı çekilir.
"""
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.local import TokenError, decode_access_token
from app.database import get_db
from app.models.user import User

# Authorization: Bearer <token> header'ını otomatik çeker
_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """Doğrulanmış kullanıcının özet bilgisi (email içermez)."""
    id: uuid.UUID
    username: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Korumalı endpoint'ler için FastAPI dependency.

    1. Bearer token'ı doğrula.
    2. Payload'daki `sub` UUID'sine göre kullanıcıyı DB'den çek.
    3. Kullanıcı yoksa veya token geçersizse 401.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header eksik.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token geçersiz: sub yok.",
        )

    try:
        user_uuid = uuid.UUID(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token geçersiz: sub formatı.",
        ) from exc

    user = db.query(User).filter(User.id == user_uuid, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı veya devre dışı.",
        )

    return CurrentUser(id=user.id, username=user.username)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    """
    İsteğe bağlı auth dependency.

    Token yoksa veya geçersizse `None` döner; varsa `CurrentUser` döner.
    GET /reviews gibi anonim erişime açık ama owner'a özel veri (örn.
    `is_owner` flag'i) döndürmek isteyen endpoint'ler için kullanılır.
    """
    if credentials is None:
        return None
    try:
        claims = decode_access_token(credentials.credentials)
    except TokenError:
        return None

    sub = claims.get("sub")
    if not sub:
        return None
    try:
        user_uuid = uuid.UUID(sub)
    except (TypeError, ValueError):
        return None

    user = db.query(User).filter(User.id == user_uuid, User.is_active.is_(True)).first()
    if user is None:
        return None
    return CurrentUser(id=user.id, username=user.username)
