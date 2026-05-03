"""
ProfessorCourse ORM model.

Bir hocanın belirli bir dönemde hangi dersi verdiğini gösteren
çoka-çok ilişki tablosu.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProfessorCourse(Base):
    __tablename__ = "professor_courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    professor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("professors.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    # e.g. "Fall 2024", "Spring 2025"
    semester: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "professor_id", "course_id", "semester",
            name="uq_professor_course_semester"
        ),
    )

    # Relationships
    professor: Mapped["Professor"] = relationship(
        "Professor", back_populates="professor_courses"
    )
    course: Mapped["Course"] = relationship(
        "Course", back_populates="professor_courses"
    )

    def __repr__(self) -> str:
        return (
            f"<ProfessorCourse professor_id={self.professor_id} "
            f"course_id={self.course_id} semester={self.semester!r}>"
        )
