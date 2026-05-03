"""
User ORM model.

Email artık auth ve şifre sıfırlama için kalıcı olarak tutulur; ancak public
API'lerde veya yorumlarda gösterilmez. Yorumlar yine tamamen anonimdir.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="user", cascade="all, delete-orphan"
    )
    upvotes: Mapped[list["Upvote"]] = relationship(
        "Upvote", back_populates="user", cascade="all, delete-orphan"
    )
    downvotes: Mapped[list["Downvote"]] = relationship(
        "Downvote", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
