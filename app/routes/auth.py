"""
Authentication endpoints — local register/login (OTP destekli).

POST /auth/register/start   → email + username + password al, OTP gönder
POST /auth/register/verify  → OTP'yi doğrula, User oluştur, token dön
POST /auth/login            → email veya username + password ile giriş, token dön
POST /auth/password/forgot  → kayıtlı e-postaya şifre sıfırlama OTP'si gönder
POST /auth/password/reset   → OTP ile şifreyi sıfırla
POST /auth/email/bind/start → legacy hesaba private email bağlama OTP'si gönder
POST /auth/email/bind/verify→ email bağlamayı doğrula
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.email_otp import (
    generate_otp,
    hash_otp,
    send_otp_email,
    verify_otp,
)
from app.auth.local import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.auth.dependencies import CurrentUser, get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.pending_email_bind import PendingEmailBind
from app.models.pending_registration import PendingRegistration
from app.models.password_reset_request import PasswordResetRequest as PasswordResetRequestModel
from app.models.user import User
from app.schemas.auth import (
    EmailBindStartRequest,
    EmailBindVerifyRequest,
    LoginRequest,
    MessageResponse,
    OtpStartResponse,
    PasswordForgotRequest,
    PasswordResetRequest,
    RegisterStartRequest,
    RegisterStartResponse,
    RegisterVerifyRequest,
    TokenResponse,
    UserSummary,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("auth.routes")

settings = get_settings()


# ── Yardımcılar ─────────────────────────────────────────────────────────────

def _check_email_domain(email: str) -> str:
    """Email'i normalize et ve domain kontrolü yap."""
    email_lc = email.strip().lower()
    expected = settings.allowed_email_domain.lower().lstrip("@")
    if not email_lc.endswith(f"@{expected}"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sadece @{expected} uzantılı e-posta adresleriyle kayıt olunabilir.",
        )
    return email_lc


def _purge_expired_pending(db: Session) -> None:
    """Süresi dolmuş pending kayıtlarını temizle (best-effort)."""
    now = datetime.now(timezone.utc)
    db.query(PendingRegistration).filter(PendingRegistration.expires_at < now).delete()
    db.query(PasswordResetRequestModel).filter(PasswordResetRequestModel.expires_at < now).delete()
    db.query(PendingEmailBind).filter(PendingEmailBind.expires_at < now).delete()
    db.commit()


def _otp_response(message: str) -> OtpStartResponse:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_ttl_minutes)
    return OtpStartResponse(message=message, expires_at=expires_at)


def _user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        email=user.email,
        has_email=bool(user.email),
    )


def _start_otp_flow(model, db: Session, lookup: dict, create_kwargs: dict) -> datetime:
    otp = generate_otp()
    otp_hash_value = hash_otp(otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_ttl_minutes)
    record = db.query(model).filter_by(**lookup).first()

    if record is None:
        record = model(**create_kwargs, otp_hash=otp_hash_value, expires_at=expires_at, attempts=0)
        db.add(record)
    else:
        record.otp_hash = otp_hash_value
        record.expires_at = expires_at
        record.attempts = 0
        for key, value in create_kwargs.items():
            setattr(record, key, value)

    db.commit()
    return expires_at, otp


# ── POST /auth/register/start ───────────────────────────────────────────────

@router.post(
    "/register/start",
    response_model=RegisterStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Kayıt: e-posta doğrulama OTP'si gönder",
)
def register_start(body: RegisterStartRequest, db: Session = Depends(get_db)):
    """
    Kullanıcının kayıt akışını başlatır:
    1. Email @sabanciuniv.edu mu? Kontrol et.
    2. Username ya da email zaten kullanılıyor mu?
    3. OTP üret, hash'le, pending_registrations'a yaz.
    4. OTP'yi maile gönder. (SMTP yoksa konsola yazılır.)
    """
    email = _check_email_domain(body.email)
    first_name = body.first_name.strip()
    last_name = body.last_name.strip()
    username = email.split("@")[0]

    existing_email_user = db.query(User).filter(User.email == email).first()
    if existing_email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresiyle zaten bir hesap var. Giriş yapın veya şifrenizi sıfırlayın.",
        )

    _purge_expired_pending(db)

    password_hash_value = hash_password(body.password)
    expires_at, otp = _start_otp_flow(
        PendingRegistration,
        db,
        lookup={"email": email},
        create_kwargs={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "password_hash": password_hash_value,
        },
    )

    try:
        send_otp_email(email, otp)
    except RuntimeError as exc:
        # Mail gönderilemediyse pending kaydı yine duruyor — kullanıcı tekrar deneyebilir.
        logger.error("OTP gönderilemedi (%s): %s", email, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="E-posta gönderilemedi, lütfen tekrar deneyin.",
        ) from exc

    return RegisterStartResponse(
        message="Doğrulama kodu e-posta adresinize gönderildi.",
        expires_at=expires_at,
    )


