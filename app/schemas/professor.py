"""
Professor Pydantic şemaları.

ProfessorCreate  → POST /professors body
ProfessorRead    → liste yanıtı (özet)
ProfessorDetail  → GET /professors/{id} yanıtı (ortalama puan dahil)
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# NOT: SL (School of Languages) faaliyet dışı bırakıldı. Eski DB'lerde SL
# kayıtları olabilir; faculty alanı str olarak da kabul edilir ama yeni
# kayıtlarda SL kullanılamaz.
FacultyCode = Literal["FENS", "FASS", "SBS"]


class ProfessorCreate(BaseModel):
    """POST /professors için istek gövdesi."""
    name: str = Field(..., min_length=2, max_length=128, examples=["Kamer Kaya"])
    title: str | None = Field(None, max_length=64, examples=["Assoc. Prof."])
    department: str | None = Field(None, max_length=128, examples=["Computer Science & Engineering"])
    faculty: FacultyCode | None = Field(None, examples=["FENS"])


class CourseInProfessor(BaseModel):
    """Professor detay yanıtında iç içe gelen ders özeti."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    semester: str | None


class ProfessorRead(BaseModel):
    """GET /professors liste elemanı — hafif yanıt."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str | None
    department: str | None
    faculty: str | None
    created_at: datetime
    average_rating: float | None = Field(
        None, description="Tüm yorumların ortalama puanı (yorum yoksa null)"
    )
    review_count: int = Field(0, description="Bu hocaya yazılmış toplam yorum sayısı")


class ProfessorDetail(BaseModel):
    """GET /professors/{id} — tam detay + ortalama puan."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str | None
    department: str | None
    faculty: str | None
    created_at: datetime
    average_rating: float | None = Field(
        None, description="Tüm yorumların ortalama puanı (yorum yoksa null)"
    )
    review_count: int = Field(0, description="Bu hocaya yazılmış toplam yorum sayısı")
    courses: list[CourseInProfessor] = []
