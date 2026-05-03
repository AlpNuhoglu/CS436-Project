"""
Email OTP yardımcıları.

- 6 haneli OTP üretir.
- OTP'yi bcrypt ile hash'leyip karşılaştırır (plaintext OTP DB'de tutulmaz).
- SMTP_HOST set'liyse mail gönderir; değilse konsola yazdırır (dev fallback).
"""
import logging
import secrets
import smtplib
from email.message import EmailMessage

from passlib.context import CryptContext

from app.config import get_settings

logger = logging.getLogger("auth.otp")

settings = get_settings()

# OTP'leri bcrypt ile hashleyelim — passlib bcrypt ile uzun dize sorunu yaratabilir
# fakat 6 haneli OTP için sorunsuz.
_otp_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── OTP üret / doğrula ──────────────────────────────────────────────────────

def generate_otp() -> str:
    """6 haneli sıfırla padding'lenmiş OTP üret."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return _otp_ctx.hash(otp)


def verify_otp(otp: str, otp_hash: str) -> bool:
    try:
        return _otp_ctx.verify(otp, otp_hash)
    except ValueError:
        return False


# ── Email gönder ────────────────────────────────────────────────────────────

_REGISTER_SUBJECT = "Ders Forumu — E-posta Doğrulama Kodu"
_REGISTER_TEMPLATE = """\
Merhaba,

Ders Forumu'na kayıt olmak için aşağıdaki 6 haneli doğrulama kodunu giriniz:

    {otp}

Bu kod {ttl} dakika içinde geçerliliğini yitirir. Eğer bu isteği sen
yapmadıysan bu maili görmezden gelebilirsin.

— Ders Forumu (Sabancı Üniversitesi)
"""

_RESET_SUBJECT = "Ders Forumu — Şifre Sıfırlama Kodu"
_RESET_TEMPLATE = """\
Merhaba,

Ders Forumu hesabının şifresini sıfırlamak için aşağıdaki 6 haneli kodu
giriniz:

    {otp}

Bu kod {ttl} dakika içinde geçerliliğini yitirir. Eğer bu isteği sen
yapmadıysan hesabın güvende olup bu maili görmezden gelebilirsin.

— Ders Forumu (Sabancı Üniversitesi)
"""


def send_otp_email(to_email: str, otp: str, purpose: str = "register") -> None:
    """
    OTP'yi mail olarak gönder. SMTP yapılandırması yoksa yalnızca log'a yaz.

    purpose: "register" | "reset"
    Hatalar HTTPException olarak değil, RuntimeError olarak fırlatılır;
    çağıran route bunu çevirebilir.
    """
    if purpose == "reset":
        subject = _RESET_SUBJECT
        body = _RESET_TEMPLATE.format(otp=otp, ttl=settings.otp_ttl_minutes)
    else:
        subject = _REGISTER_SUBJECT
        body = _REGISTER_TEMPLATE.format(otp=otp, ttl=settings.otp_ttl_minutes)

    if not settings.smtp_host:
        logger.warning(
            "SMTP yapılandırılmamış — OTP konsola yazdırılıyor.\n"
            "  to=%s\n  otp=%s",
            to_email,
            otp,
        )
        print(f"\n[OTP] {to_email} → {otp}\n", flush=True)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("OTP gönderildi → %s", to_email)
    except Exception as exc:  # noqa: BLE001
        logger.exception("OTP maili gönderilemedi → %s", to_email)
        raise RuntimeError(f"E-posta gönderilemedi: {exc}") from exc
