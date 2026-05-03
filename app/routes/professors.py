"""
Professor endpoint'leri.

GET  /professors              → tüm hocaları listele (bölüme / fakülteye göre filtrele)
GET  /professors/{id}         → hoca detayı + ortalama puan
GET  /professors/{id}/courses → hocanın verdiği dersler
POST /professors              → yeni hoca ekle (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.professor import Professor
from app.models.professor_course import ProfessorCourse
from app.models.course import Course
from app.models.review import Review
from app.schemas.professor import (
    CourseInProfessor,
    ProfessorCreate,
    ProfessorDetail,
    ProfessorRead,
)

router = APIRouter(prefix="/professors", tags=["professors"])


# ── GET /professors ───────────────────────────────────────────────────────────

@router.get("", response_model=list[ProfessorRead], summary="Hoca listesi")
def list_professors(
    department: str | None = Query(None, description="Bölüme göre filtrele (kısmi eşleşme)"),
    faculty: str | None = Query(
        None,
        description="Fakülte kısaltması: FENS / FASS / SBS",
        examples=["FENS"],
    ),
    q: str | None = Query(None, description="İsim içinde ara"),
    semester: str | None = Query(
        None,
        description=(
            "Sadece bu döneme ait yorumların avg_rating / review_count'unu hesapla. "
            "Boş = tüm zamanlar (örn. 'Spring 2025')."
        ),
        examples=["Spring 2025"],
    ),
    skip: int = Query(0, ge=0, description="Kaç kayıt atlanacak (sayfalama)"),
    limit: int = Query(
        500,
        ge=1,
        le=1000,
        description="Kaç kayıt döndürülecek (scraper sonrası 100'den fazla hoca olabilir)",
    ),
    db: Session = Depends(get_db),
):
    """
    Tüm hocaları döndürür. Her hoca için ortalama puan ve yorum sayısı dahildir.

    - **department**: Bölüm adına göre filtrele (case-insensitive, kısmi eşleşme).
    - **faculty**: FENS / FASS / SBS.
    - **q**: İsme göre arama.
    - **semester**: Yorum agregatlarını sadece bu döneme göre hesapla. Hocaları
      yine de döndürür ama avg/count o dönemin yorumlarına dayanır
      (yorum yoksa null/0 döner). Liste filtrelenmez, sadece istatistikler değişir.
    """
    # Semester verildiyse yorumları o döneme göre filtrelemek için correlated
    # join koşuluna ek kriter koyuyoruz; bu sayede yorumu olmayan hocalar
    # da listeden düşmüyor (LEFT JOIN davranışı korunuyor).
    review_join_cond = Review.professor_id == Professor.id
    if semester:
        review_join_cond = review_join_cond & (Review.semester == semester)

    query = (
        db.query(
            Professor,
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .outerjoin(Review, review_join_cond)
    )

    if department:
        query = query.filter(Professor.department.ilike(f"%{department}%"))
    if faculty:
        query = query.filter(Professor.faculty == faculty.upper())
    if q:
        query = query.filter(Professor.name.ilike(f"%{q}%"))

    rows = (
        query.group_by(Professor.id)
        .order_by(Professor.name)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        ProfessorRead(
            id=prof.id,
            name=prof.name,
            title=prof.title,
            department=prof.department,
            faculty=prof.faculty,
            created_at=prof.created_at,
            average_rating=round(float(avg), 2) if avg is not None else None,
            review_count=int(cnt or 0),
        )
        for prof, avg, cnt in rows
    ]


# ── GET /professors/{id} ──────────────────────────────────────────────────────

@router.get("/{professor_id}", response_model=ProfessorDetail, summary="Hoca detayı")
def get_professor(
    professor_id: int,
    semester: str | None = Query(
        None,
        description=(
            "Yalnızca bu döneme ait yorumların ortalama/sayısını döndür "
            "(örn. 'Spring 2025'). Boş bırakılırsa tüm dönemler hesaplanır. "
            "courses listesi semester filtresinden etkilenmez."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Belirli bir hocanın bilgilerini döndürür.

    Yanıta şunlar eklenir:
    - **average_rating**: Hocaya yapılan yorumların ortalaması (semester filtresi varsa o döneme göre).
    - **review_count**: Yorum sayısı (semester filtresine duyarlı).
    - **courses**: Bu hocanın verdiği tüm dersler — semester filtresinden etkilenmez.
    """
    professor = db.query(Professor).filter(Professor.id == professor_id).first()
    if not professor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hoca bulunamadı.")

    # Ortalama puan + yorum sayısı (opsiyonel dönem filtresi)
    agg_q = db.query(func.avg(Review.rating), func.count(Review.id)).filter(
        Review.professor_id == professor_id
    )
    if semester:
        agg_q = agg_q.filter(Review.semester == semester)
    avg, cnt = agg_q.one()
    average_rating = round(float(avg), 2) if avg is not None else None
    review_count = int(cnt or 0)

    # Hocanın derslerini getir (ders kodu + dönem bilgisiyle)
    rows = (
        db.query(Course, ProfessorCourse.semester)
        .join(ProfessorCourse, ProfessorCourse.course_id == Course.id)
        .filter(ProfessorCourse.professor_id == professor_id)
        .order_by(ProfessorCourse.semester.desc(), Course.code)
        .all()
    )
    courses = [
        CourseInProfessor(
            id=course.id,
            code=course.code,
            name=course.name,
            semester=semester,
        )
        for course, semester in rows
    ]

    return ProfessorDetail(
        id=professor.id,
        name=professor.name,
        title=professor.title,
        department=professor.department,
        faculty=professor.faculty,
        created_at=professor.created_at,
        average_rating=average_rating,
        review_count=review_count,
        courses=courses,
    )


# ── GET /professors/{id}/courses ─────────────────────────────────────────────

@router.get(
    "/{professor_id}/courses",
    response_model=list[CourseInProfessor],
    summary="Hocanın dersleri",
)
def get_professor_courses(
    professor_id: int,
    semester: str | None = Query(None, description="Döneme göre filtrele (örn. 'Spring 2025')"),
    db: Session = Depends(get_db),
):
    """
    Bir hocanın verdiği dersleri döndürür.

    - **semester**: Belirli bir döneme göre filtrele (opsiyonel).
    """
    professor = db.query(Professor).filter(Professor.id == professor_id).first()
    if not professor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hoca bulunamadı.")

    query = (
        db.query(Course, ProfessorCourse.semester)
        .join(ProfessorCourse, ProfessorCourse.course_id == Course.id)
        .filter(ProfessorCourse.professor_id == professor_id)
    )

    if semester:
        query = query.filter(ProfessorCourse.semester.ilike(f"%{semester}%"))

    rows = query.order_by(ProfessorCourse.semester.desc(), Course.code).all()

    return [
        CourseInProfessor(id=c.id, code=c.code, name=c.name, semester=sem)
        for c, sem in rows
    ]


# ── POST /professors ──────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProfessorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni hoca ekle (admin)",
)
def create_professor(body: ProfessorCreate, db: Session = Depends(get_db)):
    """
    Yeni bir hoca kaydı oluşturur.
    """
    professor = Professor(
        name=body.name,
        title=body.title,
        department=body.department,
        faculty=body.faculty,
    )
    db.add(professor)
    db.commit()
    db.refresh(professor)
    return professor
