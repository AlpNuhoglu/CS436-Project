"""
Cognito JWT doğrulama motoru.

Cognito'nun public JWKS endpoint'inden anahtarları çeker ve
gelen Bearer token'ı doğrular.

DEBUG=true iken Cognito bağlantısına gerek yoktur — sahte bir kullanıcı
döndürülür. Production'da bu flag kapalı olmalıdır.
"""
import time
from functools import lru_cache
from typing import Any

import httpx
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.config import get_settings

settings = get_settings()


# ── JWKS (JSON Web Key Set) ───────────────────────────────────────────────────

def _jwks_url() -> str:
    return (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
        f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Cognito'nun public anahtarlarını çek ve önbellekle."""
    response = httpx.get(_jwks_url(), timeout=5)
    response.raise_for_status()
    return response.json()


def _find_public_key(token: str) -> Any:
    """Token header'ındaki kid'e göre doğru public key'i bul."""
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    jwks = _get_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwk.construct(key_data)
    return None


# ── Token doğrulama ───────────────────────────────────────────────────────────

class CognitoTokenError(Exception):
    """Token geçersiz veya süresi dolmuş."""
    pass


def verify_token(token: str) -> dict:
    """
    Cognito JWT token'ını doğrula ve claim'leri döndür.

    Raises:
        CognitoTokenError: Token geçersizse.
    """
    # 1. Public key'i bul
    public_key = _find_public_key(token)
    if public_key is None:
        raise CognitoTokenError("Token imzası için uygun anahtar bulunamadı.")

    # 2. İmzayı doğrula ve claim'leri çöz
    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.cognito_app_client_id,
            options={"verify_exp": True},
        )
    except JWTError as exc:
        raise CognitoTokenError(f"Token doğrulama hatası: {exc}") from exc

    # 3. Token tipini kontrol et (access token olmalı)
    if claims.get("token_use") not in ("access", "id"):
        raise CognitoTokenError("Geçersiz token tipi.")

    # 4. İssuer'ı kontrol et
    expected_iss = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
        f"/{settings.cognito_user_pool_id}"
    )
    if claims.get("iss") != expected_iss:
        raise CognitoTokenError("Token issuer geçersiz.")

    return claims


# ── Geliştirme modu sahte token ───────────────────────────────────────────────

def get_debug_user() -> dict:
    """
    DEBUG=true modunda kullanılacak sahte kullanıcı claim'leri.
    Cognito bağlantısı gerektirmez.
    """
    return {
        "sub": "debug-user-00000000-0000-0000-0000-000000000001",
        "email": "testuser@sabanciuniv.edu",
        "cognito:username": "testuser",
        "token_use": "access",
        "iss": "debug",
        "exp": int(time.time()) + 3600,
    }
