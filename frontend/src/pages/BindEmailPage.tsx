import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { startEmailBind, verifyEmailBind } from '../api'
import { useAuth } from '../contexts/AuthContext'

const ALLOWED_DOMAIN = 'sabanciuniv.edu'

type Step = 'start' | 'verify'

export default function BindEmailPage() {
  const { user, loading, refreshUser } = useAuth()
  const [step, setStep] = useState<Step>('start')
  const [email, setEmail] = useState(user?.email ?? '')
  const [otp, setOtp] = useState('')
  const [info, setInfo] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)

  if (!loading && !user) return <Navigate to="/login" replace />

  if (!loading && user?.has_email) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-md bg-white rounded-2xl border border-[#dde3ec] shadow-sm p-8 text-center">
          <h1 className="serif text-2xl font-bold text-[#0A1733] mb-2">E-posta zaten bağlı</h1>
          <p className="text-sm text-gray-600">
            Hesabında kayıtlı private e-posta: <b>{user.email}</b>
          </p>
        </div>
      </div>
    )
  }

  const start = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setInfo('')
    setSubmitting(true)
    try {
      const resp = await startEmailBind({ email: email.trim().toLowerCase() })
      setInfo(resp.message)
      setExpiresAt(resp.expires_at)
      setStep('verify')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Doğrulama başlatılamadı.')
    } finally {
      setSubmitting(false)
    }
  }

  const verify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setInfo('')
    setSubmitting(true)
    try {
      const resp = await verifyEmailBind({ email: email.trim().toLowerCase(), otp })
      await refreshUser()
      setInfo(resp.message)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Doğrulama tamamlanamadı.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl border border-[#dde3ec] shadow-sm p-8">
          <h1 className="serif text-2xl font-bold text-[#0A1733] mb-1">Hesaba E-posta Bağla</h1>
          <p className="text-sm text-gray-600 mb-6">
            Anonim yorum modelini bozmadan hesabına private bir kurtarma e-postası ekle.
          </p>

          {step === 'start' ? (
            <form onSubmit={start} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sabancı e-posta adresi</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoFocus
                  placeholder={`isim.soyisim@${ALLOWED_DOMAIN}`}
                  className="w-full border border-[#dde3ec] rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-[#003087]"
                />
              </div>

              {error && <p className="text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
              {info && <p className="text-sm text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg">{info}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                {submitting ? 'Kod gönderiliyor...' : 'Doğrulama Kodu Gönder'}
              </button>
            </form>
          ) : (
            <form onSubmit={verify} className="space-y-4">
              {info && (
                <p className="text-sm text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg">
                  {info}
                  {expiresAt && (
                    <span className="block text-[11px] text-emerald-700/80 mt-1">
                      Son geçerlilik: {new Date(expiresAt).toLocaleTimeString('tr-TR')}
                    </span>
                  )}
                </p>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">6 haneli kod</label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                  required
                  autoFocus
                  className="w-full border border-[#dde3ec] rounded-lg px-3 py-3 text-center text-xl tracking-[0.5em] font-mono focus:outline-none focus:border-[#003087]"
                />
              </div>

              {error && <p className="text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                {submitting ? 'Doğrulanıyor...' : 'E-postayı Bağla'}
              </button>

              <div className="flex items-center justify-between text-xs text-gray-600 pt-1">
                <button
                  type="button"
                  onClick={() => { setStep('start'); setOtp(''); setError(''); setInfo('') }}
                  className="hover:underline"
                >
                  ← E-postayı düzenle
                </button>
                <Link to="/" className="hover:underline">
                  Anasayfaya dön
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
