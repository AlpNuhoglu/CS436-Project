import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import StarRating from './ui/StarRating'
import { createReview } from '../api'
import type { Course, Professor } from '../types'
import { useAuth } from '../contexts/AuthContext'

interface Props {
  professors?: Professor[]
  courses?: Course[]
  fixedProfessorId?: number
  fixedProfessorName?: string
  fixedCourseId?: number
  fixedCourseName?: string
  availableProfessors?: { id: number; name: string; semester?: string | null }[]
  availableCourses?: { id: number; code: string; name: string; semester?: string | null }[]
  /**
   * Dropdown'da gösterilecek dönem seçenekleri. Tipik olarak
   * professor.courses veya course.professors içindeki semester değerlerinden
   * dedupe edilerek hesaplanır. Boş array ise kullanıcı serbest metin girer.
   */
  availableSemesters?: string[]
  onSuccess?: () => void
}

const DIFFICULTY_LABELS: Record<number, string> = {
  1: 'Çok kolay',
  2: 'Kolay',
  3: 'Orta',
  4: 'Zor',
  5: 'Çok zor',
}

/**
 * Backend hatasını kullanıcıya gösterilecek tek bir string'e indirger.
 * - HTTPException'lardan gelen `detail: string` doğrudan kullanılır.
 * - Pydantic validation hatalarından gelen `detail: [{msg, loc, ...}]`
 *   formundan ilk anlamlı `msg` çekilir; "Value error, " ön ekleri kırpılır.
 */
function extractErrorMessage(err: any): string {
  const detail = err?.response?.data?.detail
  if (!detail) return 'Bir hata oluştu.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    const msg: string = typeof first === 'string' ? first : (first?.msg ?? '')
    // Pydantic v2 "Value error, ..." ön ekini temizle
    return msg.replace(/^Value error,?\s*/i, '') || 'Yorum doğrulanamadı.'
  }
  return 'Bir hata oluştu.'
}

