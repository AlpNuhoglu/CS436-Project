// SL (School of Languages) sistemden kaldırıldı; eski DB kayıtları kalmış
// olsa bile UI listesinde gösterilmez ve filtre seçeneği değildir.
export type Faculty = 'FENS' | 'FASS' | 'SBS'

export interface Professor {
  id: number
  name: string
  title: string | null
  department: string | null
  faculty: Faculty | null
  created_at: string
  average_rating?: number | null
  review_count?: number
}

export interface ProfessorDetail extends Professor {
  average_rating: number | null
  courses: CourseInProfessor[]
}

export interface CourseInProfessor {
  id: number
  code: string
  name: string
  semester: string | null
}

export interface Course {
  id: number
  code: string
  name: string
  department: string | null
  faculty: Faculty | null
  difficulty: number | null
  workload_hours: number | null
  created_at: string
  average_rating?: number | null
  review_count?: number
}

export interface CourseListResponse {
  items: Course[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}

export interface Review {
  id: number
  professor_id: number | null
  course_id: number | null
  semester?: string | null
  rating: number
  difficulty?: number | null
  workload_hours?: number | null
  comment: string | null
  is_anonymous: boolean
  upvote_count: number
  downvote_count: number
  // (hoca, ders, dönem) üçlüsü scraper'dan gelen veriyle eşleşiyor mu?
  // false ise frontend'de "Doğrulanmamış kombinasyon" rozeti gösterilir.
  is_verified_pairing?: boolean
  // Backend optional auth ile döner: bu yorumu okuyan giriş yapmış kullanıcı
  // yorumun sahibi mi? Sadece true ise düzenle/sil butonları gösterilir.
  is_owner?: boolean
  created_at: string
  updated_at: string
  first_name: string | null
  last_name: string | null
}

export interface SearchResult {
  professors: Professor[]
  courses: Course[]
}

export interface UpvoteStatus {
  upvoted: boolean
  upvote_count: number
  downvoted: boolean
  downvote_count: number
}

export interface ReviewCreate {
  professor_id?: number | null
  course_id?: number | null
  semester?: string | null
  rating: number
  difficulty?: number | null
  comment?: string
  // Tüm yorumlar her zaman anonim olarak yayınlanır — bu alan istemcide yok.
}

export interface ReviewUpdate {
  rating?: number
  difficulty?: number | null
  workload_hours?: number | null
  comment?: string | null
}

// ── Shared presentation helpers ──────────────────────────────────────────

export interface FacultyMeta {
  code: Faculty
  name: string
  full: string
  gradient: string            // Tailwind gradient classes for dark cards
  badgeBg: string             // Tailwind bg class for light badges
  badgeText: string           // Tailwind text class for light badges
}

export const FACULTIES: FacultyMeta[] = [
  {
    code: 'FENS',
    name: 'FENS',
    full: 'Mühendislik ve Doğa Bilimleri Fak.',
    gradient: 'from-[#14296A] to-[#0A1733]',
    badgeBg: 'bg-[#003087]',
    badgeText: 'text-white',
  },
  {
    code: 'FASS',
    name: 'FASS',
    full: 'Sanat ve Sosyal Bilimler Fak.',
    gradient: 'from-[#7C3AED] to-[#3B1A6E]',
    badgeBg: 'bg-[#7C3AED]',
    badgeText: 'text-white',
  },
  {
    code: 'SBS',
    name: 'SBS',
    full: 'Yönetim Bilimleri Fak.',
    gradient: 'from-[#E3001B] to-[#7a0013]',
    badgeBg: 'bg-[#E3001B]',
    badgeText: 'text-white',
  },
  // SL (Diller Okulu) sistemden kaldırıldı — sadece Arapça/Türkçe gibi servis
  // dersleri içerdiği için yorum platformuna değer katmıyordu.
]

export const FACULTY_MAP: Record<Faculty, FacultyMeta> = Object.fromEntries(
  FACULTIES.map(f => [f.code, f]),
) as Record<Faculty, FacultyMeta>

// ── HomePage stats payload ───────────────────────────────────────────────

export interface HomeSummary {
  professors_count: number
  courses_count: number
  reviews_count: number
  reviews_this_week: number
}

export interface TrendingCourse {
  id: number
  code: string
  name: string
  department: string | null
  faculty: Faculty | null
  difficulty: number | null
  workload_hours: number | null
  average_rating: number | null
  review_count_total: number
  review_count_week: number
  professor_count: number
}

export interface FeaturedProfessor {
  id: number
  name: string
  title: string | null
  department: string | null
  faculty: Faculty | null
  average_rating: number | null
  review_count: number
  rating_distribution: number[]
  courses: { id: number; code: string }[]
}

export interface LatestReview {
  id: number
  rating: number
  comment: string | null
  is_anonymous: boolean
  username: string | null
  created_at: string
  course_code: string | null
  professor_name: string | null
}

export interface PopularSearchTerm {
  label: string
  kind: 'course' | 'professor'
  target_id: number
}

export interface HomeStats {
  summary: HomeSummary
  trending_course: TrendingCourse | null
  featured_professor: FeaturedProfessor | null
  latest_review: LatestReview | null
  top_professors: Professor[]
  top_courses: Course[]
  latest_reviews: LatestReview[]
  popular_searches: PopularSearchTerm[]
}

export interface LeaderboardStats {
  semester: string | null
  top_professors: Professor[]
  top_courses: Course[]
}

export interface SemesterOption {
  semester: string
  review_count: number
}
