"""
Stats / anasayfa veri şemaları.

/stats/home endpoint'i HomePage (Keşfet) için gereken tüm dinamik veriyi
tek yanıtta döndürür.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.course import CourseRead
from app.schemas.professor import ProfessorRead


class HomeSummary(BaseModel):
    """Stat şeridi (Hocalar / Dersler / Yorumlar / Bu hafta)."""
    professors_count: int
    courses_count: int
    reviews_count: int
    reviews_this_week: int


class TrendingCourse(BaseModel):
    """Son 7 günde en çok yorum alan ders. Yorum yoksa fallback: tüm zamanlar."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    department: str | None
    faculty: str | None
    difficulty: int | None
    workload_hours: int | None
    average_rating: float | None
    review_count_total: int
    review_count_week: int
    professor_count: int


class FeaturedProfessorCourse(BaseModel):
    """Öne çıkan hocanın verdiği ders özeti (hero card için)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str


class FeaturedProfessor(BaseModel):
    """En çok yorum alan hoca (hero card)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str | None
    department: str | None
    faculty: str | None
    average_rating: float | None
    review_count: int
    # Rating'lerin 5 üzerinden dağılımı (1,2,3,4,5 yıldızların yüzdeleri)
    rating_distribution: list[int] = Field(
        default_factory=lambda: [0, 0, 0, 0, 0],
        description="1-5 yıldız dağılımı (yüzde, toplam 100)",
    )
    courses: list[FeaturedProfessorCourse] = []


class LatestReview(BaseModel):
    """Son yorum (quote card)."""
    id: int
    rating: int
    comment: str | None
    is_anonymous: bool
    username: str | None
    created_at: datetime
    course_code: str | None
    professor_name: str | None


class PopularSearchTerm(BaseModel):
    """Popüler arama (footerdaki chipler) — en çok yorum alan dersler."""
    label: str       # örn. "CS 204"
    kind: str        # "course" | "professor"
    target_id: int


class HomeStats(BaseModel):
    """/stats/home — HomePage için tek payload."""
    summary: HomeSummary
    trending_course: TrendingCourse | None
    featured_professor: FeaturedProfessor | None
    latest_review: LatestReview | None
    top_professors: list[ProfessorRead]
    top_courses: list[CourseRead]
    latest_reviews: list[LatestReview]
    popular_searches: list[PopularSearchTerm]


class LeaderboardStats(BaseModel):
    """
    /stats/leaderboard — top hocalar / dersler.

    Opsiyonel `?semester=` ile dönem bazlı; `?limit=` ile top-N kontrolü.
    """
    semester: str | None = Field(
        None, description="Filtrelenen dönem (None = tüm zamanlar)"
    )
    top_professors: list[ProfessorRead] = Field(
        default_factory=list,
        description="En çok yorum alan hocalar (yorum sayısı + ortalama puana göre sıralı)",
    )
    top_courses: list[CourseRead] = Field(
        default_factory=list,
        description="En çok yorum alan dersler (yorum sayısı + ortalama puana göre sıralı)",
    )


class SemesterOption(BaseModel):
    """/stats/semesters için tek dönem kaydı."""
    semester: str
    review_count: int
