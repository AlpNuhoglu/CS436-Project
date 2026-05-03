import { Link, useLocation } from 'react-router-dom'
import type { Professor } from '../types'
import { FACULTY_MAP } from '../types'

interface Props {
  professor: Professor
  /** Küçük dekoratif sparkline (seed=random gibi görünmesi için id kullanır) */
  showSparkline?: boolean
}

const AVATAR_GRADIENTS = [
  'from-navy-500 to-navy-700',
  'from-[#7C3AED] to-[#3B1A6E]',
  'from-red-500 to-[#7a0013]',
  'from-[#0EA5A6] to-[#064E4E]',
  'from-[#F59E0B] to-[#7B3F00]',
  'from-mint to-[#065F46]',
]

export default function ProfessorCard({ professor, showSparkline = true }: Props) {
  const location = useLocation()
  const initials = professor.name.split(' ').map(n => n[0]).slice(0, 2).join('')
  const grad = AVATAR_GRADIENTS[professor.id % AVATAR_GRADIENTS.length]
  const facultyMeta = professor.faculty ? FACULTY_MAP[professor.faculty] : null

  // Deterministic "sparkline" heights based on id — pure decoration
  const bars = Array.from({ length: 12 }, (_, i) => {
    const base = ((professor.id * 13 + i * 7) % 60) + 30
    return base
  })

  return (
    <Link
      to={`/professors/${professor.id}`}
      state={{ back: `${location.pathname}${location.search}` }}
      className="group relative block bg-white border border-line rounded-[22px] p-5 transition-all hover:-translate-y-1 hover:shadow-[0_30px_60px_-24px_rgba(11,18,32,.35)] hover:border-transparent overflow-hidden"
    >
      <div className="absolute top-0 right-0 w-[120px] h-[120px] bg-[radial-gradient(circle_at_top_right,rgba(0,48,135,.08),transparent_60%)] pointer-events-none" />

      <div className="flex items-center gap-3.5">
        <div
          className={`w-14 h-14 rounded-[18px] grid place-items-center text-white font-bold serif text-lg bg-gradient-to-br ${grad} shadow-[inset_0_0_0_2px_rgba(255,255,255,0.08)]`}
        >
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-navy-900 truncate">{professor.name}</div>
          <div className="text-xs text-navy-300 mt-0.5 truncate">
            {professor.title ?? '—'}{professor.department ? ` · ${professor.department}` : ''}
          </div>
        </div>
        <div className="flex flex-col items-end gap-0.5 shrink-0">
          <div className="serif font-bold text-[22px] text-navy-900 leading-none">
            {professor.average_rating != null ? professor.average_rating.toFixed(1) : '—'}
          </div>
          <div className="text-[11px] text-navy-300">puan</div>
        </div>
      </div>

      {showSparkline && (
        <>
          <div className="h-px bg-line my-4" />
          <div className="flex items-end gap-[3px] h-7">
            {bars.map((h, i) => (
              <span
                key={i}
                style={{ height: `${h}%` }}
                className={`block w-[6px] rounded-sm ${
                  h > 80 ? 'bg-red-500' : h > 55 ? 'bg-navy-500' : 'bg-navy-100'
                }`}
              />
            ))}
          </div>
        </>
      )}

      <div className="flex flex-wrap gap-1.5 mt-4">
        {facultyMeta && (
          <span className="text-[11px] px-2.5 py-1 rounded-full bg-navy-100 text-navy-700 font-semibold tracking-wide">
            {facultyMeta.name}
          </span>
        )}
        {professor.department && (
          <span className="text-[11px] px-2.5 py-1 rounded-full bg-cream-2 text-navy-700 font-medium truncate max-w-[180px]">
            {professor.department}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between mt-4">
        <span className="text-[13px] text-navy-300">
          {professor.review_count != null && professor.review_count > 0
            ? `${professor.review_count} yorum`
            : 'Henüz yorum yok'}
        </span>
        <span className="w-8 h-8 rounded-full bg-cream-2 grid place-items-center text-navy-900 group-hover:bg-red-500 group-hover:text-white transition-colors">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M5 12h14m-6-6 6 6-6 6"/>
          </svg>
        </span>
      </div>
    </Link>
  )
}
