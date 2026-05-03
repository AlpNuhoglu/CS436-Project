"""
Review ORM model.

Bir kullanıcının bir hoca ve/veya ders için yazdığı değerlendirmeyi temsil eder.
En az biri (professor_id veya course_id) dolu olmalıdır — bu kural
uygulama katmanında kontrol edilir.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    professor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("professors.id", ondelete="SET NULL"), nullable=True
    )
    course_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    # Hangi dönemde alındığı — örn. "Spring 2025". Opsiyonel; kullanıcı
    # belirtmek istemezse NULL kalır. professor_courses tablosundaki
    # değerlerle aynı formatta tutulur.
    semester: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 1–5 arası puan
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    # Öğrencinin hissettiği zorluk (1–5) ve haftalık saat (0–60).
    # Ders için verilen yorumlarda anlamlıdır; hoca-only yorumlarda NULL kalabilir.
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workload_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating"),
        CheckConstraint(
            "difficulty IS NULL OR (difficulty >= 1 AND difficulty <= 5)",
            name="ck_reviews_difficulty",
        ),
        CheckConstraint(
            "workload_hours IS NULL OR (workload_hours >= 0 AND workload_hours <= 60)",
            name="ck_reviews_workload_hours",
        ),
        # Aynı kullanıcı aynı hoca+ders+dönem üçlüsü için yalnızca bir yorum yazabilir.
        # NOT: PostgreSQL'de NULL'lar UNIQUE'te ayrı sayılır, dolayısıyla semester=NULL
        # yorumlar tek kullanıcıda birden fazla kez girilebilir — uygulama tarafında
        # ek kontrol yok (opsiyonel olduğu için kabul edilebilir).
        UniqueConstraint(
            "user_id", "professor_id", "course_id", "semester",
            name="uq_review_user_prof_course_semester",
        ),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reviews")
    professor: Mapped["Professor | None"] = relationship(
        "Professor", back_populates="reviews"
    )
    course: Mapped["Course | None"] = relationship(
        "Course", back_populates="reviews"
    )
    upvotes: Mapped[list["Upvote"]] = relationship(
        "Upvote", back_populates="review", cascade="all, delete-orphan"
    )
    downvotes: Mapped[list["Downvote"]] = relationship(
        "Downvote", back_populates="review", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} rating={self.rating} user_id={self.user_id}>"
