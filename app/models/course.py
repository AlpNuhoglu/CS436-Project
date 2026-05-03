"""
Course ORM model.

Sabancı Üniversitesi'ndeki dersleri temsil eder.
"""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)   # e.g. CS436
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # FENS / FASS / SBS / SL — fakülte kısaltması
    faculty: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # 1–5 arası (1 = çok kolay, 5 = çok zor)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Haftalık yaklaşık iş yükü (saat)
    workload_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("code", name="uq_courses_code"),
        CheckConstraint(
            "difficulty IS NULL OR (difficulty >= 1 AND difficulty <= 5)",
            name="ck_courses_difficulty",
        ),
        CheckConstraint(
            "workload_hours IS NULL OR (workload_hours >= 0 AND workload_hours <= 60)",
            name="ck_courses_workload_hours",
        ),
    )

    # Relationships
    professor_courses: Mapped[list["ProfessorCourse"]] = relationship(
        "ProfessorCourse", back_populates="course", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="course"
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} code={self.code!r} name={self.name!r}>"
