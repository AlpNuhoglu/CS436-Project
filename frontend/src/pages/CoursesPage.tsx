import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getAllCourses, getSemesters } from '../api'
import type { Course, Faculty, SemesterOption } from '../types'
import { FACULTIES } from '../types'
import CourseCard from '../components/CourseCard'
import { normalizeSearch } from '../hooks/normalizeSearch'

type SortKey = 'code' | 'difficulty' | 'workload'
type WorkloadFilter = 'ALL' | 'light' | 'mid' | 'heavy'

function normalizedWords(value: string) {
  return value
    .split(/[^\p{L}\p{N}]+/u)
    .map(normalizeSearch)
    .filter(Boolean)
}

function matchesCourseSearch(course: Course, needle: string) {
  const normalizedCode = normalizeSearch(course.code)
  const normalizedName = normalizeSearch(course.name)

  return (
    normalizedCode.startsWith(needle) ||
    normalizedCode.includes(needle) ||
    normalizedName.includes(needle) ||
    normalizedWords(course.name).some(word => word.startsWith(needle))
  )
}

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([])
  const [semesters, setSemesters] = useState<SemesterOption[]>([])
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()

  const searchFaculty = (searchParams.get('faculty') as Faculty | null) ?? null
  const searchSemester = searchParams.get('semester') ?? ''
  const searchQuery = searchParams.get('q') ?? ''
  const [faculty, setFaculty] = useState<Faculty | 'ALL'>(searchFaculty ?? 'ALL')
  const [semester, setSemester] = useState(searchSemester)
  const [q, setQ] = useState(searchQuery)
  const [difficulty, setDifficulty] = useState<number | 'ALL'>('ALL')
  const [workload, setWorkload] = useState<WorkloadFilter>('ALL')
  const [sortKey, setSortKey] = useState<SortKey>('code')

  useEffect(() => {
    setFaculty(searchFaculty ?? 'ALL')
    setSemester(searchSemester)
    setQ(searchQuery)
  }, [searchFaculty, searchSemester, searchQuery])

  useEffect(() => {
    let cancelled = false
    getSemesters().then((data) => {
      if (!cancelled) setSemesters(data)
    })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    getAllCourses(semester ? { semester } : {})
      .then((data) => {
        if (!cancelled) setCourses(data)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [semester])

  // Keep the ?faculty query param in sync so links from the home page stick
  useEffect(() => {
    const next: Record<string, string> = {}
    if (faculty !== 'ALL') next.faculty = faculty
    if (semester) next.semester = semester
    if (q) next.q = q
    setSearchParams(next, { replace: true })
  }, [faculty, semester, q, setSearchParams])

  const filtered = useMemo(() => {
    let out = courses
    if (faculty !== 'ALL') out = out.filter(c => c.faculty === faculty)
    if (difficulty !== 'ALL') out = out.filter(c => c.difficulty === difficulty)
    if (workload !== 'ALL') {
      out = out.filter(c => {
        const w = c.workload_hours ?? 0
        if (workload === 'light') return w <= 7
        if (workload === 'mid')   return w > 7 && w <= 11
        return w > 11
      })
    }
    // Üst search bar gibi: case ve space duyarsız.
    // "CS 4 36" → "cs436", DB'deki "CS436" da → "cs436" → eşleşir.
    const needle = normalizeSearch(q)
    if (needle) {
      const alphabeticQuery = /^\p{L}+$/u.test(needle)

      if (alphabeticQuery) {
        const codePrefixMatches = out.filter(c => normalizeSearch(c.code).startsWith(needle))
        out = codePrefixMatches.length > 0
          ? codePrefixMatches
          : out.filter(c => matchesCourseSearch(c, needle))
      } else {
        out = out.filter(c => matchesCourseSearch(c, needle))
      }
    }
    out = [...out].sort((a, b) => {
      if (sortKey === 'difficulty') return (b.difficulty ?? 0) - (a.difficulty ?? 0)
      if (sortKey === 'workload')   return (b.workload_hours ?? 0) - (a.workload_hours ?? 0)
      return a.code.localeCompare(b.code)
    })
    return out
  }, [courses, faculty, difficulty, workload, q, sortKey])

  const facultyCounts = useMemo(() => {
    const m: Record<string, number> = { ALL: courses.length }
    for (const f of FACULTIES) m[f.code] = 0
    courses.forEach(c => { if (c.faculty) m[c.faculty]++ })
    return m
  }, [courses])

  const activeFacultyLabel =
    faculty === 'ALL' ? null : FACULTIES.find(f => f.code === faculty)?.full

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <div className="text-[12px] tracking-[0.22em] uppercase text-red-500 font-bold">📚 Katalog</div>
        <h1 className="serif font-semibold text-navy-900 text-[clamp(32px,4vw,52px)] tracking-[-0.02em] mt-2 leading-[1.05] max-w-[22ch]">
          {courses.length ? `${courses.length} ders — doğru olanı bul.` : 'Dersler yükleniyor…'}
        </h1>
        <p className="text-navy-500 mt-2.5 max-w-[56ch] text-[15px] leading-relaxed">
          Fakülte, zorluk ve haftalık iş yüküne göre filtrele. Her ders için öğrenci puanları,
          haftalık ortalama iş yükü ve dersi veren hocalar.
        </p>
      </div>

      {/* Filter bar */}
      <div className="bg-white border border-line rounded-[20px] p-3.5 flex flex-wrap items-center gap-2.5 shadow-[0_1px_2px_rgba(11,18,32,.06)]">
        <div className="flex-1 min-w-[240px] flex items-center gap-2.5 px-3.5 py-2 border border-line rounded-full">
          <svg className="w-4 h-4 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
          </svg>
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Ders kodu veya içeriğe göre ara…"
            className="flex-1 bg-transparent outline-none text-[13px] placeholder:text-navy-300"
          />
        </div>

        {/* Faculty */}
        <div className="inline-flex bg-white border border-line rounded-full p-1">
          <Seg current={faculty} value="ALL" label={`Tümü (${facultyCounts.ALL})`} onSelect={setFaculty} />
          {FACULTIES.map(f => (
            <Seg key={f.code} current={faculty} value={f.code} label={`${f.name} (${facultyCounts[f.code] ?? 0})`} onSelect={setFaculty} />
          ))}
        </div>

        <select
          value={semester}
          onChange={e => setSemester(e.target.value)}
          className="min-w-[220px] bg-white border border-line rounded-full px-4 py-2 text-[13px] text-navy-700 outline-none"
        >
          <option value="">Tüm dönemler</option>
          {semesters.map(s => (
            <option key={s.semester} value={s.semester}>
              {s.semester} ({s.review_count})
            </option>
          ))}
        </select>
      </div>

      {/* Secondary filters */}
      <div className="mt-3 flex flex-wrap items-center gap-2.5">
        <span className="text-[12px] tracking-[0.12em] uppercase text-navy-300 font-semibold mr-1">Zorluk</span>
        <div className="inline-flex bg-white border border-line rounded-full p-1">
          <Seg current={difficulty} value="ALL" label="Tümü" onSelect={setDifficulty} />
          {[1,2,3,4,5].map(n => (
            <Seg key={n} current={difficulty} value={n} label={<DiffDots n={n} />} onSelect={setDifficulty} />
          ))}
        </div>

        <span className="text-[12px] tracking-[0.12em] uppercase text-navy-300 font-semibold mx-1">Yük</span>
        <div className="inline-flex bg-white border border-line rounded-full p-1">
          <Seg current={workload} value="ALL"   label="Tümü"   onSelect={setWorkload} />
          <Seg current={workload} value="light" label="Hafif"  onSelect={setWorkload} />
          <Seg current={workload} value="mid"   label="Orta"   onSelect={setWorkload} />
          <Seg current={workload} value="heavy" label="Yoğun"  onSelect={setWorkload} />
        </div>

        <span className="text-[12px] tracking-[0.12em] uppercase text-navy-300 font-semibold mx-1 ml-auto">Sırala</span>
        <div className="inline-flex bg-white border border-line rounded-full p-1">
          <Seg current={sortKey} value="code"       label="Kod"     onSelect={setSortKey} />
          <Seg current={sortKey} value="difficulty" label="Zorluk"  onSelect={setSortKey} />
          <Seg current={sortKey} value="workload"   label="Yük"     onSelect={setSortKey} />
        </div>
      </div>

      {/* Result meta */}
      <div className="flex items-center justify-between mt-6 mb-4">
        <div className="text-[14px] text-navy-500">
          <b className="text-navy-900">{filtered.length}</b> sonuç
          {activeFacultyLabel && <> · <em className="not-italic text-red-500 font-semibold">{activeFacultyLabel}</em></>}
          {semester && <> · <span className="text-navy-900 font-semibold">{semester}</span></>}
        </div>
        {(faculty !== 'ALL' || difficulty !== 'ALL' || workload !== 'ALL' || semester || q) && (
          <button
            onClick={() => {
              setFaculty('ALL')
              setDifficulty('ALL')
              setWorkload('ALL')
              setSemester('')
              setQ('')
            }}
            className="text-[13px] text-navy-500 hover:text-red-500 font-semibold"
          >
            Filtreleri temizle ✕
          </button>
        )}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1,2,3,4,5,6,7,8,9].map(i => <div key={i} className="h-[180px] rounded-[22px] bg-white border border-line animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-line rounded-[22px] p-12 text-center text-navy-300">
          Bu filtrelerle sonuç bulunamadı.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map(c => <CourseCard key={c.id} course={c} />)}
        </div>
      )}
    </div>
  )
}

function Seg<T extends string | number>({
  current, value, label, onSelect,
}: {
  current: T
  value: T
  label: React.ReactNode
  onSelect: (v: T) => void
}) {
  const active = current === value
  return (
    <button
      onClick={() => onSelect(value)}
      className={`px-3 py-1.5 rounded-full text-[13px] font-semibold transition-colors ${
        active ? 'bg-navy-900 text-white' : 'text-navy-500 hover:text-navy-900'
      }`}
    >
      {label}
    </button>
  )
}

function DiffDots({ n }: { n: number }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      {[1,2,3,4,5].map(i => (
        <span key={i} className={`w-1.5 h-1.5 rounded-full ${i <= n ? 'bg-red-500' : 'bg-mist'}`} />
      ))}
    </span>
  )
}
