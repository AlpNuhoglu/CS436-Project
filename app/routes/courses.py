"""
Course endpoint'leri.

GET  /courses       → tüm dersleri listele (bölüme/fakülteye/zorluğa göre filtrele)
GET  /courses/{id}  → ders detayı + ortalama puan + hocalar
POST /courses       → yeni ders ekle (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.professor import Professor
from app.models.professor_course import ProfessorCourse
from app.models.review import Review
from app.schemas.course import (
    CourseCreate,
    CourseDetail,
    CourseListResponse,
    CourseRead,
    ProfessorInCourse,
)

router = APIRouter(prefix="/courses", tags=["courses"])


# ── GET /courses ──────────────────────────────────────────────────────────────

@router.get("", response_model=CourseListResponse, summary="Ders listesi")
def list_courses(
    department: str | None = Query(None, description="Bölüme göre filtrele (kısmi eşleşme)"),
    faculty: str | None = Query(
        None,
        description="Fakülte kısaltması: FENS / FASS / SBS",
        examples=["FENS"],
    ),
    q: str | None = Query(None, description="Ders kodu veya adında ara"),
    min_difficulty: int | None = Query(None, ge=1, le=5, description="Minimum zorluk (1-5)"),
    max_difficulty: int | None = Query(None, ge=1, le=5, description="Maksimum zorluk (1-5)"),
    max_workload: int | None = Query(None, ge=0, le=60, description="Haftalık maksimum saat"),
    semester: str | None = Query(
        None,
        description=(
            "Yorum agregatlarını (avg_rating, review_count, difficulty, workload_hours) "
            "sadece bu döneme göre hesapla. Boş = tüm zamanlar (örn. 'Spring 2025')."
        ),
        examples=["Spring 2025"],
    ),
    skip: int = Query(0, ge=0, description="Kaç kayıt atlanacak"),
    limit: int = Query(
        200,
        ge=1,
        le=1000,
        description=(
            "Kaç kayıt döndürülecek. Frontend tüm katalogu art arda sayfalayıp "
            "çekebilir; bu yüzden default orta boy tutulur."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Ders listesi — çoklu filtreleri destekler.

    - **department**: Bölüm adı (kısmi eşleşme).
    - **faculty**: FENS / FASS / SBS.
    - **q**: Ders kodu veya isim araması.
    - **min_difficulty** / **max_difficulty**: Zorluk aralığı.
    - **max_workload**: Haftalık iş yükü üst sınırı.
    - **semester**: Belirli bir döneme ait yorum istatistikleri ("Spring 2025'in
      en yüksek puanlı dersleri" gibi sorgular için). Liste filtrelenmez,
      sadece avg/count/difficulty/workload o dönemin yorumlarına göre hesaplanır.
    """
    # Zorluk ve iş yükü önce öğrenci yorumlarından ortalanır; yoksa courses tablosundaki
    # baseline değer kullanılır.
    review_join_cond = Review.course_id == Course.id
    if semester:
        review_join_cond = review_join_cond & (Review.semester == semester)

    query = (
        db.query(
            Course,
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
            func.avg(Review.difficulty).label("avg_difficulty"),
            func.avg(Review.workload_hours).label("avg_workload"),
        )
        .outerjoin(Review, review_join_cond)
    )

    if department:
        query = query.filter(Course.department.ilike(f"%{department}%"))
    if faculty:
        query = query.filter(Course.faculty == faculty.upper())
    if q:
        like = f"%{q}%"
        query = query.filter((Course.code.ilike(like)) | (Course.name.ilike(like)))

    rows = (
        query.group_by(Course.id)
        .order_by(Course.code)
        .all()
    )

    def effective_difficulty(c, avg_d):
        return round(float(avg_d)) if avg_d is not None else c.difficulty

    def effective_workload(c, avg_w):
        return round(float(avg_w)) if avg_w is not None else c.workload_hours

    # Python tarafında difficulty/workload filtrelerini uygula çünkü "effective"
    # değer yorumlardan geliyor.
    filtered = []
    for c, avg, cnt, avg_d, avg_w in rows:
        eff_d = effective_difficulty(c, avg_d)
        eff_w = effective_workload(c, avg_w)
        if min_difficulty is not None and (eff_d is None or eff_d < min_difficulty):
            continue
        if max_difficulty is not None and (eff_d is None or eff_d > max_difficulty):
            continue
        if max_workload is not None and (eff_w is None or eff_w > max_workload):
            continue
        filtered.append((c, avg, cnt, eff_d, eff_w))

    total = len(filtered)
    page = [
        CourseRead(
            id=c.id,
            code=c.code,
            name=c.name,
            department=c.department,
            faculty=c.faculty,
            difficulty=eff_d,
            workload_hours=eff_w,
            created_at=c.created_at,
            average_rating=round(float(avg), 2) if avg is not None else None,
            review_count=int(cnt or 0),
        )
        for c, avg, cnt, eff_d, eff_w in filtered[skip : skip + limit]
    ]
    return CourseListResponse(
        items=page,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(page)) < total,
    )


