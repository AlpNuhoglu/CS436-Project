"""
Authentication Pydantic şemaları.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Register (start) ────────────────────────────────────────────────────────

class RegisterStartRequest(BaseModel):
    """POST /auth/register/start — isim + soyisim + email + password ile kayıt başlatır."""
    first_name: str = Field(..., min_length=2, max_length=64, description="Ad")
    last_name: str = Field(..., min_length=2, max_length=64, description="Soyad")
    email: EmailStr = Field(..., description="@sabanciuniv.edu uzantılı e-posta")
    password: str = Field(..., min_length=8, max_length=128, description="Min 8 karakter")

    @field_validator("first_name", "last_name")
    @classmethod
    def _normalize_name(cls, v: str) -> str:
        v = " ".join(v.strip().split())
        if len(v) < 2:
            raise ValueError("Bu alan en az 2 karakter olmalıdır.")
        return v


class RegisterStartResponse(BaseModel):
    """Kayıt başlatıldı — OTP maile gönderildi."""
    message: str
    expires_at: datetime


class OtpStartResponse(BaseModel):
    """OTP tabanlı akış başlatıldı — kod gönderildi."""
    message: str
    expires_at: datetime


# ── Register (verify) ───────────────────────────────────────────────────────

class RegisterVerifyRequest(BaseModel):
    """POST /auth/register/verify — emaile gelen OTP ile doğrulama."""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


# ── Login ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """POST /auth/login — email veya username + password."""
    identifier: str
    password: str


# ── Password reset ──────────────────────────────────────────────────────────

class PasswordForgotRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Email bind (legacy accounts) ───────────────────────────────────────────

class EmailBindStartRequest(BaseModel):
    email: EmailStr


class EmailBindVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


# ── Token response (login & verify) ─────────────────────────────────────────

class TokenResponse(BaseModel):
    """JWT içeren standart auth yanıtı."""
    access_token: str
    token_type: str = "bearer"
    user: "UserSummary"


class UserSummary(BaseModel):
    """Token sahibi user özet bilgisi."""
    id: str
    first_name: str | None = None
    last_name: str | None = None
    username: str
    email: EmailStr | None = None
    has_email: bool


class MessageResponse(BaseModel):
    message: str


TokenResponse.model_rebuild()
