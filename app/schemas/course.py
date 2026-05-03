"""
Course Pydantic şemaları.

CourseCreate  → POST /courses body
CourseRead    → liste yanıtı (özet)
CourseDetail  → GET /courses/{id} yanıtı
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# FENS / FASS / SBS — SL (School of Languages) sistemden çıkarıldı.
# Eski DB kayıtlarında SL geçen rows kalabilir ama yeni kayıt kabul edilmez.
FacultyCode = Literal["FENS", "FASS", "SBS"]


class CourseCreate(BaseModel):
    """POST /courses için istek gövdesi."""
    code: str = Field(..., min_length=2, max_length=16, examples=["CS436"])
    name: str = Field(..., min_length=2, max_length=256, examples=["Cloud Computing & Distributed Systems"])
    department: str | None = Field(None, max_length=128, examples=["Computer Science & Engineering"])
    faculty: FacultyCode | None = Field(None, examples=["FENS"])
    difficulty: int | None = Field(None, ge=1, le=5, examples=[4])
    workload_hours: int | None = Field(None, ge=0, le=60, examples=[12])


class ProfessorInCourse(BaseModel):
    """Course detay yanıtında iç içe gelen hoca özeti."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str | None
    semester: str | None


class CourseRead(BaseModel):
    """GET /courses liste elemanı — hafif yanıt."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    department: str | None
    faculty: str | None
    difficulty: int | None
    workload_hours: int | None
    created_at: datetime
    average_rating: float | None = Field(
        None, description="Bu dersin yorum ortalaması (yorum yoksa null)"
    )
    review_count: int = Field(0, description="Bu derse yazılmış toplam yorum sayısı")


class CourseListResponse(BaseModel):
    """GET /courses — sayfalanmış ders listesi yanıtı."""

    items: list[CourseRead]
    total: int = Field(..., ge=0, description="Filtre sonrası toplam ders sayısı")
    skip: int = Field(..., ge=0, description="Atlanan kayıt sayısı")
    limit: int = Field(..., ge=1, description="Bu sayfadaki üst kayıt sınırı")
    has_more: bool = Field(..., description="Devam sayfası var mı?")


class CourseDetail(BaseModel):
    """GET /courses/{id} — tam detay + bu dersi veren hocalar."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    department: str | None
    faculty: str | None
    difficulty: int | None
    workload_hours: int | None
    created_at: datetime
    average_rating: float | None = Field(
        None, description="Bu derse ait yorumların ortalama puanı"
    )
    review_count: int = Field(0, description="Bu derse yazılmış toplam yorum sayısı")
    professors: list[ProfessorInCourse] = []
