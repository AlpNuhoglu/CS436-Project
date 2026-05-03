import { Link, useLocation } from 'react-router-dom'
import type { Course } from '../types'
import { FACULTY_MAP } from '../types'

interface Props {
  course: Course
}

export default function CourseCard({ course }: Props) {
  const location = useLocation()
  const facultyMeta = course.faculty ? FACULTY_MAP[course.faculty] : null
  const diff = course.difficulty ?? 0

  return (
    <Link
      to={`/courses/${course.id}`}
      state={{ back: `${location.pathname}${location.search}` }}
      className="group block bg-white border border-line rounded-[22px] p-5 transition-all hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_rgba(11,18,32,.18),0_2px_6px_rgba(11,18,32,.06)]"
    >
      <div className="flex items-center justify-between mb-2.5">
        {facultyMeta ? (
          <span className={`${facultyMeta.badgeBg} ${facultyMeta.badgeText} mono text-[11px] tracking-wide font-bold px-2.5 py-1 rounded-full`}>
            {facultyMeta.name}
          </span>
        ) : (
          <span className="text-[11px] text-navy-300">—</span>
        )}
        {course.average_rating != null ? (
          <span className="inline-flex items-center gap-1 text-amber text-xs">
            <span className="text-amber">★</span>
            <b className="text-navy-900">{course.average_rating.toFixed(1)}</b>
            {course.review_count != null && course.review_count > 0 && (
              <span className="text-navy-300 font-medium">· {course.review_count}</span>
            )}
          </span>
        ) : (
          <span className="text-[11px] text-navy-300">Yorumsuz</span>
        )}
      </div>

      <div className="serif font-bold text-[24px] text-navy-900 tracking-tight leading-none">
        {course.code}
      </div>
      <div className="text-[14px] text-navy-700 mt-1 leading-snug line-clamp-2">
        {course.name}
      </div>

      <div className="flex items-center justify-between mt-4 text-xs text-navy-300">
        <span className="truncate max-w-[60%]">{course.department ?? '—'}</span>
        <span className="flex items-center gap-1" title="Zorluk seviyesi">
          {[1, 2, 3, 4, 5].map(n => (
            <span
              key={n}
              className={`w-1.5 h-1.5 rounded-full ${n <= diff ? 'bg-red-500' : 'bg-mist'}`}
            />
          ))}
        </span>
      </div>

      <div className="flex items-center justify-between mt-2 text-[12px] text-navy-500">
        <span>
          {course.workload_hours != null ? (
            <>Haftalık <b className="text-navy-900">~{course.workload_hours}</b> saat</>
          ) : (
            <span className="text-navy-300">—</span>
          )}
        </span>
        <span className="inline-flex items-center gap-1 text-navy-300 group-hover:text-red-500 transition-colors">
          Detay
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M5 12h14m-6-6 6 6-6 6"/>
          </svg>
        </span>
      </div>
    </Link>
  )
}
