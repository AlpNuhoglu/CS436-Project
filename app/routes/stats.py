"""
Stats endpoint'leri.

GET /stats/home → HomePage (Keşfet) için aggregate edilmiş dinamik veri.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.professor import Professor
from app.models.professor_course import ProfessorCourse
from app.models.review import Review
from app.schemas.course import CourseRead
from app.schemas.professor import ProfessorRead
from app.schemas.stats import (
    FeaturedProfessor,
    FeaturedProfessorCourse,
    HomeStats,
    HomeSummary,
    LatestReview,
    LeaderboardStats,
    PopularSearchTerm,
    SemesterOption,
    TrendingCourse,
)

router = APIRouter(prefix="/stats", tags=["stats"])


def _latest_review_from_row(review: Review) -> LatestReview:
    # Tüm yorumlar anonim — username asla dönmez.
    return LatestReview(
        id=review.id,
        rating=review.rating,
        comment=review.comment,
        is_anonymous=True,
        username=None,
        created_at=review.created_at,
        course_code=review.course.code if review.course else None,
        professor_name=review.professor.name if review.professor else None,
    )


@router.get("/home", response_model=HomeStats, summary="HomePage (Keşfet) verileri")
def home_stats(db: Session = Depends(get_db)):
    """
    HomePage için tek çağrıda toplanmış dinamik veri:

    - **summary**: Hocalar / dersler / yorumlar / bu haftaki yorum sayısı
    - **trending_course**: Son 7 günde en çok yorum alan ders (yoksa all-time)
    - **featured_professor**: En çok yorum alan hoca (rating dağılımı + dersler)
    - **latest_review**: En yeni (yorumlu) değerlendirme
    - **top_professors**: En çok yorum alan ilk 6 hoca (min 1 yorum)
    - **top_courses**: En çok yorum alan ilk 6 ders
    - **latest_reviews**: CTA şeridi için son 3 yorum
    - **popular_searches**: En popüler 5 ders (kod olarak)
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # ── Summary ──────────────────────────────────────────────────────────────
    professors_count = db.query(func.count(Professor.id)).scalar() or 0
    courses_count = db.query(func.count(Course.id)).scalar() or 0
    reviews_count = db.query(func.count(Review.id)).scalar() or 0
    reviews_this_week = (
        db.query(func.count(Review.id))
        .filter(Review.created_at >= week_ago)
        .scalar()
        or 0
    )
    summary = HomeSummary(
        professors_count=int(professors_count),
        courses_count=int(courses_count),
        reviews_count=int(reviews_count),
        reviews_this_week=int(reviews_this_week),
    )

    # ── Trending course (son 7 gün, fallback: all-time) ──────────────────────
    trending_course: TrendingCourse | None = None

    # Her ders için week count + total count + avg rating + avg difficulty + avg workload
    week_count_expr = func.sum(
        case((Review.created_at >= week_ago, 1), else_=0)
    ).label("week_count")
    total_count_expr = func.count(Review.id).label("total_count")
    avg_rating_expr = func.avg(Review.rating).label("avg_rating")
    avg_diff_expr = func.avg(Review.difficulty).label("avg_diff")
    avg_wl_expr = func.avg(Review.workload_hours).label("avg_wl")

    course_stats_rows = (
        db.query(Course, week_count_expr, total_count_expr, avg_rating_expr, avg_diff_expr, avg_wl_expr)
        .outerjoin(Review, Review.course_id == Course.id)
        .group_by(Course.id)
        .all()
    )

    # Önce bu hafta en çok yorumu olan ders — yoksa all-time en çok yorumlu
    sorted_by_week = sorted(
        course_stats_rows,
        key=lambda r: (int(r[1] or 0), int(r[2] or 0), float(r[3] or 0)),
        reverse=True,
    )
    if sorted_by_week and int(sorted_by_week[0][1] or 0) > 0:
        picked = sorted_by_week[0]
    else:
        sorted_by_total = sorted(
            course_stats_rows,
            key=lambda r: (int(r[2] or 0), float(r[3] or 0)),
            reverse=True,
        )
        picked = sorted_by_total[0] if sorted_by_total else None

    if picked:
        course, week_cnt, total_cnt, avg, avg_d, avg_w = picked
        prof_cnt = (
            db.query(func.count(ProfessorCourse.professor_id))
            .filter(ProfessorCourse.course_id == course.id)
            .scalar()
            or 0
        )
        eff_diff = round(float(avg_d)) if avg_d is not None else course.difficulty
        eff_wl = round(float(avg_w)) if avg_w is not None else course.workload_hours
        trending_course = TrendingCourse(
            id=course.id,
            code=course.code,
            name=course.name,
            department=course.department,
            faculty=course.faculty,
            difficulty=eff_diff,
            workload_hours=eff_wl,
            average_rating=round(float(avg), 2) if avg is not None else None,
            review_count_total=int(total_cnt or 0),
            review_count_week=int(week_cnt or 0),
            professor_count=int(prof_cnt),
        )

    # ── Featured professor (all-time en çok yorumlu) ─────────────────────────
    featured_professor: FeaturedProfessor | None = None
    prof_row = (
        db.query(Professor, func.count(Review.id), func.avg(Review.rating))
        .outerjoin(Review, Review.professor_id == Professor.id)
        .group_by(Professor.id)
        .order_by(func.count(Review.id).desc(), func.avg(Review.rating).desc().nullslast())
        .first()
    )
    if prof_row:
        prof, prof_review_count, prof_avg = prof_row
        prof_review_count = int(prof_review_count or 0)
        # Rating dağılımı (yüzde)
        dist_rows = (
            db.query(Review.rating, func.count(Review.id))
            .filter(Review.professor_id == prof.id)
            .group_by(Review.rating)
            .all()
        )
        dist_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating, cnt in dist_rows:
            if rating in dist_counts:
                dist_counts[rating] = int(cnt)
        if prof_review_count > 0:
            rating_distribution = [
                round(dist_counts[i] * 100 / prof_review_count) for i in range(1, 6)
            ]
        else:
            rating_distribution = [0, 0, 0, 0, 0]

        # Bu hocanın verdiği en fazla 3 ders (ders kodu)
        course_rows = (
            db.query(Course.id, Course.code)
            .join(ProfessorCourse, ProfessorCourse.course_id == Course.id)
            .filter(ProfessorCourse.professor_id == prof.id)
            .order_by(ProfessorCourse.semester.desc())
            .limit(3)
            .all()
        )
        featured_professor = FeaturedProfessor(
            id=prof.id,
            name=prof.name,
            title=prof.title,
            department=prof.department,
            faculty=prof.faculty,
            average_rating=round(float(prof_avg), 2) if prof_avg is not None else None,
            review_count=prof_review_count,
            rating_distribution=rating_distribution,
            courses=[FeaturedProfessorCourse(id=cid, code=ccode) for cid, ccode in course_rows],
        )

    # ── Latest review (yorumu boş olmayan en yeni) ───────────────────────────
    latest_review_row = (
        db.query(Review)
        .filter(Review.comment.isnot(None), func.length(Review.comment) > 0)
        .order_by(Review.created_at.desc())
        .first()
    )
    latest_review = _latest_review_from_row(latest_review_row) if latest_review_row else None

    # ── Top professors (en çok yorum alan ilk 6, yorumu olanlar) ─────────────
    top_prof_rows = (
        db.query(Professor, func.avg(Review.rating), func.count(Review.id))
        .join(Review, Review.professor_id == Professor.id)
        .group_by(Professor.id)
        .order_by(func.count(Review.id).desc(), func.avg(Review.rating).desc().nullslast())
        .limit(6)
        .all()
    )
    top_professors = [
        ProfessorRead(
            id=p.id,
            name=p.name,
            title=p.title,
            department=p.department,
            faculty=p.faculty,
            created_at=p.created_at,
            average_rating=round(float(avg), 2) if avg is not None else None,
            review_count=int(cnt or 0),
        )
        for p, avg, cnt in top_prof_rows
    ]
    # Eğer hiç yorum yoksa en azından alfabetik ilk 6 hoca
    if not top_professors:
        fallback = db.query(Professor).order_by(Professor.name).limit(6).all()
        top_professors = [
            ProfessorRead(
                id=p.id, name=p.name, title=p.title, department=p.department,
                faculty=p.faculty, created_at=p.created_at,
                average_rating=None, review_count=0,
            )
            for p in fallback
        ]

    # ── Top courses ──────────────────────────────────────────────────────────
    top_course_rows = (
        db.query(Course, func.avg(Review.rating), func.count(Review.id))
        .join(Review, Review.course_id == Course.id)
        .group_by(Course.id)
        .order_by(func.count(Review.id).desc(), func.avg(Review.rating).desc().nullslast())
        .limit(6)
        .all()
    )
    top_courses = [
        CourseRead(
            id=c.id,
            code=c.code,
            name=c.name,
            department=c.department,
            faculty=c.faculty,
            difficulty=c.difficulty,
            workload_hours=c.workload_hours,
            created_at=c.created_at,
            average_rating=round(float(avg), 2) if avg is not None else None,
            review_count=int(cnt or 0),
        )
        for c, avg, cnt in top_course_rows
    ]
    if not top_courses:
        fallback = db.query(Course).order_by(Course.code).limit(6).all()
        top_courses = [
            CourseRead(
                id=c.id, code=c.code, name=c.name, department=c.department,
                faculty=c.faculty, difficulty=c.difficulty,
                workload_hours=c.workload_hours, created_at=c.created_at,
                average_rating=None, review_count=0,
            )
            for c in fallback
        ]

    # ── Latest reviews (CTA band — 3 tane yorumlu) ───────────────────────────
    latest_review_rows = (
        db.query(Review)
        .filter(Review.comment.isnot(None), func.length(Review.comment) > 0)
        .order_by(Review.created_at.desc())
        .limit(3)
        .all()
    )
    latest_reviews = [_latest_review_from_row(r) for r in latest_review_rows]

    # ── Popular searches: en çok yorumlu 5 ders (kodu chip olarak) ───────────
    pop_rows = (
        db.query(Course.id, Course.code, func.count(Review.id).label("cnt"))
        .outerjoin(Review, Review.course_id == Course.id)
        .group_by(Course.id)
        .order_by(func.count(Review.id).desc(), Course.code)
        .limit(5)
        .all()
    )
    popular_searches = [
        PopularSearchTerm(label=code, kind="course", target_id=cid)
        for cid, code, _ in pop_rows
    ]

    return HomeStats(
        summary=summary,
        trending_course=trending_course,
        featured_professor=featured_professor,
        latest_review=latest_review,
        top_professors=top_professors,
        top_courses=top_courses,
        latest_reviews=latest_reviews,
        popular_searches=popular_searches,
    )