# ── POST /auth/register/verify ──────────────────────────────────────────────

@router.post(
    "/register/verify",
    response_model=TokenResponse,
    summary="Kayıt: OTP doğrula, hesap aç ve token dön",
)
def register_verify(body: RegisterVerifyRequest, db: Session = Depends(get_db)):
    """
    OTP'yi doğrular. Başarılıysa:
      - users tablosuna ad + soyad + username + private email + password_hash ile kayıt açar
      - pending_registrations satırını siler
      - JWT döner (otomatik giriş)
    """
    email = _check_email_domain(body.email)
    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bekleyen bir kayıt bulunamadı. Lütfen yeniden başlatın.",
        )

    now = datetime.now(timezone.utc)
    if pending.expires_at < now:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Doğrulama kodu süresi doldu. Lütfen yeniden başlatın.",
        )

    if pending.attempts >= settings.otp_max_attempts:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla yanlış deneme. Lütfen yeniden başlatın.",
        )

    if not verify_otp(body.otp, pending.otp_hash):
        pending.attempts += 1
        db.commit()
        remaining = max(0, settings.otp_max_attempts - pending.attempts)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kod hatalı. Kalan deneme: {remaining}.",
        )

    # OTP doğru → User oluştur, pending'i sil.
    # Username yarışını önlemek için son bir kontrol:
    if db.query(User).filter(User.username == pending.username).first():
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu kullanıcı adı bu sırada başka biri tarafından alındı.",
        )

    if not pending.first_name or not pending.last_name:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bekleyen kayıt güncel değil. Lütfen kayıt sürecini yeniden başlatın.",
        )

    user = User(
        first_name=pending.first_name,
        last_name=pending.last_name,
        username=pending.username,
        email=pending.email,
        password_hash=pending.password_hash,
        is_active=True,
    )
    db.add(user)
    db.delete(pending)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(
        access_token=token,
        user=_user_summary(user),
    )


# ── POST /auth/login ────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Kullanıcı adı + şifre ile giriş",
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    identifier = body.identifier.strip()
    if "@" in identifier:
        user = db.query(User).filter(User.email == identifier.lower()).first()
    else:
        user = (
            db.query(User)
            .filter(or_(User.username == identifier, User.email == identifier.lower()))
            .first()
        )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta/kullanıcı adı veya şifre hatalı.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesap devre dışı.",
        )

    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(
        access_token=token,
        user=_user_summary(user),
    )


# ── POST /auth/password/forgot ─────────────────────────────────────────────

