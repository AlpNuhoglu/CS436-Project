import { useEffect, useMemo, useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHomeStats } from '../api'
import type { HomeStats } from '../types'
import { FACULTIES, FACULTY_MAP } from '../types'
import ProfessorCard from '../components/ProfessorCard'
import CourseCard from '../components/CourseCard'

// ── Yardımcılar ────────────────────────────────────────────────────────────

function initialsOf(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .map(p => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

function formatCount(n: number) {
  if (n >= 10000) return `${(n / 1000).toFixed(1)}k`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return n.toString()
}

function timeAgoTr(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'az önce'
  if (mins < 60) return `${mins} dk önce`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} sa önce`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days} gün önce`
  const wks = Math.floor(days / 7)
  if (wks < 5) return `${wks} hafta önce`
  const months = Math.floor(days / 30)
  return `${months} ay önce`
}

// ── Disclaimer banner ──────────────────────────────────────────────────────

const DISCLAIMER_KEY = 'df_disclaimer_dismissed'

function DisclaimerBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(DISCLAIMER_KEY)) setVisible(true)
  }, [])

  const dismiss = useCallback(() => {
    localStorage.setItem(DISCLAIMER_KEY, '1')
    setVisible(false)
  }, [])

  if (!visible) return null

  return (
    <div className="fixed bottom-5 right-5 z-50 w-[340px] bg-white rounded-2xl border border-[#dde3ec] shadow-[0_8px_32px_-8px_rgba(10,23,51,0.18)] p-5 animate-[fadeInUp_.25s_ease]">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
            <svg className="w-4 h-4 text-amber-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <span className="text-[13px] font-semibold text-navy-900">Bir hatırlatma</span>
        </div>
        <button
          onClick={dismiss}
          className="text-gray-400 hover:text-gray-600 transition-colors shrink-0 -mt-0.5"
          aria-label="Kapat"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <p className="text-[13px] text-navy-500 leading-relaxed">
        Platformdaki her yorum, o öğrencinin kişisel deneyimini yansıtır. Birden fazla yorumu okuyarak kendi değerlendirmeni yapmanı tavsiye ederiz.
      </p>
      <button
        onClick={dismiss}
        className="mt-4 w-full bg-navy-900 hover:bg-navy-700 text-white text-[13px] font-semibold py-2 rounded-xl transition-colors"
      >
        Tamam, anladım
      </button>
    </div>
  )
}


// ── HomePage ───────────────────────────────────────────────────────────────

