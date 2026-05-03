import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(identifier.trim(), password)
      const from = (location.state as { from?: string } | null)?.from ?? '/'
      navigate(from, { replace: true })
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Giriş yapılamadı.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl border border-[#dde3ec] shadow-sm p-8">
          <h1 className="serif text-2xl font-bold text-[#0A1733] mb-1">Giriş Yap</h1>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sabancı e-posta adresi</label>
              <input
                type="email"
                value={identifier}
                onChange={e => setIdentifier(e.target.value)}
                required
                autoFocus
                placeholder="isim.soyisim@sabanciuniv.edu"
                className="w-full border border-[#dde3ec] rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-[#003087]"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Şifre</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  className="w-full border border-[#dde3ec] rounded-lg px-3 py-2.5 pr-10 text-sm focus:outline-none focus:border-[#003087]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
            >
              {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
            </button>

            <div className="text-right">
              <Link to="/forgot-password" className="text-sm font-medium text-[#003087] hover:underline">
                Şifremi unuttum
              </Link>
            </div>
          </form>

          <div className="mt-6 pt-6 border-t border-[#eef1f6] text-sm text-gray-600 text-center">
            Hesabın yok mu?{' '}
            <Link to="/register" className="font-medium text-[#003087] hover:underline">
              Kayıt ol
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
