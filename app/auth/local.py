"""
Local kimlik doğrulama: password hashing + JWT issue/verify.

Cognito yerine projemizin kendi JWT'sini kullanıyoruz. Token'lar HS256 ile
JWT_SECRET üzerinden imzalanır. Payload'da yalnızca kullanıcının UUID'si
(`sub`) ve username (`username`) tutulur — başka PII yoktur.
"""
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()


_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password hashing ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd_ctx.verify(password, password_hash)
    except ValueError:
        return False


# ── JWT ─────────────────────────────────────────────────────────────────────

class TokenError(Exception):
    pass


def create_access_token(*, user_id: uuid.UUID, username: str) -> str:
    """Kullanıcı için imzalı bir access token üret."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Token'ı doğrula ve payload'ı döndür."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenError(f"Token doğrulama hatası: {exc}") from exc