# ── GET /courses/{id} ─────────────────────────────────────────────────────────

@router.get("/{course_id}", response_model=CourseDetail, summary="Ders detayı")
def get_course(
    course_id: int,
    semester: str | None = Query(
        None,
        description=(
            "Yalnızca bu döneme ait yorumların ortalama/sayısı/zorluk/iş yükü "
            "değerlerini döndür (örn. 'Spring 2025'). Boş bırakılırsa tüm "
            "dönemler hesaplanır. professors listesi filtreden etkilenmez."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Belirli bir dersin bilgilerini döndürür.

    Yanıta şunlar eklenir:
    - **average_rating**: Yorum ortalaması (semester filtresi varsa o döneme göre).
    - **difficulty / workload_hours**: Yorum bazlı ortalamalar (semester'a duyarlı).
    - **professors**: Bu dersi veren tüm hocalar — semester filtresinden etkilenmez.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ders bulunamadı.")

    agg_q = db.query(
        func.avg(Review.rating),
        func.count(Review.id),
        func.avg(Review.difficulty),
        func.avg(Review.workload_hours),
    ).filter(Review.course_id == course_id)
    if semester:
        agg_q = agg_q.filter(Review.semester == semester)
    avg, cnt, avg_d, avg_w = agg_q.one()
    average_rating = round(float(avg), 2) if avg is not None else None
    review_count = int(cnt or 0)
    effective_difficulty = round(float(avg_d)) if avg_d is not None else course.difficulty
    effective_workload = round(float(avg_w)) if avg_w is not None else course.workload_hours

    rows = (
        db.query(Professor, ProfessorCourse.semester)
        .join(ProfessorCourse, ProfessorCourse.professor_id == Professor.id)
        .filter(ProfessorCourse.course_id == course_id)
        .order_by(ProfessorCourse.semester.desc(), Professor.name)
        .all()
    )
    professors = [
        ProfessorInCourse(
            id=prof.id,
            name=prof.name,
            title=prof.title,
            semester=semester,
        )
        for prof, semester in rows
    ]

    return CourseDetail(
        id=course.id,
        code=course.code,
        name=course.name,
        department=course.department,
        faculty=course.faculty,
        difficulty=effective_difficulty,
        workload_hours=effective_workload,
        created_at=course.created_at,
        average_rating=average_rating,
        review_count=review_count,
        professors=professors,
    )


# ── POST /courses ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni ders ekle (admin)",
)
def create_course(body: CourseCreate, db: Session = Depends(get_db)):
    """
    Yeni bir ders kaydı oluşturur. Aynı kodla ders zaten varsa 409 döner.
    """
    existing = db.query(Course).filter(Course.code == body.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{body.code}' kodlu ders zaten mevcut.",
        )

    course = Course(
        code=body.code.upper(),
        name=body.name,
        department=body.department,
        faculty=body.faculty,
        difficulty=body.difficulty,
        workload_hours=body.workload_hours,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