@router.post(
    "/password/forgot",
    response_model=OtpStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Şifre sıfırlama kodu gönder",
)
def password_forgot(body: PasswordForgotRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    _purge_expired_pending(db)
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()

    if user is not None:
        expires_at, otp = _start_otp_flow(
            PasswordResetRequestModel,
            db,
            lookup={"user_id": user.id},
            create_kwargs={"user_id": user.id},
        )
        try:
            send_otp_email(email, otp, purpose="reset")
        except RuntimeError as exc:
            logger.error("Password reset OTP gönderilemedi (%s): %s", email, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="E-posta gönderilemedi, lütfen tekrar deneyin.",
            ) from exc
        return OtpStartResponse(
            message="Eğer bu e-posta ile bir hesap varsa, şifre sıfırlama kodu gönderildi.",
            expires_at=expires_at,
        )

    return _otp_response("Eğer bu e-posta ile bir hesap varsa, şifre sıfırlama kodu gönderildi.")


@router.post(
    "/password/reset",
    response_model=MessageResponse,
    summary="OTP ile şifreyi sıfırla",
)
def password_reset(body: PasswordResetRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu e-posta için aktif bir hesap bulunamadı.",
        )

    pending = db.query(PasswordResetRequestModel).filter(
        PasswordResetRequestModel.user_id == user.id
    ).first()
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bekleyen bir şifre sıfırlama isteği bulunamadı.",
        )

    now = datetime.now(timezone.utc)
    if pending.expires_at < now:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Doğrulama kodu süresi doldu. Lütfen yeniden isteyin.",
        )

    if pending.attempts >= settings.otp_max_attempts:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla yanlış deneme. Lütfen yeni kod isteyin.",
        )

    if not verify_otp(body.otp, pending.otp_hash):
        pending.attempts += 1
        db.commit()
        remaining = max(0, settings.otp_max_attempts - pending.attempts)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kod hatalı. Kalan deneme: {remaining}.",
        )

    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yeni şifre mevcut şifrenizle aynı olamaz.",
        )

    user.password_hash = hash_password(body.new_password)
    db.delete(pending)
    db.commit()
    return MessageResponse(message="Şifreniz güncellendi. Artık yeni şifrenizle giriş yapabilirsiniz.")


# ── POST /auth/email/bind/* ────────────────────────────────────────────────

@router.post(
    "/email/bind/start",
    response_model=OtpStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Legacy hesaba e-posta bağlama kodu gönder",
)
def email_bind_start(
    body: EmailBindStartRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    if user.email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu hesapta zaten kayıtlı bir e-posta var.",
        )

    email = _check_email_domain(body.email)
    _purge_expired_pending(db)

    existing_email_user = db.query(User).filter(User.email == email).first()
    if existing_email_user and existing_email_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi başka bir hesapta kullanılıyor.",
        )

    pending_with_email = db.query(PendingEmailBind).filter(PendingEmailBind.email == email).first()
    if pending_with_email and pending_with_email.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi şu anda doğrulama bekleyen başka bir hesapta kullanılıyor.",
        )

    expires_at, otp = _start_otp_flow(
        PendingEmailBind,
        db,
        lookup={"user_id": current_user.id},
        create_kwargs={"user_id": current_user.id, "email": email},
    )
    try:
        send_otp_email(email, otp)
    except RuntimeError as exc:
        logger.error("Email bind OTP gönderilemedi (%s): %s", email, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="E-posta gönderilemedi, lütfen tekrar deneyin.",
        ) from exc

    return OtpStartResponse(
        message="Doğrulama kodu e-posta adresinize gönderildi.",
        expires_at=expires_at,
    )


@router.post(
    "/email/bind/verify",
    response_model=MessageResponse,
    summary="Legacy hesaba e-posta bağlamayı doğrula",
)
def email_bind_verify(
    body: EmailBindVerifyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    if user.email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu hesapta zaten kayıtlı bir e-posta var.",
        )

    email = _check_email_domain(body.email)
    pending = db.query(PendingEmailBind).filter(PendingEmailBind.user_id == current_user.id).first()
    if not pending or pending.email != email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bekleyen bir e-posta bağlama isteği bulunamadı.",
        )

    now = datetime.now(timezone.utc)
    if pending.expires_at < now:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Doğrulama kodu süresi doldu. Lütfen yeniden isteyin.",
        )

    if pending.attempts >= settings.otp_max_attempts:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla yanlış deneme. Lütfen yeni kod isteyin.",
        )

    if not verify_otp(body.otp, pending.otp_hash):
        pending.attempts += 1
        db.commit()
        remaining = max(0, settings.otp_max_attempts - pending.attempts)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kod hatalı. Kalan deneme: {remaining}.",
        )

    existing_email_user = db.query(User).filter(User.email == email).first()
    if existing_email_user and existing_email_user.id != current_user.id:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi bu sırada başka bir hesapta kullanıldı.",
        )

    user.email = email
    db.delete(pending)
    db.commit()
    return MessageResponse(message="E-posta adresiniz hesabınıza bağlandı.")