# ── /stats/leaderboard ──────────────────────────────────────────────────────

@router.get(
    "/leaderboard",
    response_model=LeaderboardStats,
    summary="En çok yorum alan hocalar/dersler (opsiyonel dönem)",
)
def leaderboard(
    semester: str | None = Query(
        None,
        description=(
            "Sadece bu dönemin yorumlarına göre sırala "
            "(örn. 'Spring 2025'). Boş = tüm zamanlar."
        ),
        examples=["Spring 2025"],
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Top-N (her iki liste için ayrı uygulanır)",
    ),
    db: Session = Depends(get_db),
):
    """
    Yorum sayısı (descending) + ortalama puan (descending) sıralamasıyla
    top hocaları ve dersleri döndürür.

    `?semester=` verildiyse sadece o dönemin yorumları sayılır; bu durumda
    yorumu olmayan hoca/dersler listede yer almaz (INNER JOIN davranışı).
    """
    # Hocalar
    prof_q = db.query(
        Professor,
        func.avg(Review.rating).label("avg_rating"),
        func.count(Review.id).label("review_count"),
    ).join(Review, Review.professor_id == Professor.id)
    if semester:
        prof_q = prof_q.filter(Review.semester == semester)
    prof_rows = (
        prof_q.group_by(Professor.id)
        .order_by(
            func.count(Review.id).desc(),
            func.avg(Review.rating).desc().nullslast(),
            Professor.name,
        )
        .limit(limit)
        .all()
    )
    top_professors = [
        ProfessorRead(
            id=p.id,
            name=p.name,
            title=p.title,
            department=p.department,
            faculty=p.faculty,
            created_at=p.created_at,
            average_rating=round(float(avg), 2) if avg is not None else None,
            review_count=int(cnt or 0),
        )
        for p, avg, cnt in prof_rows
    ]

    # Dersler
    course_q = db.query(
        Course,
        func.avg(Review.rating).label("avg_rating"),
        func.count(Review.id).label("review_count"),
        func.avg(Review.difficulty).label("avg_difficulty"),
        func.avg(Review.workload_hours).label("avg_workload"),
    ).join(Review, Review.course_id == Course.id)
    if semester:
        course_q = course_q.filter(Review.semester == semester)
    course_rows = (
        course_q.group_by(Course.id)
        .order_by(
            func.count(Review.id).desc(),
            func.avg(Review.rating).desc().nullslast(),
            Course.code,
        )
        .limit(limit)
        .all()
    )
    top_courses = [
        CourseRead(
            id=c.id,
            code=c.code,
            name=c.name,
            department=c.department,
            faculty=c.faculty,
            difficulty=round(float(avg_d)) if avg_d is not None else c.difficulty,
            workload_hours=round(float(avg_w)) if avg_w is not None else c.workload_hours,
            created_at=c.created_at,
            average_rating=round(float(avg), 2) if avg is not None else None,
            review_count=int(cnt or 0),
        )
        for c, avg, cnt, avg_d, avg_w in course_rows
    ]

    return LeaderboardStats(
        semester=semester,
        top_professors=top_professors,
        top_courses=top_courses,
    )


# ── /stats/semesters ────────────────────────────────────────────────────────

@router.get(
    "/semesters",
    response_model=list[SemesterOption],
    summary="Sistemde yorumu olan tüm dönemler (frontend dropdown için)",
)
def list_semesters(db: Session = Depends(get_db)):
    """
    Yorumlarda kullanılmış tüm dönem değerlerini, her birinin yorum sayısıyla
    birlikte döndürür. NULL semester'lar listeye dahil edilmez.

    Frontend dönem dropdown'unu bu endpoint'ten doldurur.
    """
    rows = (
        db.query(Review.semester, func.count(Review.id))
        .filter(Review.semester.isnot(None))
        .group_by(Review.semester)
        .order_by(Review.semester.desc())
        .all()
    )
    return [SemesterOption(semester=sem, review_count=int(cnt)) for sem, cnt in rows]
