"""
Review ve Upvote endpoint'leri.

POST   /reviews                      → yorum yaz (auth gerekli)
PUT    /reviews/{id}                 → kendi yorumunu düzenle (auth, sahip)
DELETE /reviews/{id}                 → kendi yorumunu sil (auth, sahip)
GET    /professors/{id}/reviews      → hocanın yorumları (?semester=... filtresi)
GET    /courses/{id}/reviews         → dersin yorumları (?semester=... filtresi)
POST   /reviews/{id}/upvote          → beğen / beğeniyi geri al (toggle)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, get_current_user_optional
from app.database import get_db
from app.models.course import Course
from app.models.professor import Professor
from app.models.professor_course import ProfessorCourse
from app.models.review import Review
from app.models.upvote import Upvote
from app.models.downvote import Downvote as DownvoteModel
from app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate, UpvoteStatus

log = logging.getLogger("ders_forumu.reviews")

router = APIRouter(tags=["reviews"])


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _is_verified_pairing(
    db: Session,
    professor_id: int | None,
    course_id: int | None,
    semester: str | None,
) -> bool:
    """
    (hoca, ders, dönem) üçlüsünün scraper'dan gelen professor_courses
    kayıtlarıyla uyumlu olup olmadığını döner.

    Esnek validasyon mantığı:
      - Hem hoca hem ders verildiyse: (prof, course[, sem]) kombinasyonu var mı?
      - Sadece hoca: o hoca herhangi bir derste / belirtilen dönemde var mı?
      - Sadece ders: o ders herhangi bir hoca / belirtilen dönemde verilmiş mi?
      - Hiçbiri yoksa: True (validasyon kapsamı dışı).
    """
    q = db.query(ProfessorCourse.id)

    if professor_id is not None:
        q = q.filter(ProfessorCourse.professor_id == professor_id)
    if course_id is not None:
        q = q.filter(ProfessorCourse.course_id == course_id)
    if semester:
        q = q.filter(ProfessorCourse.semester == semester)

    if professor_id is None and course_id is None and not semester:
        return True

    return db.query(q.exists()).scalar() or False


def _to_review_read(
    review: Review,
    upvote_count: int,
    is_verified_pairing: bool = True,
    current_user: CurrentUser | None = None,
    downvote_count: int = 0,
) -> ReviewRead:
    is_owner = bool(current_user and current_user.id == review.user_id)
    return ReviewRead(
        id=review.id,
        professor_id=review.professor_id,
        course_id=review.course_id,
        semester=review.semester,
        rating=review.rating,
        difficulty=review.difficulty,
        workload_hours=review.workload_hours,
        comment=review.comment,
        is_anonymous=False,
        upvote_count=upvote_count,
        downvote_count=downvote_count,
        is_verified_pairing=is_verified_pairing,
        created_at=review.created_at,
        updated_at=review.updated_at,
        first_name=review.user.first_name,
        last_name=review.user.last_name,
        is_owner=is_owner,
    )


# ── POST /reviews ─────────────────────────────────────────────────────────────

@router.post(
    "/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Yorum yaz",
)
def create_review(
    body: ReviewCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Giriş yapmış kullanıcı bir hoca ve/veya ders için yorum yazar.

    - `professor_id`, `course_id` ve `semester` zorunludur.
    - Aynı kullanıcı aynı hoca+ders çifti için yalnızca bir yorum yazabilir.
    - `is_anonymous: true` ise yanıtta `username` alanı `null` döner.
    """
    # Hoca/ders var mı?
    if body.professor_id:
        prof = db.query(Professor).filter(Professor.id == body.professor_id).first()
        if not prof:
            raise HTTPException(status_code=404, detail="Hoca bulunamadı.")
    if body.course_id:
        course = db.query(Course).filter(Course.id == body.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Ders bulunamadı.")

    # Esnek pairing validasyonu — uyumsuz kombinasyonlar reddedilmez,
    # sadece is_verified_pairing=False olarak işaretlenir.
    verified = _is_verified_pairing(
        db,
        professor_id=body.professor_id,
        course_id=body.course_id,
        semester=body.semester,
    )
    if not verified:
        log.info(
            "Doğrulanamayan yorum kombinasyonu: prof=%s course=%s semester=%r user=%s",
            body.professor_id, body.course_id, body.semester, current_user.id,
        )

    # Duplicate kontrolü — (user, prof, course, semester) tuple'ı.
    # NOT: PostgreSQL'de NULL'lar UNIQUE'te ayrı sayıldığı için aynı kullanıcı
    # semester=None ile birden fazla kez yorum yazabilir; bu kasıtlı (opsiyonel
    # alan davranışı). Kullanıcı dönem belirtirse zaten unique constraint kilitler.
    existing = (
        db.query(Review)
        .filter(
            Review.user_id == current_user.id,
            Review.professor_id == body.professor_id,
            Review.course_id == body.course_id,
            Review.semester == body.semester,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Bu hoca/ders/dönem kombinasyonu için zaten bir yorumunuz var. "
                "Yorumu düzenlemek için PUT /reviews/{id} kullanın."
            ),
        )

    review = Review(
        user_id=current_user.id,
        professor_id=body.professor_id,
        course_id=body.course_id,
        semester=body.semester,
        rating=body.rating,
        difficulty=body.difficulty,
        workload_hours=body.workload_hours,
        comment=body.comment,
        is_anonymous=True,  # tüm yorumlar daima anonim
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return _to_review_read(
        review, upvote_count=0, is_verified_pairing=verified, current_user=current_user,
    )


# ── GET /professors/{id}/reviews ──────────────────────────────────────────────

@router.get(
    "/professors/{professor_id}/reviews",
    response_model=list[ReviewRead],
    summary="Hocanın yorumları",
)
def get_professor_reviews(
    professor_id: int,
    semester: str | None = Query(
        None,
        description="Belirli bir dönemin yorumları (örn. 'Spring 2025'). Boş = tüm dönemler.",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Bir hocaya yapılmış yorumları döndürür.
    Anonim yorumlarda `username` alanı `null` olarak gelir.

    `semester` query parametresi verilirse sadece o dönem için yazılan
    yorumlar döner (örn. öğrenci CS401'i Spring 2025'te aldıysa sadece o
    dönem yazılmış yorumlara bakmak isteyebilir).

    Auth header gönderildiyse istek sahibinin kendi yorumları için
    `is_owner=True` döner; diğer durumlarda False.
    """
    prof = db.query(Professor).filter(Professor.id == professor_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Hoca bulunamadı.")

    q = db.query(Review).filter(Review.professor_id == professor_id)
    if semester:
        q = q.filter(Review.semester == semester)

    reviews = (
        q.order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for r in reviews:
        count = db.query(func.count(Upvote.id)).filter(Upvote.review_id == r.id).scalar() or 0
        dcount = db.query(func.count(DownvoteModel.id)).filter(DownvoteModel.review_id == r.id).scalar() or 0
        verified = _is_verified_pairing(db, r.professor_id, r.course_id, r.semester)
        result.append(_to_review_read(r, count, is_verified_pairing=verified, current_user=current_user, downvote_count=dcount))
    return result


# ── GET /courses/{id}/reviews ─────────────────────────────────────────────────

@router.get(
    "/courses/{course_id}/reviews",
    response_model=list[ReviewRead],
    summary="Dersin yorumları",
)
def get_course_reviews(
    course_id: int,
    semester: str | None = Query(
        None,
        description="Belirli bir dönemin yorumları (örn. 'Spring 2025'). Boş = tüm dönemler.",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Bir derse yapılmış yorumları döndürür.
    Anonim yorumlarda `username` alanı `null` olarak gelir.

    `semester` query parametresi verilirse sadece o dönemin yorumları döner.
    Auth header verildiyse istek sahibi yorum sahibi olduğunda `is_owner=True`.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Ders bulunamadı.")

    q = db.query(Review).filter(Review.course_id == course_id)
    if semester:
        q = q.filter(Review.semester == semester)

    reviews = (
        q.order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for r in reviews:
        count = db.query(func.count(Upvote.id)).filter(Upvote.review_id == r.id).scalar() or 0
        dcount = db.query(func.count(DownvoteModel.id)).filter(DownvoteModel.review_id == r.id).scalar() or 0
        verified = _is_verified_pairing(db, r.professor_id, r.course_id, r.semester)
        result.append(_to_review_read(r, count, is_verified_pairing=verified, current_user=current_user, downvote_count=dcount))
    return result


# ── PUT /reviews/{id} (sahip kendi yorumunu düzenler) ───────────────────────

@router.put(
    "/reviews/{review_id}",
    response_model=ReviewRead,
    summary="Yorumu düzenle (sadece sahip)",
)
def update_review(
    review_id: int,
    body: ReviewUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Yorumu düzenler. Sadece yorumun sahibi düzenleyebilir; aksi halde 403.

    `(professor_id, course_id, semester)` üçlüsü değiştirilemez — yanlış
    pairing seçildiyse yorum silinip yenisi yazılmalı. Yalnızca
    rating / difficulty / workload_hours / comment güncellenir.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Yorum bulunamadı.")
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yalnızca kendi yorumunuzu düzenleyebilirsiniz.",
        )

    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Güncellenecek en az bir alan gönderilmelidir.",
        )

    for field, value in payload.items():
        setattr(review, field, value)

    db.commit()
    db.refresh(review)

    upvote_count = (
        db.query(func.count(Upvote.id)).filter(Upvote.review_id == review.id).scalar() or 0
    )
    downvote_count = (
        db.query(func.count(DownvoteModel.id)).filter(DownvoteModel.review_id == review.id).scalar() or 0
    )
    verified = _is_verified_pairing(db, review.professor_id, review.course_id, review.semester)
    return _to_review_read(
        review, upvote_count, is_verified_pairing=verified, current_user=current_user, downvote_count=downvote_count,
    )


# ── DELETE /reviews/{id} (sahip kendi yorumunu siler) ───────────────────────

@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Yorumu sil (sadece sahip)",
)
def delete_review(
    review_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Yorumu siler. Sadece sahip silebilir. Bağlı upvote'lar CASCADE ile
    otomatik temizlenir (FK ondelete='CASCADE').
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Yorum bulunamadı.")
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yalnızca kendi yorumunuzu silebilirsiniz.",
        )

    db.delete(review)
    db.commit()
    return None


# ── POST /reviews/{id}/upvote (toggle) ───────────────────────────────────────

@router.post(
    "/reviews/{review_id}/upvote",
    response_model=UpvoteStatus,
    summary="Beğen / beğeniyi geri al (toggle)",
)
def toggle_upvote(
    review_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Yorumu beğen veya beğeniyi geri al.

    - Daha önce beğenilmediyse → beğeni ekler, `upvoted: true` döner.
    - Daha önce beğenildiyse → beğeniyi kaldırır, `upvoted: false` döner.
    - Kişi kendi yorumunu da beğenebilir (kısıtlama yok).
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Yorum bulunamadı.")

    existing_upvote = (
        db.query(Upvote)
        .filter(Upvote.user_id == current_user.id, Upvote.review_id == review_id)
        .first()
    )

    if existing_upvote:
        db.delete(existing_upvote)
        db.commit()
        upvoted = False
    else:
        # Varsa downvote'u kaldır (aynı anda ikisi olmaz)
        existing_downvote = (
            db.query(DownvoteModel)
            .filter(DownvoteModel.user_id == current_user.id, DownvoteModel.review_id == review_id)
            .first()
        )
        if existing_downvote:
            db.delete(existing_downvote)
        db.add(Upvote(user_id=current_user.id, review_id=review_id))
        db.commit()
        upvoted = True

    upvote_count = (
        db.query(func.count(Upvote.id)).filter(Upvote.review_id == review_id).scalar() or 0
    )
    downvote_count = (
        db.query(func.count(DownvoteModel.id)).filter(DownvoteModel.review_id == review_id).scalar() or 0
    )

    return UpvoteStatus(upvoted=upvoted, upvote_count=upvote_count, downvoted=False, downvote_count=downvote_count)


# ── POST /reviews/{id}/downvote (toggle) ─────────────────────────────────────

@router.post(
    "/reviews/{review_id}/downvote",
    response_model=UpvoteStatus,
    summary="Faydasız / faydasız işaretini geri al (toggle)",
)
def toggle_downvote(
    review_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Yorumu faydasız olarak işaretle veya işareti geri al.

    - Daha önce faydasız işaretlenmediyse → downvote ekler, `downvoted: true` döner.
    - Daha önce faydasız işaretlendiyse → downvote kaldırır, `downvoted: false` döner.
    - Upvote ile birlikte olamaz: faydasız eklenirse varsa upvote otomatik kaldırılır.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Yorum bulunamadı.")

    existing_downvote = (
        db.query(DownvoteModel)
        .filter(DownvoteModel.user_id == current_user.id, DownvoteModel.review_id == review_id)
        .first()
    )

    if existing_downvote:
        db.delete(existing_downvote)
        db.commit()
        downvoted = False
    else:
        # Varsa upvote'u kaldır (aynı anda ikisi olmaz)
        existing_upvote = (
            db.query(Upvote)
            .filter(Upvote.user_id == current_user.id, Upvote.review_id == review_id)
            .first()
        )
        if existing_upvote:
            db.delete(existing_upvote)
        db.add(DownvoteModel(user_id=current_user.id, review_id=review_id))
        db.commit()
        downvoted = True

    upvote_count = (
        db.query(func.count(Upvote.id)).filter(Upvote.review_id == review_id).scalar() or 0
    )
    downvote_count = (
        db.query(func.count(DownvoteModel.id)).filter(DownvoteModel.review_id == review_id).scalar() or 0
    )

    return UpvoteStatus(upvoted=False, upvote_count=upvote_count, downvoted=downvoted, downvote_count=downvote_count)
