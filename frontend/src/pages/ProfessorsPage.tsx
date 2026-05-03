import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getAllProfessors, getSemesters } from '../api'
import type { Professor, Faculty, SemesterOption } from '../types'
import { FACULTIES } from '../types'
import ProfessorCard from '../components/ProfessorCard'
import { normalizeSearch } from '../hooks/normalizeSearch'

type SortKey = 'name' | 'rating'

export default function ProfessorsPage() {
  const [professors, setProfessors] = useState<Professor[]>([])
  const [semesters, setSemesters] = useState<SemesterOption[]>([])
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const searchFaculty = (searchParams.get('faculty') as Faculty | null) ?? null
  const searchSemester = searchParams.get('semester') ?? ''
  const searchQuery = searchParams.get('q') ?? ''
  const [faculty, setFaculty] = useState<Faculty | 'ALL'>(searchFaculty ?? 'ALL')
  const [semester, setSemester] = useState(searchSemester)
  const [q, setQ] = useState(searchQuery)
  const [sortKey, setSortKey] = useState<SortKey>('name')

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

    getAllProfessors(semester ? { semester } : {})
      .then((data) => {
        if (!cancelled) setProfessors(data)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [semester])

  useEffect(() => {
    const next: Record<string, string> = {}
    if (faculty !== 'ALL') next.faculty = faculty
    if (semester) next.semester = semester
    if (q) next.q = q
    setSearchParams(next, { replace: true })
  }, [faculty, semester, q, setSearchParams])

  const filtered = useMemo(() => {
    let out = professors
    if (faculty !== 'ALL') out = out.filter(p => p.faculty === faculty)
    // Üst search bar gibi: case ve space duyarsız.
    // "Kamer Kaya" / "kamerkaya" / "KAMER KAYA" hepsi aynı sonucu verir.
    const needle = normalizeSearch(q)
    if (needle) {
      out = out.filter(p =>
        normalizeSearch(p.name).includes(needle) ||
        normalizeSearch(p.department).includes(needle),
      )
    }
    out = [...out].sort((a, b) => {
      if (sortKey === 'rating') {
        return (b.average_rating ?? 0) - (a.average_rating ?? 0)
      }
      return a.name.localeCompare(b.name, 'tr')
    })
    return out
  }, [professors, faculty, q, sortKey])

  const facultyCounts = useMemo(() => {
    const m: Record<string, number> = { ALL: professors.length }
    for (const f of FACULTIES) m[f.code] = 0
    professors.forEach(p => { if (p.faculty) m[p.faculty]++ })
    return m
  }, [professors])

  const activeFacultyLabel =
    faculty === 'ALL' ? null : FACULTIES.find(f => f.code === faculty)?.full

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <div className="text-[12px] tracking-[0.22em] uppercase text-red-500 font-bold">Hocalar</div>
        <h1 className="serif font-semibold text-navy-900 text-[clamp(32px,4vw,52px)] tracking-[-0.02em] mt-2 leading-[1.05] max-w-[22ch]">
          Sabancı'nın akademisyen kadrosu, tek sayfada.
        </h1>
        <p className="text-navy-500 mt-2.5 max-w-[56ch] text-[15px] leading-relaxed">
          <b className="text-navy-900">{filtered.length}</b> hoca listeleniyor · Anlatım, adillik ve
          erişilebilirlik üzerine öğrenci geri bildirimlerinden oluşturulan puanlar.
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
            placeholder="İsim veya bölüm ara…"
            className="flex-1 bg-transparent outline-none text-[13px] placeholder:text-navy-300"
          />
        </div>

        {/* Faculty segmented */}
        <div className="inline-flex bg-white border border-line rounded-full p-1">
          <FacultyTab current={faculty} code="ALL" label={`Tümü (${facultyCounts.ALL})`} onSelect={setFaculty} />
          {FACULTIES.map(f => (
            <FacultyTab key={f.code} current={faculty} code={f.code} label={`${f.name} (${facultyCounts[f.code] ?? 0})`} onSelect={setFaculty} />
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

        <div className="inline-flex bg-white border border-line rounded-full p-1">
          <SortTab current={sortKey} key_={'name'} label="İsim" onSelect={setSortKey} />
          <SortTab current={sortKey} key_={'rating'} label="Puan" onSelect={setSortKey} />
        </div>
      </div>

      <div className="flex items-center justify-between mt-6 mb-4">
        <div className="text-[14px] text-navy-500">
          <b className="text-navy-900">{filtered.length}</b> sonuç
          {activeFacultyLabel && <> · <em className="not-italic text-red-500 font-semibold">{activeFacultyLabel}</em></>}
          {semester && <> · <span className="text-navy-900 font-semibold">{semester}</span></>}
        </div>
        {(faculty !== 'ALL' || semester || q) && (
          <button
            onClick={() => { setFaculty('ALL'); setSemester(''); setQ('') }}
            className="text-[13px] text-navy-500 hover:text-red-500 font-semibold"
          >
            Filtreleri temizle ✕
          </button>
        )}
      </div>

      {/* Grid */}
      <div>
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1,2,3,4,5,6].map(i => <div key={i} className="h-[220px] rounded-[22px] bg-white border border-line animate-pulse" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white border border-line rounded-[22px] p-12 text-center text-navy-300">
            Bu filtrelerle sonuç bulunamadı.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map(p => <ProfessorCard key={p.id} professor={p} />)}
          </div>
        )}
      </div>
    </div>
  )
}

function FacultyTab({
  current, code, label, onSelect,
}: {
  current: Faculty | 'ALL'
  code: Faculty | 'ALL'
  label: string
  onSelect: (v: Faculty | 'ALL') => void
}) {
  const active = current === code
  return (
    <button
      onClick={() => onSelect(code)}
      className={`px-3.5 py-1.5 rounded-full text-[13px] font-semibold ${
        active ? 'bg-navy-900 text-white' : 'text-navy-500 hover:text-navy-900'
      }`}
    >
      {label}
    </button>
  )
}

function SortTab({
  current, key_, label, onSelect,
}: {
  current: SortKey
  key_: SortKey
  label: string
  onSelect: (v: SortKey) => void
}) {
  const active = current === key_
  return (
    <button
      onClick={() => onSelect(key_)}
      className={`px-3.5 py-1.5 rounded-full text-[13px] font-semibold ${
        active ? 'bg-navy-900 text-white' : 'text-navy-500 hover:text-navy-900'
      }`}
    >
      {label}
    </button>
  )
}
