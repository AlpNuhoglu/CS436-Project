import { useState } from 'react'
import StarRating from './ui/StarRating'
import { toggleUpvote, toggleDownvote, updateReview, deleteReview } from '../api'
import type { Review } from '../types'

interface Props {
  review: Review
  /**
   * Düzenle/sil/upvote ile review state mutate olduğunda parent listenin
   * yenilenmesi için opsiyonel callback. Verilmezse component sadece
   * lokal state günceller.
   */
  onChanged?: () => void
}

const DIFFICULTY_LABELS: Record<number, string> = {
  1: 'Çok kolay', 2: 'Kolay', 3: 'Orta', 4: 'Zor', 5: 'Çok zor',
}

function extractErrorMessage(err: any): string {
  const detail = err?.response?.data?.detail
  if (!detail) return 'Bir hata oluştu.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    const msg: string = typeof first === 'string' ? first : (first?.msg ?? '')
    return msg.replace(/^Value error,?\s*/i, '') || 'İstek doğrulanamadı.'
  }
  return 'Bir hata oluştu.'
}

export default function ReviewCard({ review, onChanged }: Props) {
  const [current, setCurrent] = useState<Review>(review)
  const [upvotes, setUpvotes] = useState(review.upvote_count)
  const [upvoted, setUpvoted] = useState(false)
  const [downvotes, setDownvotes] = useState(review.downvote_count)
  const [downvoted, setDownvoted] = useState(false)
  const [editing, setEditing] = useState(false)
  const [deleted, setDeleted] = useState(false)

  // Edit form state — sadece editing=true iken kullanılır
  const [editRating, setEditRating] = useState(review.rating)
  const [editDifficulty, setEditDifficulty] = useState<number>(review.difficulty ?? 0)
  const [editComment, setEditComment] = useState<string>(review.comment ?? '')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const handleUpvote = async () => {
    try {
      const res = await toggleUpvote(current.id)
      setUpvotes(res.upvote_count)
      setUpvoted(res.upvoted)
      if (res.upvoted) { setDownvoted(false); setDownvotes(res.downvote_count) }
    } catch {}
  }

  const handleDownvote = async () => {
    try {
      const res = await toggleDownvote(current.id)
      setDownvotes(res.downvote_count)
      setDownvoted(res.downvoted)
      if (res.downvoted) { setUpvoted(false); setUpvotes(res.upvote_count) }
    } catch {}
  }

  const startEdit = () => {
    setEditRating(current.rating)
    setEditDifficulty(current.difficulty ?? 0)
    setEditComment(current.comment ?? '')
    setErr('')
    setEditing(true)
  }

  const cancelEdit = () => { setEditing(false); setErr('') }

  const saveEdit = async () => {
    if (editRating < 1 || editRating > 5) { setErr('Puan 1-5 arasında olmalı.'); return }
    if (current.course_id && editDifficulty === 0) { setErr('Lütfen zorluk seçin.'); return }
    setBusy(true); setErr('')
    try {
      const updated = await updateReview(current.id, {
        rating: editRating,
        difficulty: current.course_id ? editDifficulty : null,
        workload_hours: null,
        comment: editComment.trim() === '' ? null : editComment.trim(),
      })
      setCurrent(updated)
      setUpvotes(updated.upvote_count)
      setEditing(false)
      onChanged?.()
    } catch (e) {
      setErr(extractErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Bu yorumu silmek istediğine emin misin? Geri alınamaz.')) return
    setBusy(true); setErr('')
    try {
      await deleteReview(current.id)
      setDeleted(true)
      onChanged?.()
    } catch (e) {
      setErr(extractErrorMessage(e))
      setBusy(false)
    }
  }

  if (deleted) return null

  const date = new Date(current.created_at).toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' })
  const wasEdited = current.updated_at && current.created_at && current.updated_at !== current.created_at

  return (
    <div className="bg-white rounded-xl border border-[#dde3ec] p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-[#003087]/10 text-[#003087] flex items-center justify-center font-semibold text-sm">
            {(current.first_name?.[0] ?? '?').toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-gray-800 flex items-center gap-2">
              {current.first_name && current.last_name
                ? `${current.first_name} ${current.last_name[0].toUpperCase()}***`
                : <span className="italic text-gray-400">Anonim</span>
              }
              {current.is_owner && (
                <span className="text-[10px] font-semibold text-[#003087] bg-[#003087]/10 px-1.5 py-0.5 rounded">
                  Sen
                </span>
              )}
            </p>
            <p className="text-xs text-gray-400">
              {date}
              {wasEdited && <span className="ml-1 italic">(düzenlendi)</span>}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {current.semester && (
            <span className="text-[11px] font-medium text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
              {current.semester}
            </span>
          )}
          {/* is_verified_pairing rozeti — false ise uyarı */}
          {current.is_verified_pairing === false && (
            <span
              title="Bu hoca/ders/dönem kombinasyonu SUIS verilerinde bulunamadı."
              className="text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded"
            >
              ⚠ Doğrulanmamış
            </span>
          )}
          {!editing && <StarRating value={current.rating} size="sm" />}
        </div>
      </div>

      {/* ── Editing modu ─────────────────────────────────────────────────── */}
      {editing ? (
        <div className="mt-4 space-y-3 border-t border-[#dde3ec] pt-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Puan</label>
            <StarRating value={editRating} size="md" interactive onChange={setEditRating} />
          </div>

          {current.course_id && (
            <>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-gray-700">Zorluk *</label>
                  <span className="text-xs text-gray-500">
                    {editDifficulty > 0 ? DIFFICULTY_LABELS[editDifficulty] : 'Seçin'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  {[1, 2, 3, 4, 5].map(n => {
                    const active = editDifficulty >= n
                    return (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setEditDifficulty(n)}
                        className={`h-7 w-7 rounded-full border text-xs font-semibold transition-colors ${
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
            </>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Yorum</label>
            <textarea
              value={editComment}
              onChange={e => setEditComment(e.target.value)}
              rows={3}
              maxLength={2000}
              className="w-full border border-[#dde3ec] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#003087] resize-none"
            />
          </div>

          {err && <p className="text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{err}</p>}

          <div className="flex items-center gap-2">
            <button
              type="button" disabled={busy} onClick={saveEdit}
              className="bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              {busy ? 'Kaydediliyor...' : 'Kaydet'}
            </button>
            <button
              type="button" disabled={busy} onClick={cancelEdit}
              className="border border-[#dde3ec] text-gray-700 hover:bg-gray-50 disabled:opacity-50 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Vazgeç
            </button>
          </div>
        </div>
      ) : (
        <>
          {current.comment && (
            <p className="mt-3 text-sm text-gray-700 leading-relaxed whitespace-pre-line">{current.comment}</p>
          )}

          {current.difficulty != null && current.course_id && (
            <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
              {current.difficulty != null && (
                <span>Zorluk: <span className="font-medium text-gray-700">{DIFFICULTY_LABELS[current.difficulty] ?? current.difficulty}</span></span>
              )}
            </div>
          )}

          {err && <p className="mt-3 text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{err}</p>}

          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={handleUpvote}
              title="Faydalı"
              className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors
                ${upvoted
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-100 hover:bg-emerald-50 text-gray-600 hover:text-emerald-700'}`}
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 20h2c.55 0 1-.45 1-1v-9c0-.55-.45-1-1-1H2v11zm19.83-7.12c.11-.25.17-.52.17-.8V11c0-1.1-.9-2-2-2h-5.5l.92-4.65c.05-.22.02-.46-.08-.66-.23-.45-.52-.86-.88-1.22L14 2 7.59 8.41C7.21 8.79 7 9.3 7 9.83V19c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05z"/>
              </svg>
              <span className="font-medium">Faydalı</span>
              {upvotes > 0 && <span className="text-xs opacity-75">({upvotes})</span>}
            </button>
            <button
              onClick={handleDownvote}
              title="Faydasız"
              className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors
                ${downvoted
                  ? 'bg-red-500 text-white'
                  : 'bg-gray-100 hover:bg-red-50 text-gray-600 hover:text-red-600'}`}
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22 4h-2c-.55 0-1 .45-1 1v9c0 .55.45 1 1 1h2V4zM2.17 11.12c-.11.25-.17.52-.17.8V13c0 1.1.9 2 2 2h5.5l-.92 4.65c-.05.22-.02.46.08.66.23.45.52.86.88 1.22L10 22l6.41-6.41c.38-.38.59-.89.59-1.42V5c0-1.1-.9-2-2-2H6c-.83 0-1.54.5-1.84 1.22L2.17 11.12z"/>
              </svg>
              <span className="font-medium">Faydasız</span>
              {downvotes > 0 && <span className="text-xs opacity-75">({downvotes})</span>}
            </button>

            {/* Owner için düzenle/sil — sadece backend is_owner=true dediyse */}
            {current.is_owner && (
              <>
                <button
                  onClick={startEdit}
                  className="text-sm px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-[#003087]/10 text-gray-600 hover:text-[#003087] transition-colors"
                >
                  Düzenle
                </button>
                <button
                  onClick={handleDelete}
                  disabled={busy}
                  className="text-sm px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-red-50 text-gray-600 hover:text-[#E3001B] disabled:opacity-50 transition-colors"
                >
                  Sil
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
