import { useEffect, useMemo, useState } from 'react'
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom'
import { getCourse, getCourseReviews } from '../api'
import type { Review } from '../types'
import StarRating from '../components/ui/StarRating'
import ReviewCard from '../components/ReviewCard'
import ReviewForm from '../components/ReviewForm'

export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const backUrl = (location.state as { back?: string } | null)?.back ?? '/courses'
  const [course, setCourse] = useState<any>(null)
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [semester, setSemester] = useState<string>('')

  const numId = Number(id)

  const reloadReviews = () => {
    getCourseReviews(numId, semester ? { semester } : {}).then(setReviews)
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getCourse(numId, semester ? { semester } : {}),
      getCourseReviews(numId, semester ? { semester } : {}),
    ])
      .then(([crs, revs]) => { setCourse(crs); setReviews(revs) })
      .finally(() => setLoading(false))
  }, [numId, semester])

  const availableSemesters = useMemo<string[]>(() => {
    if (!course?.professors) return []
    const set = new Set<string>()
    for (const p of course.professors) {
      if (p.semester) set.add(p.semester)
    }
    return Array.from(set).sort().reverse()
  }, [course])

  const visibleProfessors = useMemo(() => {
    if (!course?.professors) return []
    if (!semester) return course.professors
    return course.professors.filter((p: any) => p.semester === semester)
  }, [course, semester])

  if (loading && !course) return <div className="text-center py-20 text-gray-400">Yükleniyor...</div>
  if (!course) return <div className="text-center py-20 text-gray-500">Ders bulunamadı.</div>

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Back button */}
      <button onClick={() => navigate(backUrl)}
        className="inline-flex items-center gap-2 mb-5 px-4 py-2 rounded-lg bg-white border border-[#dde3ec] text-sm font-medium text-gray-700 hover:bg-[#003087] hover:text-white hover:border-[#003087] transition-all shadow-sm group">
        <svg className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Geri Dön
      </button>

      {/* Header */}
      <div className="bg-white rounded-2xl border border-[#dde3ec] p-6 mb-6">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 rounded-xl bg-[#003087] text-white flex items-center justify-center font-bold text-sm shrink-0">
            {course.code}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">{course.name}</h1>
            <p className="text-gray-400 text-sm mt-0.5">{course.department}</p>
            {course.average_rating != null && (
              <div className="flex items-center gap-2 mt-3">
                <StarRating value={course.average_rating} size="md" />
                <span className="text-lg font-bold text-gray-800">{course.average_rating.toFixed(1)}</span>
                <span className="text-sm text-gray-400">({reviews.length} yorum{semester ? ` · ${semester}` : ''})</span>
              </div>
            )}
          </div>
          <button onClick={() => setShowForm(v => !v)}
            className="bg-[#003087] hover:bg-[#002060] text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors shrink-0">
            + Yorum Yaz
          </button>
        </div>

        {/* Dönem dropdown */}
        {availableSemesters.length > 0 && (
          <div className="mt-5 pt-5 border-t border-[#eef1f6] flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">Dönem filtresi:</label>
            <select
              value={semester}
              onChange={e => setSemester(e.target.value)}
              className="border border-[#dde3ec] rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-[#003087]"
            >
              <option value="">Tüm dönemler</option>
              {availableSemesters.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            {semester && (
              <button
                onClick={() => setSemester('')}
                className="text-xs text-gray-500 hover:text-[#003087]"
              >
                Temizle
              </button>
            )}
          </div>
        )}
      </div>

      {showForm && (
        <div className="mb-6">
          <ReviewForm
            fixedCourseId={course.id}
            fixedCourseName={`${course.code} — ${course.name}`}
            availableProfessors={course.professors}
            availableSemesters={availableSemesters}
            onSuccess={() => { setShowForm(false); reloadReviews() }}
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Professors */}
        <div>
          <h2 className="font-semibold text-gray-900 mb-3">Bu Dersi Verenler</h2>
          <div className="space-y-2">
            {visibleProfessors.length === 0 && (
              <p className="text-sm text-gray-400">
                {semester ? `${semester} için hoca bulunamadı.` : 'Hoca bulunamadı.'}
              </p>
            )}
            {visibleProfessors.map((p: any) => (
              <Link key={`${p.id}-${p.semester}`} to={`/professors/${p.id}`}
                state={{ back: `${location.pathname}${location.search}` }}
                className="bg-white rounded-lg border border-[#dde3ec] px-3 py-2.5 flex items-center gap-2 hover:border-[#003087]/30 transition-colors group">
                <div className="w-8 h-8 rounded-full bg-[#003087]/10 text-[#003087] group-hover:bg-[#003087] group-hover:text-white flex items-center justify-center text-xs font-bold transition-colors shrink-0">
                  {p.name.split(' ').map((n: string) => n[0]).slice(0, 2).join('')}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                  {p.semester && <p className="text-xs text-gray-400">{p.semester}</p>}
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Reviews */}
        <div className="lg:col-span-2">
          <h2 className="font-semibold text-gray-900 mb-3">
            Yorumlar ({reviews.length}){semester ? ` · ${semester}` : ''}
          </h2>
          {reviews.length === 0 ? (
            <div className="bg-white rounded-xl border border-[#dde3ec] p-8 text-center text-gray-400 text-sm">
              {semester
                ? `${semester} için henüz yorum yok. Filtreyi değiştir veya ilk yorumu sen yaz!`
                : 'Henüz yorum yok. İlk yorumu sen yaz!'}
            </div>
          ) : (
            <div className="space-y-4">
              {reviews.map(r => <ReviewCard key={r.id} review={r} onChanged={reloadReviews} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
