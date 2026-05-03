import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { search } from '../api'
import type { SearchResult } from '../types'
import { useAuth } from '../contexts/AuthContext'

export default function Navbar() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<SearchResult | null>(null)
  const [open, setOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [hidden, setHidden] = useState(false)
  const navigate = useNavigate()
  const wrapRef = useRef<HTMLDivElement>(null)
  const lastScrollY = useRef(0)
  const { user, logout } = useAuth()

  useEffect(() => {
    const onScroll = () => {
      const current = window.scrollY
      setHidden(current > lastScrollY.current && current > 60)
      lastScrollY.current = current
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const handleSearch = async (val: string) => {
    setQ(val)
    if (val.length < 2) { setResults(null); setOpen(false); return }
    try {
      const data = await search(val)
      setResults(data)
      setOpen(true)
    } catch { setOpen(false) }
  }

  const go = (path: string) => {
    setOpen(false); setQ(''); setResults(null)
    navigate(path)
  }

  // ⌘K / Ctrl+K to focus search
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        wrapRef.current?.querySelector('input')?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <>
      {/* Nav */}
      <nav className={`sticky top-0 z-40 backdrop-blur-md bg-cream/75 border-b border-line/60 transition-transform duration-300 ${hidden ? '-translate-y-full' : 'translate-y-0'}`}>
        <div className="max-w-[1240px] mx-auto flex items-center gap-7 px-6 py-3.5">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 shrink-0">
            <span className="relative w-[34px] h-[34px] rounded-[10px] bg-navy-500 grid place-items-center text-white font-bold text-lg shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08),0_6px_14px_-6px_rgba(0,48,135,0.6)] overflow-hidden">
              <span className="relative z-10 serif">D</span>
              <span className="absolute inset-x-0 bottom-0 h-[40%] bg-red-500" />
            </span>
            <span>
              <span className="block serif text-[20px] leading-none text-navy-900">Ders Forumu</span>
              <span className="block text-[10px] tracking-[0.22em] text-navy-300 uppercase font-semibold mt-0.5">
                Sabancı Üniversitesi
              </span>
            </span>
          </Link>

          {/* Nav links (desktop) — sadece giriş yapmış kullanıcılara */}
          <div className={`hidden lg:flex items-center gap-1 ml-2 ${!user ? 'invisible pointer-events-none' : ''}`}>
            {[
              { to: '/',            label: 'Anasayfa',           end: true },
              { to: '/professors',  label: 'Hocalar' },
              { to: '/courses',     label: 'Dersler' },
              { to: '/guidelines',  label: 'Topluluk Kuralları' },
            ].map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `px-3.5 py-2 rounded-full text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-navy-900 text-white'
                      : 'text-navy-700 hover:bg-navy-700/10 hover:text-navy-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>

          {/* Search — sadece giriş yapmış kullanıcılara göster */}
          <div ref={wrapRef} className={`relative ml-auto flex-1 max-w-[340px] hidden md:block ${!user ? 'invisible pointer-events-none' : ''}`}>
            <div className="flex items-center gap-2.5 bg-white border border-line rounded-full px-3.5 py-2 shadow-[0_1px_2px_rgba(11,18,32,.06)]">
              <svg className="w-4 h-4 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7"/>
                <path d="m21 21-4.3-4.3"/>
              </svg>
              <input
                value={q}
                onChange={e => handleSearch(e.target.value)}
                onFocus={() => results && setOpen(true)}
                onBlur={() => setTimeout(() => setOpen(false), 180)}
                placeholder="Ders kodu, hoca adı veya anahtar kelime…"
                className="flex-1 bg-transparent outline-none text-[13px] text-navy-900 placeholder:text-navy-300"
              />
              <kbd className="mono text-[11px] px-1.5 py-0.5 rounded-md bg-mist border border-line text-navy-300 hidden sm:inline">⌘K</kbd>
            </div>

            {open && results && (
              <div className="absolute top-full mt-2 left-0 right-0 bg-white rounded-2xl shadow-2xl border border-line overflow-hidden z-50">
                {results.professors.length > 0 && (
                  <div>
                    <div className="px-4 py-2 text-[11px] font-semibold text-navy-300 uppercase tracking-wider bg-cream border-b border-line">
                      Hocalar
                    </div>
                    {results.professors.slice(0, 5).map(p => (
                      <button
                        key={p.id}
                        onMouseDown={() => go(`/professors/${p.id}`)}
                        className="w-full text-left px-4 py-2.5 hover:bg-navy-100/50 flex items-center gap-3 text-sm"
                      >
                        <span className="w-8 h-8 rounded-full bg-navy-500 text-white grid place-items-center text-[11px] font-bold shrink-0">
                          {p.name.split(' ').map(n => n[0]).slice(0, 2).join('')}
                        </span>
                        <span>
                          <span className="block font-medium text-navy-900">{p.name}</span>
                          <span className="block text-xs text-navy-300">
                            {p.faculty && <b className="text-navy-500 mr-1">{p.faculty}</b>}
                            {p.department}
                          </span>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
                {results.courses.length > 0 && (
                  <div>
                    <div className="px-4 py-2 text-[11px] font-semibold text-navy-300 uppercase tracking-wider bg-cream border-y border-line">
                      Dersler
                    </div>
                    {results.courses.slice(0, 5).map(c => (
                      <button
                        key={c.id}
                        onMouseDown={() => go(`/courses/${c.id}`)}
                        className="w-full text-left px-4 py-2.5 hover:bg-navy-100/50 flex items-center gap-3 text-sm"
                      >
                        <span className="w-9 h-8 rounded-md bg-navy-100 text-navy-700 grid place-items-center text-[11px] font-bold shrink-0 mono">
                          {c.code}
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className="block font-medium text-navy-900 truncate">{c.name}</span>
                          <span className="block text-xs text-navy-300">
                            {c.faculty && <b className="text-navy-500 mr-1">{c.faculty}</b>}
                            {c.department}
                          </span>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
                {results.professors.length === 0 && results.courses.length === 0 && (
                  <div className="px-4 py-6 text-center text-sm text-navy-300">Sonuç bulunamadı</div>
                )}
              </div>
            )}
          </div>

          {/* Auth area: login/register veya profile menu */}
          {user ? (
            <div className="relative ml-auto md:ml-0 flex items-center gap-2">
              <button
                onClick={() => navigate('/professors')}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full font-semibold text-sm bg-red-500 text-white hover:bg-red-600 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Yorum Yaz
              </button>

              <button
                onClick={() => setUserMenuOpen(o => !o)}
                onBlur={() => setTimeout(() => setUserMenuOpen(false), 150)}
                className="relative w-9 h-9 rounded-full bg-navy-700 text-white grid place-items-center text-[12px] font-bold hover:bg-navy-900 transition-colors"
                aria-label="Hesap menüsü"
                title={user.first_name ? `${user.first_name} ${user.last_name ?? ''}`.trim() : user.username}
              >
                {user.first_name
                  ? `${user.first_name[0]}${user.last_name?.[0] ?? ''}`.toUpperCase()
                  : user.username.slice(0, 2).toUpperCase()}
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-xl border border-line overflow-hidden z-50">
                  <div className="px-4 py-3 border-b border-line">
                    <div className="text-[11px] uppercase tracking-wider text-navy-300 font-semibold">
                      Giriş yapıldı
                    </div>
                    <div className="text-sm font-medium text-navy-900 truncate">
                      {user.first_name ? `${user.first_name} ${user.last_name ?? ''}`.trim() : user.username}
                    </div>
                  </div>
                  <button
                    onMouseDown={() => { logout(); setUserMenuOpen(false); navigate('/') }}
                    className="w-full text-left px-4 py-2.5 text-sm text-navy-700 hover:bg-navy-100/40"
                  >
                    Çıkış yap
                  </button>
                  {!user.has_email && (
                    <button
                      onMouseDown={() => { setUserMenuOpen(false); navigate('/account/bind-email') }}
                      className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50"
                    >
                      Hesaba e-posta bağla
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="ml-auto md:ml-0 flex items-center gap-2">
              <Link
                to="/login"
                className="px-3.5 py-2 rounded-full text-sm font-medium text-navy-700 hover:bg-navy-700/10 hover:text-navy-900 transition-colors"
              >
                Giriş
              </Link>
              <Link
                to="/register"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full font-semibold text-sm bg-red-500 text-white hover:bg-red-600 transition-colors"
              >
                Kayıt Ol
              </Link>
            </div>
          )}
        </div>

        <div className={`lg:hidden border-t border-line/50 ${!user ? 'hidden' : ''}`}>
          <div className="max-w-[1240px] mx-auto px-4 py-2 flex items-center gap-2 overflow-x-auto">
            {[
              { to: '/',            label: 'Anasayfa',           end: true },
              { to: '/professors',  label: 'Hocalar' },
              { to: '/courses',     label: 'Dersler' },
              { to: '/guidelines',  label: 'Topluluk Kuralları' },
            ].map(item => (
              <NavLink
                key={`mobile-${item.to}`}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `whitespace-nowrap px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-navy-900 text-white'
                      : 'text-navy-700 hover:bg-navy-700/10 hover:text-navy-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
    </>
  )
}
