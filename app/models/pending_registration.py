"""
PendingRegistration ORM modeli.

Email + OTP doğrulaması için **geçici** kayıttır. Kullanıcı OTP'yi onaylayınca
bu satır silinir ve `users` tablosunda kalıcı kayıt oluşturulur. Buradaki
alanlar sadece doğrulama tamamlanana kadar geçici olarak bekletilir.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Email plaintext olarak doğrulama tamamlanana kadar burada tutulur.
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Yeni hesap açılırken gerçek kimlik bilgisi de toplanır; yorumlarda yine
    # public olarak gösterilmez.
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Username + password hash burada hazır beklemekte; verify olduğunda
    # User satırı bu alanlardan oluşturulur.
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # OTP'nin bcrypt hash'i (asla plaintext OTP saklanmaz)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PendingRegistration email={self.email!r} expires_at={self.expires_at}>"
