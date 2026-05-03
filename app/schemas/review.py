"""
Review ve Upvote Pydantic şemaları.

Bu projede tüm yorumlar **anonimdir**. Bu yüzden:
  - `ReviewCreate`'te `is_anonymous` alanı yok (sunucu zorla True yapar).
  - `ReviewRead`'te `username` her zaman None döner.

Topluluk kuralları:
  - `comment` alanı `app.utils.profanity.contains_profanity` ile kontrol edilir.
  - Açık küfür içeren yorumlar 422 ile reddedilir (frontend hata mesajını gösterir).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.profanity import contains_profanity


class ReviewCreate(BaseModel):
    """POST /reviews için istek gövdesi (her zaman anonim)."""
    professor_id: int | None = Field(None, description="Hoca ID — zorunlu")
    course_id: int | None = Field(None, description="Ders ID — zorunlu")
    semester: str | None = Field(
        None,
        max_length=32,
        description=(
            "Yorumun ait olduğu dönem; örn. 'Spring 2025', 'Fall 2024'. "
            "professor_courses tablosundaki değerlerle aynı formatta tutulması "
            "önerilir; uyumsuz değerler kabul edilir ama 'unverified' uyarısı üretir."
        ),
        examples=["Spring 2025"],
    )
    rating: int = Field(..., ge=1, le=5, description="1–5 arası puan")
    difficulty: int | None = Field(
        None, ge=1, le=5,
        description="Öğrencinin hissettiği zorluk (1-5). Ders yorumlarında zorunludur.",
    )
    workload_hours: int | None = Field(
        None, ge=0, le=60,
        description="Haftalık iş yükü saati (0-60). Ders yorumu için önerilir.",
    )
    comment: str | None = Field(None, max_length=2000, description="Yorum metni (opsiyonel)")

    @field_validator("semester")
    @classmethod
    def _normalize_semester(cls, v: str | None) -> str | None:
        """Boş string'i None'a çevir; başında/sonunda boşluk varsa kırp."""
        if v is None:
            return None
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def _validate_review_context(self) -> "ReviewCreate":
        if self.professor_id is None:
            raise ValueError("Hoca seçimi zorunludur.")
        if self.course_id is None:
            raise ValueError("Ders seçimi zorunludur.")
        if self.semester is None:
            raise ValueError("Dönem seçimi zorunludur.")
        if self.difficulty is None:
            raise ValueError("Zorluk seçimi zorunludur.")
        return self

    @field_validator("comment")
    @classmethod
    def _no_profanity(cls, v: str | None) -> str | None:
        """Açık küfür içeren yorumları reddet (topluluk kuralları)."""
        if v is None:
            return v
        bad, _ = contains_profanity(v)
        if bad:
            # Kullanıcıya yakalanan kelimeyi göstermiyoruz — sadece neden reddedildiğini.
            raise ValueError(
                "Yorumunuz topluluk kurallarına uymuyor. "
                "Lütfen küfür ve hakaret içermeyen, saygılı bir dil kullanın."
            )
        return v


class ReviewRead(BaseModel):
    """Yorum yanıtı."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    professor_id: int | None
    course_id: int | None
    semester: str | None = None
    rating: int
    difficulty: int | None = None
    workload_hours: int | None = None
    comment: str | None
    is_anonymous: bool = False
    upvote_count: int = 0
    downvote_count: int = 0
    # Bu (hoca, ders, dönem) üçlüsü scraper'dan gelen professor_courses
    # kayıtlarıyla eşleşiyor mu? Esnek validasyon: eşleşmese bile yorum
    # kabul edilir, ama frontend bu bilgiyi kullanıcıya rozet/ikaz olarak
    # gösterebilir ("Bu kombinasyon SUIS'te bulunamadı").
    is_verified_pairing: bool = True
    created_at: datetime
    updated_at: datetime
    first_name: str | None = None
    last_name: str | None = None
    # Bu yorumu okuyan giriş yapmış kullanıcı yorumun sahibi mi?
    # Frontend buna bakarak "Düzenle / Sil" butonlarını gösterir.
    # Anonim ziyaretçide veya başkasının yorumunda her zaman False döner.
    is_owner: bool = False


class ReviewUpdate(BaseModel):
    """
    PUT /reviews/{id} için istek gövdesi — tüm alanlar opsiyonel,
    sadece gönderilenler güncellenir (partial update).

    Sahibi olmayan kullanıcılar 403 alır. (prof, course, semester) üçlüsü
    burada değiştirilemez — sadece içerik (rating, difficulty, workload, comment).
    """
    rating: int | None = Field(None, ge=1, le=5)
    difficulty: int | None = Field(None, ge=1, le=5)
    workload_hours: int | None = Field(None, ge=0, le=60)
    comment: str | None = Field(None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def _no_profanity(cls, v: str | None) -> str | None:
        if v is None:
            return v
        bad, _ = contains_profanity(v)
        if bad:
            raise ValueError(
                "Yorumunuz topluluk kurallarına uymuyor. "
                "Lütfen küfür ve hakaret içermeyen, saygılı bir dil kullanın."
            )
        return v


class UpvoteStatus(BaseModel):
    """Upvote/downvote toggle sonucu."""
    upvoted: bool = Field(..., description="True: beğeni eklendi, False: beğeni kaldırıldı")
    upvote_count: int = Field(..., description="Güncel beğeni sayısı")
    downvoted: bool = Field(False, description="True: faydasız işaretlendi, False: kaldırıldı")
    downvote_count: int = Field(0, description="Güncel faydasız sayısı")