export default function ReviewForm({
  professors = [],
  courses = [],
  fixedProfessorId,
  fixedProfessorName,
  fixedCourseId,
  fixedCourseName,
  availableProfessors,
  availableCourses,
  availableSemesters = [],
  onSuccess,
}: Props) {
  const { user } = useAuth()
  const [professorId, setProfessorId] = useState<number | ''>(fixedProfessorId ?? '')
  const [courseId, setCourseId] = useState<number | ''>(fixedCourseId ?? '')
  const [semester, setSemester] = useState<string>('')
  const [rating, setRating] = useState(0)
  const [difficulty, setDifficulty] = useState<number>(0)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  // Forma beslenen kaynak listeler. Dönem seçimine göre filtrelenir ve
  // tekrar eden hoca/ders kayıtları tek seçeneğe indirgenir.
  const professorList = availableProfessors ?? professors
  const courseList = availableCourses ?? courses

  const hasCourse = Boolean(fixedCourseId || courseId)

  const filteredProfessorList = useMemo(() => {
    const items = semester
      ? professorList.filter(p => !('semester' in p) || !p.semester || p.semester === semester)
      : professorList
    const seen = new Set<number>()
    return items.filter(p => {
      if (seen.has(p.id)) return false
      seen.add(p.id)
      return true
    })
  }, [professorList, semester])

  const filteredCourseList = useMemo(() => {
    const items = semester
      ? courseList.filter(c => !('semester' in c) || !c.semester || c.semester === semester)
      : courseList
    const seen = new Set<number>()
    return items.filter(c => {
      if (seen.has(c.id)) return false
      seen.add(c.id)
      return true
    })
  }, [courseList, semester])

  useEffect(() => {
    if (!fixedProfessorId && professorId && !filteredProfessorList.some(p => p.id === professorId)) {
      setProfessorId('')
    }
  }, [filteredProfessorList, fixedProfessorId, professorId])

  useEffect(() => {
    if (!fixedCourseId && courseId && !filteredCourseList.some(c => c.id === courseId)) {
      setCourseId('')
    }
  }, [filteredCourseList, fixedCourseId, courseId])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (rating === 0) { setError('Lütfen bir puan verin.'); return }
    if (!professorId) { setError('Lütfen hoca seçin.'); return }
    if (!courseId) { setError('Lütfen ders seçin.'); return }
    if (!semester.trim()) { setError('Lütfen dönem seçin.'); return }
    if (hasCourse && difficulty === 0) { setError('Lütfen zorluk seçin.'); return }

    setError(''); setLoading(true)
    try {
      await createReview({
        professor_id: professorId || null,
        course_id: courseId || null,
        semester: semester.trim(),
        rating,
        difficulty: hasCourse ? difficulty : null,
        comment: comment.trim() || undefined,
      })
      setSuccess(true)
      onSuccess?.()
    } catch (err: any) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
        <p className="text-green-700 font-medium">✓ Yorumunuz eklendi!</p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="bg-white rounded-xl border border-[#dde3ec] p-6 text-center space-y-3">
        <h3 className="font-semibold text-gray-900 text-lg">Yorum Yaz</h3>
        <p className="text-sm text-gray-600">
          Yorum yapmak için Sabancı e-postanla giriş yapman gerekiyor.
          Yorumların <b>her zaman anonim</b> olarak yayınlanır.
        </p>
        <div className="flex items-center justify-center gap-2 pt-1">
          <Link to="/login" className="px-4 py-2 rounded-lg text-sm font-medium border border-[#dde3ec] text-navy-700 hover:bg-navy-100/40 transition-colors">
            Giriş Yap
          </Link>
          <Link to="/register" className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#003087] text-white hover:bg-[#002060] transition-colors">
            Kayıt Ol
          </Link>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="bg-white rounded-xl border border-[#dde3ec] p-6 space-y-4">
      <h3 className="font-semibold text-gray-900 text-lg">Yorum Yaz</h3>

      <div className={`grid grid-cols-1 ${!fixedProfessorId && !fixedCourseId ? 'sm:grid-cols-2' : ''} gap-3`}>
        {/* Professor field */}
        {fixedProfessorId ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hoca</label>
            <div className="w-full border border-[#dde3ec] bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-700">
              {fixedProfessorName ?? `Hoca #${fixedProfessorId}`}
            </div>
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hoca *</label>
            <select value={professorId} onChange={e => setProfessorId(Number(e.target.value) || '')}
              className="w-full border border-[#dde3ec] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#003087]">
              <option value="">Hoca seçin</option>
              {filteredProfessorList.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        )}

        {/* Course field */}
        {fixedCourseId ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ders</label>
            <div className="w-full border border-[#dde3ec] bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-700">
              {fixedCourseName ?? `Ders #${fixedCourseId}`}
            </div>
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ders *</label>
            <select value={courseId} onChange={e => setCourseId(Number(e.target.value) || '')}
              className="w-full border border-[#dde3ec] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#003087]">
              <option value="">Ders seçin</option>
              {filteredCourseList.map(c => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
            </select>
          </div>
        )}
      </div>

      {/* Dönem seçici */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Dönem *</label>
        {availableSemesters.length > 0 ? (
          <select
            value={semester}
            onChange={e => setSemester(e.target.value)}
            className="w-full border border-[#dde3ec] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#003087]"
          >
            <option value="">Dönem seçin</option>
            {availableSemesters.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        ) : (
          <input
            type="text"
            value={semester}
            onChange={e => setSemester(e.target.value)}
            placeholder="örn. Spring 2025"
            maxLength={32}
            className="w-full border border-[#dde3ec] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#003087]"
          />
        )}
        <p className="text-xs text-gray-400 mt-1">
          Dönem bilgisi yorumun gerçek ders eşleşmesiyle bağlanması için zorunlu tutulur.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Puan</label>
        <StarRating value={rating} size="lg" interactive onChange={setRating} />
      </div>

      {/* Ders‐spesifik alanlar: sadece ders seçildiğinde gösterilir */}
      {hasCourse && (
        <div className="space-y-3 rounded-lg border border-[#e5ebf4] bg-[#f8faff] p-4">
          <div className="text-xs font-semibold tracking-wide text-[#003087] uppercase">
            Ders Değerlendirmesi
          </div>

          {/* Difficulty 1-5 nokta seçici */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-sm font-medium text-gray-700">Zorluk *</label>
              <span className="text-xs text-gray-500">
                {difficulty > 0 ? DIFFICULTY_LABELS[difficulty] : 'Seçin'}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              {[1, 2, 3, 4, 5].map(n => {
                const active = difficulty >= n
                return (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setDifficulty(n)}
                    aria-label={`Zorluk ${n}`}
                    className={`h-8 w-8 rounded-full border text-xs font-semibold transition-colors ${
                      active
                        ? 'bg-[#003087] border-[#003087] text-white'
                        : 'bg-white border-[#dde3ec] text-gray-500 hover:border-[#003087]'
                    }`}
                  >
                    {n}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Yorum</label>
        <textarea value={comment} onChange={e => setComment(e.target.value)} rows={3}
          placeholder="Deneyiminizi paylaşın..."
          className="w-full border border-[#dde3ec] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#003087] resize-none" />
      </div>

      <div className="flex items-start gap-2 text-xs text-gray-600 bg-[#f8faff] border border-[#e5ebf4] rounded-lg px-3 py-2">
        <svg className="w-4 h-4 text-[#003087] shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 1l3 6 6 .9-4.5 4.4 1 6.2L12 15.8 6.5 18.5l1-6.2L3 7.9 9 7l3-6z" />
        </svg>
        <span>
          Yorumun <b>anonim olarak yayınlanır</b> — kullanıcı adın hiçbir yorumda görünmez.{' '}
          Lütfen{' '}
          <Link to="/guidelines" target="_blank" className="text-[#003087] hover:underline font-medium">
            topluluk kurallarına
          </Link>
          {' '}uy: küfür içeren yorumlar otomatik reddedilir.
        </span>
      </div>

      {error && <p className="text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

      <button type="submit" disabled={loading}
        className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm">
        {loading ? 'Gönderiliyor...' : 'Yorum Gönder'}
      </button>
    </form>
  )
}
