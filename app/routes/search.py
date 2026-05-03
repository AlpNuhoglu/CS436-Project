"""
Arama endpoint'i.

GET /search?q=ahmet → hoca adı ve ders adı/kodu üzerinde LIKE sorgusu
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.professor import Professor
from app.schemas.course import CourseRead
from app.schemas.professor import ProfessorRead
from pydantic import BaseModel

router = APIRouter(tags=["search"])


class SearchResult(BaseModel):
    professors: list[ProfessorRead]
    courses: list[CourseRead]


@router.get("/search", response_model=SearchResult, summary="Hoca ve ders ara")
def search(
    q: str = Query(..., min_length=2, description="Arama terimi (en az 2 karakter)"),
    db: Session = Depends(get_db),
):
    """
    Hoca adı ve ders adı/kodu üzerinde büyük/küçük harf duyarsız arama yapar.

    Örnek: `GET /search?q=ahmet` → adında "ahmet" geçen tüm hocalar ve dersler
    """
    # Boşlukları kaldırarak normalize et ("cs 3" → "cs3", "ali k" → "alik")
    q_normalized = q.replace(" ", "")
    pattern = f"%{q_normalized}%"

    from sqlalchemy import func as sqlfunc

    professors = (
        db.query(Professor)
        .filter(sqlfunc.replace(Professor.name, " ", "").ilike(pattern))
        .order_by(Professor.name)
        .limit(20)
        .all()
    )

    courses = (
        db.query(Course)
        .filter(
            sqlfunc.replace(Course.name, " ", "").ilike(pattern)
            | sqlfunc.replace(Course.code, " ", "").ilike(pattern)
        )
        .order_by(Course.code)
        .limit(20)
        .all()
    )

    return SearchResult(professors=professors, courses=courses)
