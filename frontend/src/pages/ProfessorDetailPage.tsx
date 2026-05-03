import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { getProfessor, getProfessorReviews } from '../api'
import type { ProfessorDetail, Review } from '../types'
import StarRating from '../components/ui/StarRating'
import ReviewCard from '../components/ReviewCard'
import ReviewForm from '../components/ReviewForm'

export default function ProfessorDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const backUrl = (location.state as { back?: string } | null)?.back ?? '/professors'
  const [professor, setProfessor] = useState<ProfessorDetail | null>(null)
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  // "" = tüm dönemler. Dropdown değişince hem detay hem yorum listesi yenilenir.
  const [semester, setSemester] = useState<string>('')

  const numId = Number(id)

  // Yorum yenileme — semester filtresine sadık kalır
  const reloadReviews = () => {
    getProfessorReviews(numId, semester ? { semester } : {}).then(setReviews)
  }

  // Tam yenileme (detay + yorumlar) — semester değiştiğinde tetiklenir
  useEffect(() => {
    setLoading(true)
    Promise.all([
      getProfessor(numId, semester ? { semester } : {}),
      getProfessorReviews(numId, semester ? { semester } : {}),
    ])
      .then(([prof, revs]) => { setProfessor(prof); setReviews(revs) })
      .finally(() => setLoading(false))
  }, [numId, semester])

  // Bu hocanın professor_courses tablosunda yer aldığı tüm dönemler — dropdown
  // ve ReviewForm için kaynak. Sadece detay verisinden türetilir, ek istek atmaz.
  const availableSemesters = useMemo(() => {
    if (!professor) return []
    const set = new Set<string>()
    for (const c of professor.courses) {
      if (c.semester) set.add(c.semester)
    }
    return Array.from(set).sort().reverse()
  }, [professor])

  const visibleCourses = useMemo(() => {
    if (!professor) return []
    if (!semester) return professor.courses
    return professor.courses.filter(c => c.semester === semester)
  }, [professor, semester])

  if (loading && !professor) return <div className="text-center py-20 text-gray-400">Yükleniyor...</div>
  if (!professor) return <div className="text-center py-20 text-gray-500">Hoca bulunamadı.</div>

  const initials = professor.name.split(' ').map(n => n[0]).slice(0, 2).join('')

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

      {/* Profile header */}
      <div className="bg-white rounded-2xl border border-[#dde3ec] p-6 mb-6">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 rounded-full bg-[#003087] text-white flex items-center justify-center font-bold text-xl shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-gray-900">{professor.name}</h1>
            {professor.title && <p className="text-[#003087] font-medium">{professor.title}</p>}
            {professor.department && <p className="text-gray-400 text-sm mt-0.5">{professor.department}</p>}
            {professor.average_rating != null && (
              <div className="flex items-center gap-2 mt-3">
                <StarRating value={professor.average_rating} size="md" />
                <span className="text-lg font-bold text-gray-800">{professor.average_rating.toFixed(1)}</span>
                <span className="text-sm text-gray-400">({reviews.length} yorum{semester ? ` · ${semester}` : ''})</span>
              </div>
            )}
          </div>
          <button onClick={() => setShowForm(v => !v)}
            className="bg-[#003087] hover:bg-[#002060] text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors shrink-0">
            + Yorum Yaz
          </button>
        </div>

        {/* Dönem dropdown — yorum listesini ve istatistikleri filtreler */}
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

      {/* Review form */}
      {showForm && (
        <div className="mb-6">
          <ReviewForm
            fixedProfessorId={professor.id}
            fixedProfessorName={professor.name}
            availableCourses={professor.courses}
            availableSemesters={availableSemesters}
            onSuccess={() => { setShowForm(false); reloadReviews() }}
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Courses */}
        <div>
          <h2 className="font-semibold text-gray-900 mb-3">Verdiği Dersler</h2>
          <div className="space-y-2">
            {visibleCourses.length === 0 && (
              <p className="text-sm text-gray-400">
                {semester ? `${semester} için ders bulunamadı.` : 'Ders bulunamadı.'}
              </p>
            )}
            {visibleCourses.map(c => (
              <div key={`${c.id}-${c.semester}`}
                className="bg-white rounded-lg border border-[#dde3ec] px-3 py-2.5">
                <p className="text-sm font-semibold text-[#003087]">{c.code}</p>
                <p className="text-xs text-gray-600 truncate">{c.name}</p>
                {c.semester && <p className="text-xs text-gray-400 mt-0.5">{c.semester}</p>}
              </div>
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
