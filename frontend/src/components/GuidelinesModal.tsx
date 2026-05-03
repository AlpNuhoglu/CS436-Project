import { useEffect, useRef, useState } from 'react'
import GuidelinesContent from './GuidelinesContent'

interface Props {
  open: boolean
  onClose: () => void
  onAccept: () => void
}

/**
 * Kayıt formundan açılan, "okumadan kabul edemezsin" modal'i.
 *
 * Kullanıcı kuralları okuduğunu varsayabilmemiz için scroll konumunu izleriz —
 * "Kabul ediyorum" butonu içerik sonuna kaydırılana kadar pasif kalır.
 *
 * Klavye erişilebilirliği:
 *   - ESC kapatır.
 *   - Arka planda body scroll kilitlenir.
 */
export default function GuidelinesModal({ open, onClose, onAccept }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [reachedEnd, setReachedEnd] = useState(false)

  // ESC kısayolu + body scroll kilidi
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  // Modal her açıldığında scroll konumunu sıfırla
  useEffect(() => {
    if (!open) return
    setReachedEnd(false)
    // bir tick sonra scroll'u en başa al — DOM hazır olduktan sonra
    requestAnimationFrame(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = 0
    })
  }, [open])

  // Edge-case: içerik konteynerden kısa ise (zaten "tabanda"yız) → hemen aktif et
  useEffect(() => {
    if (!open) return
    const el = scrollRef.current
    if (!el) return
    if (el.scrollHeight <= el.clientHeight + 4) {
      setReachedEnd(true)
    }
  }, [open])

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const distanceFromBottom = el.scrollHeight - (el.scrollTop + el.clientHeight)
    if (distanceFromBottom <= 24) setReachedEnd(true)
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guidelines-modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-[#0A1733]/65 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal kart */}
      <div className="relative w-full max-w-2xl max-h-[88vh] bg-cream rounded-2xl shadow-2xl border border-[#dde3ec] flex flex-col overflow-hidden">
        {/* Başlık */}
        <div className="flex items-start justify-between gap-4 px-6 py-4 border-b border-[#dde3ec] bg-white">
          <div>
            <h2
              id="guidelines-modal-title"
              className="serif text-2xl text-navy-900 leading-tight"
            >
              Topluluk Kuralları
            </h2>
            <p className="text-xs text-navy-500 mt-1">
              Kayıt için okuyup onaylaman gerekiyor — sayfayı sonuna kadar kaydır.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="shrink-0 w-8 h-8 rounded-full hover:bg-navy-100/60 grid place-items-center text-navy-500 hover:text-navy-900 transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* İçerik (kaydırılabilir) */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="overflow-y-auto px-6 py-5 flex-1 bg-cream"
        >
          <GuidelinesContent />

          {/* Sona ulaştın işareti */}
          <div
            className={`mt-6 flex items-center justify-center gap-2 text-xs transition-colors ${
              reachedEnd ? 'text-emerald-700' : 'text-navy-300'
            }`}
          >
            {reachedEnd ? (
              <>
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                  <path d="M5 13l4 4L19 7" />
                </svg>
                Sona ulaştın — şimdi kabul edebilirsin.
              </>
            ) : (
              <>
                <svg className="w-4 h-4 animate-bounce" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                  <path d="M12 5v14m-6-6 6 6 6-6" />
                </svg>
                Devam etmek için kuralları sonuna kadar kaydır.
              </>
            )}
          </div>
        </div>

        {/* Footer aksiyonları */}
        <div className="flex items-center justify-end gap-2 px-6 py-3.5 border-t border-[#dde3ec] bg-white">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-full text-sm font-medium text-navy-700 hover:bg-navy-100/40 transition-colors"
          >
            İptal
          </button>
          <button
            type="button"
            onClick={onAccept}
            disabled={!reachedEnd}
            className="px-5 py-2 rounded-full text-sm font-semibold bg-[#003087] hover:bg-[#002060] disabled:bg-navy-300 disabled:cursor-not-allowed text-white transition-colors"
            title={reachedEnd ? 'Kabul et' : 'Önce kuralları sonuna kadar kaydır'}
          >
            Okudum, kabul ediyorum
          </button>
        </div>
      </div>
    </div>
  )
}
