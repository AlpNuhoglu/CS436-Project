"""
Professor ORM model.

Sabancı Üniversitesi'ndeki öğretim üyelerini temsil eder.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Professor(Base):
    __tablename__ = "professors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # FENS / FASS / SBS / SL — fakülte kısaltması
    faculty: Mapped[str | None] = mapped_column(String(8), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    professor_courses: Mapped[list["ProfessorCourse"]] = relationship(
        "ProfessorCourse", back_populates="professor", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="professor"
    )

    def __repr__(self) -> str:
        return f"<Professor id={self.id} name={self.name!r}>"