export default function HomePage() {
  const [stats, setStats] = useState<HomeStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getHomeStats()
      .then(setStats)
      .finally(() => setLoading(false))
  }, [])

  const facultyStats = useMemo(() => {
    const m: Record<string, { profs: number; courses: number }> = {}
    for (const f of FACULTIES) m[f.code] = { profs: 0, courses: 0 }
    if (!stats) return m
    stats.top_professors.forEach(p => { if (p.faculty && m[p.faculty]) m[p.faculty].profs++ })
    stats.top_courses.forEach(c => { if (c.faculty && m[c.faculty]) m[c.faculty].courses++ })
    return m
  }, [stats])

  const summary = stats?.summary
  const trending = stats?.trending_course
  const featured = stats?.featured_professor
  const latest = stats?.latest_review

  return (
    <div>
      <DisclaimerBanner />
      {/* ═══════════════ HERO ═══════════════ */}
      <section
        className="relative overflow-hidden text-white px-6 pt-14 pb-20 rounded-b-[36px] grain"
        style={{
          backgroundImage:
            'radial-gradient(1200px 520px at 10% -10%, rgba(227,0,27,.16), transparent 60%), radial-gradient(900px 480px at 100% 10%, rgba(255,255,255,.10), transparent 60%), linear-gradient(180deg,#09122B 0%, #0F2047 60%, #14296A 100%)',
        }}
      >
        <div className="max-w-[1240px] mx-auto grid lg:grid-cols-[1.2fr_.9fr] gap-14 items-center relative z-10">
          <div>
            <h1 className="serif font-semibold leading-[1.02] text-[clamp(40px,6vw,76px)] tracking-[-0.025em]">
              Bir dersi almadan önce,
              <br />
              <em className="not-italic italic font-normal text-[#FFD99B] relative">
                gerçek deneyimleri
                <span className="absolute left-0 right-0 bottom-[.08em] h-[.12em] bg-gradient-to-r from-transparent via-[#FFD99B]/70 to-transparent" />
              </em>{' '}
              oku.
            </h1>

            <p className="mt-4 text-navy-200 text-[17px] leading-relaxed max-w-[52ch]">
              Sabancı Üniversitesi öğrencilerinin hocalar, dersler ve program yükü hakkında paylaştığı
              kaliteli yorumlar — tek yerde, şeffaf, anonim ve doğrulanmış.
            </p>

            {/* CTAs */}
            <div className="mt-7 flex items-center gap-3 flex-wrap">
              <Link
                to="/courses"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-red-500 text-white font-semibold hover:bg-red-600 shadow-[0_20px_40px_-16px_rgba(227,0,27,0.55)]"
              >
                Dersleri Keşfet
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                  <path d="M5 12h14m-6-6 6 6-6 6"/>
                </svg>
              </Link>
              <Link
                to="/professors"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-white/8 text-white border border-white/18 font-semibold hover:bg-white/15 backdrop-blur-sm"
              >
                Hocalara Göz At
              </Link>
            </div>

            {/* Trending row — DB'den canlı (en çok yorumlu dersler) */}
            <div className="mt-6">
              <div className="text-[11px] tracking-[0.18em] uppercase text-navy-300 font-semibold mb-2.5">
                🔥 Bu hafta en çok yorumlanan dersler
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {loading ? (
                  [1, 2, 3, 4, 5].map(i => (
                    <span key={i} className="inline-block w-[90px] h-8 rounded-full bg-white/5 border border-white/10 animate-pulse" />
                  ))
                ) : (stats?.popular_searches ?? []).length === 0 ? (
                  <span className="text-white/40 text-xs">Henüz yorum yok — ilk yorumu sen yaz!</span>
                ) : (
                  stats!.popular_searches.map((p, i) => (
                    <Link
                      key={`${p.kind}-${p.target_id}`}
                      to={p.kind === 'course' ? `/courses/${p.target_id}` : `/professors/${p.target_id}`}
                      className="inline-flex items-center gap-1.5 bg-white/5 text-white font-medium border border-white/10 px-3 py-1.5 rounded-full hover:bg-white/15 transition-colors text-[13px]"
                    >
                      <span className="text-red-400 text-[10px] mono font-bold">#{i + 1}</span>
                      {p.label}
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Floating cards stack — dinamik */}
          <div className="relative h-[520px] hidden lg:block">
            {/* Top: featured professor card */}
            {featured ? (
              <Link
                to={`/professors/${featured.id}`}
                className="absolute top-2.5 right-2.5 w-[320px] rounded-[20px] bg-gradient-to-b from-white to-cream text-navy-900 p-[18px] border border-white/60 shadow-[0_30px_60px_-24px_rgba(11,18,32,.35),0_10px_20px_-10px_rgba(11,18,32,.18)] hover:-translate-y-0.5 transition-transform"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-[54px] h-[54px] rounded-full grid place-items-center p-[4px]"
                    style={{ background: 'conic-gradient(from 210deg, #003087, #E3001B, #F6A623, #003087)' }}
                  >
                    <div className="w-full h-full rounded-full bg-white grid place-items-center font-bold text-navy-900">
                      {initialsOf(featured.name)}
                    </div>
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold truncate">
                      {featured.title ? `${featured.title} ` : ''}{featured.name}
                    </div>
                    <div className="text-[12px] text-navy-300 truncate">
                      {featured.department ?? 'Bölüm belirtilmemiş'}
                      {featured.faculty ? ` · ${featured.faculty}` : ''}
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-1.5 text-amber text-sm">
                  {featured.average_rating != null ? (
                    <>
                      {'★'.repeat(Math.round(featured.average_rating))}
                      {'☆'.repeat(5 - Math.round(featured.average_rating))}
                      <b className="text-navy-900 ml-1">{featured.average_rating.toFixed(1)}</b>
                    </>
                  ) : (
                    <span className="text-navy-300 text-xs">Henüz puan yok</span>
                  )}
                  <span className="text-navy-300 font-medium">
                    · {featured.review_count} yorum
                  </span>
                </div>

                {/* Rating distribution (5→1) — DB'den */}
                <div className="mt-3.5 flex flex-col gap-1.5 text-[11px] text-navy-500">
                  {[5, 4, 3, 2, 1].map(star => {
                    const pct = featured.rating_distribution[star - 1] ?? 0
                    return (
                      <div key={star} className="flex items-center gap-2">
                        <span className="w-[40px] text-amber">{'★'.repeat(star)}</span>
                        <span className="flex-1 h-1.5 rounded bg-mist overflow-hidden">
                          <span
                            className="block h-full bg-gradient-to-r from-navy-500 to-red-500 rounded transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </span>
                        <b className="text-navy-900 w-[32px] text-right">%{pct}</b>
                      </div>
                    )
                  })}
                </div>

                <div className="mt-3.5 flex flex-wrap gap-1.5">
                  {featured.courses.slice(0, 3).map(c => (
                    <span
                      key={c.id}
                      className="text-[11px] px-2.5 py-1 rounded-full bg-navy-100 text-navy-700 font-semibold"
                    >
                      {c.code}
                    </span>
                  ))}
                  {featured.faculty && (
                    <span
                      className={`text-[11px] px-2.5 py-1 rounded-full font-semibold ${
                        FACULTY_MAP[featured.faculty]?.badgeBg ?? 'bg-navy-100'
                      } ${FACULTY_MAP[featured.faculty]?.badgeText ?? 'text-navy-700'}`}
                    >
                      {featured.faculty}
                    </span>
                  )}
                </div>
              </Link>
            ) : (
              <div className="absolute top-2.5 right-2.5 w-[320px] h-[240px] rounded-[20px] bg-white/5 border border-white/10 animate-pulse" />
            )}

            {/* Middle: trending course card */}
            {trending ? (
              <Link
                to={`/courses/${trending.id}`}
                className="absolute top-[260px] -left-2.5 w-[260px] rounded-[20px] bg-gradient-to-b from-white to-cream-2 text-navy-900 p-[18px] border border-white shadow-[0_30px_60px_-24px_rgba(11,18,32,.35)] hover:-translate-y-0.5 transition-transform"
              >
                <span className="inline-block text-[11px] px-2.5 py-1 rounded-full bg-red-50 text-red-500 font-semibold mb-2.5">
                  {trending.review_count_week > 0
                    ? `Trending bu hafta · +${trending.review_count_week}`
                    : 'En çok yorumlu ders'}
                </span>
                <div className="serif font-bold text-[22px] text-navy-900 tracking-tight">
                  {trending.code}
                </div>
                <div className="text-[13px] text-navy-700 mt-1 leading-snug line-clamp-2">
                  {trending.name}
                </div>
                <div className="mt-3.5 flex items-center gap-3.5 text-[12px] text-navy-500 flex-wrap">
                  {trending.average_rating != null && (
                    <span>★ <b className="text-navy-900">{trending.average_rating.toFixed(1)}</b></span>
                  )}
                  <span>· {trending.review_count_total} yorum</span>
                  <span>· <b className="text-navy-900">{trending.professor_count}</b> hoca</span>
                </div>
                {(trending.difficulty != null || trending.workload_hours != null) && (
                  <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                    {trending.difficulty != null && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 font-semibold">
                        Zorluk {trending.difficulty}/5
                      </span>
                    )}
                    {trending.workload_hours != null && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 font-semibold">
                        ~{trending.workload_hours} sa/hafta
                      </span>
                    )}
                  </div>
                )}
              </Link>
            ) : (
              <div className="absolute top-[260px] -left-2.5 w-[260px] h-[140px] rounded-[20px] bg-white/5 border border-white/10 animate-pulse" />
            )}

            {/* Bottom: quote card — DB'deki son yorum */}
            {latest && latest.comment ? (
              <Link
                to={
                  latest.course_code
                    ? `/courses`
                    : `/professors`
                }
                className="absolute bottom-0 right-10 w-[300px] rounded-[20px] text-white p-[18px] border border-white/20 backdrop-blur-md shadow-[0_30px_60px_-24px_rgba(11,18,32,.35)] hover:-translate-y-0.5 transition-transform"
                style={{ background: 'linear-gradient(180deg,rgba(227,0,27,.9), rgba(184,0,26,.9))' }}
              >
                <div className="serif text-[56px] leading-[0.7] text-white/35">"</div>
                <p className="mt-1.5 text-[14px] leading-relaxed line-clamp-4">
                  "{latest.comment}"
                </p>
                <div className="mt-3.5 flex items-center gap-2.5 text-[12px] text-white/85">
                  <span className="w-1.5 h-1.5 rounded-full bg-white" />
                  {latest.is_anonymous ? 'Anonim' : (latest.username ?? 'Öğrenci')}
                  {latest.course_code && <> · {latest.course_code}</>}
                  {latest.professor_name && <> · {latest.professor_name}</>}
                  <span className="ml-auto">{timeAgoTr(latest.created_at)}</span>
                </div>
              </Link>
            ) : (
              <div className="absolute bottom-0 right-10 w-[300px] h-[160px] rounded-[20px] bg-white/5 border border-white/10 animate-pulse" />
            )}
          </div>
        </div>
      </section>

      {/* Stat strip — tüm sayılar DB'den */}
      <div className="max-w-[1240px] mx-auto -mt-9 bg-white border border-line rounded-[24px] p-5 grid grid-cols-2 md:grid-cols-4 shadow-[0_20px_40px_-20px_rgba(10,23,51,.2)] relative z-20">
        {[
          {
            lab: 'Hocalar',
            val: summary ? summary.professors_count.toString() : '—',
            em: false,
            trend: summary
              ? `${Object.values(facultyStats).filter(x => x.profs > 0).length} fakülte`
              : '…',
          },
          {
            lab: 'Dersler',
            val: summary ? summary.courses_count.toString() : '—',
            em: false,
            trend: summary
              ? `${FACULTIES.length} fakülte`
              : '…',
          },
          {
            lab: 'Yorumlar',
            val: summary ? formatCount(summary.reviews_count) : '—',
            em: true,
            trend: summary
              ? (summary.reviews_this_week > 0 ? `▲ ${summary.reviews_this_week} bu hafta` : 'bu hafta yeni yorum yok')
              : '…',
          },
          {
            lab: 'Bu hafta',
            val: summary ? summary.reviews_this_week.toString() : '—',
            em: false,
            trend: summary
              ? (summary.reviews_this_week > 0 ? 'yeni yorum' : 'henüz boş')
              : '…',
          },
        ].map((s, i) => (
          <div key={i} className={`px-5 py-2 ${i < 3 ? 'md:border-r md:border-dashed md:border-line' : ''}`}>
            <div className="text-[11px] tracking-[0.12em] uppercase text-navy-300 font-semibold">{s.lab}</div>
            <div className="serif font-semibold text-[34px] tracking-[-0.02em] text-navy-900">
              {s.em ? <em className="not-italic text-red-500">{s.val}</em> : s.val}
            </div>
            <div className="text-[12px] text-mint font-semibold">{s.trend}</div>
          </div>
        ))}
      </div>

      {/* Featured professors — en çok yorum alanlar */}
      <section className="max-w-[1240px] mx-auto px-6 pt-16">
        <div className="flex flex-wrap items-end justify-between gap-6 mb-7">
          <div>
            <div className="text-[12px] tracking-[0.22em] uppercase text-red-500 font-bold">★ En çok konuşulanlar</div>
            <h2 className="serif font-semibold text-navy-900 text-[clamp(28px,3.4vw,40px)] tracking-[-0.02em] mt-2 leading-[1.05] max-w-[20ch]">
              Öğrencilerin en çok yorum yazdığı hocalar.
            </h2>
            <p className="text-navy-500 mt-2.5 max-w-[48ch] text-[15px] leading-relaxed">
              Yorum sayısı ve ortalama puana göre sıralanır — canlı veri.
            </p>
          </div>
          <Link to="/professors" className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full bg-white border border-line font-semibold text-sm text-navy-900 hover:bg-navy-900 hover:text-white hover:border-navy-900 transition-colors">
            Tümünü gör
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
              <path d="M5 12h14m-6-6 6 6-6 6"/>
            </svg>
          </Link>
        </div>

        {loading ? (
          <SkeletonGrid />
        ) : (stats?.top_professors ?? []).length === 0 ? (
          <EmptyHint text="Henüz hoca kaydı yok." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {stats!.top_professors.map(p => <ProfessorCard key={p.id} professor={p} />)}
          </div>
        )}
      </section>

      {/* Department explorer */}
      <section className="max-w-[1240px] mx-auto px-6 pt-20">
        <div className="mb-7">
          <div className="text-[12px] tracking-[0.22em] uppercase text-red-500 font-bold">◎ Fakülte rehberi</div>
          <h2 className="serif font-semibold text-navy-900 text-[clamp(28px,3.4vw,40px)] tracking-[-0.02em] mt-2 leading-[1.05] max-w-[20ch]">
            Fakülteni seç, doğru yolu bul.
          </h2>
          <p className="text-navy-500 mt-2.5 max-w-[48ch] text-[15px] leading-relaxed">
            Her fakülte için üst puanlı dersler ve öğrenci geri bildirimleri.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FACULTIES.map(f => {
            return (
              <Link
                key={f.code}
                to={{ pathname: '/courses', search: `?faculty=${f.code}` }}
                aria-label={`${f.full} derslerine git`}
                className={`relative overflow-hidden rounded-[22px] p-5 min-h-[170px] flex flex-col justify-between text-white bg-gradient-to-br ${f.gradient} hover:-translate-y-1 transition-transform`}
              >
                <div>
                  <div className="mono text-[12px] tracking-[0.14em] opacity-80">{f.code}</div>
                  <div className="serif text-[22px] font-semibold leading-tight mt-1.5">
                    {f.full}
                  </div>
                </div>
                <div className="text-[12px] font-semibold opacity-90">
                  Derslere git →
                </div>
                <div className="absolute -right-2.5 -bottom-2.5 serif text-[120px] font-light opacity-15 leading-none">
                  {f.code[0]}
                </div>
              </Link>
            )
          })}
        </div>
      </section>

      {/* Featured courses */}
      <section className="max-w-[1240px] mx-auto px-6 pt-20">
        <div className="flex flex-wrap items-end justify-between gap-6 mb-7">
          <div>
            <div className="text-[12px] tracking-[0.22em] uppercase text-red-500 font-bold">📚 Öne çıkanlar</div>
            <h2 className="serif font-semibold text-navy-900 text-[clamp(28px,3.4vw,40px)] tracking-[-0.02em] mt-2 leading-[1.05] max-w-[20ch]">
              Bu dönem merak edilen dersler.
            </h2>
          </div>
          <Link to="/courses" className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full bg-white border border-line font-semibold text-sm text-navy-900 hover:bg-navy-900 hover:text-white hover:border-navy-900 transition-colors">
            Tüm dersler
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
              <path d="M5 12h14m-6-6 6 6-6 6"/>
            </svg>
          </Link>
        </div>

        {loading ? (
          <SkeletonGrid />
        ) : (stats?.top_courses ?? []).length === 0 ? (
          <EmptyHint text="Henüz ders kaydı yok." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {stats!.top_courses.map(c => <CourseCard key={c.id} course={c} />)}
          </div>
        )}
      </section>

    </div>
  )
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {[1,2,3,4,5,6].map(i => (
        <div key={i} className="h-[220px] rounded-[22px] bg-white border border-line animate-pulse" />
      ))}
    </div>
  )
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="bg-white border border-line rounded-[22px] p-12 text-center text-navy-300">
      {text}
    </div>
  )
}
