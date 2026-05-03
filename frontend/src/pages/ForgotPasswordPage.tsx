import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { forgotPassword, resetPassword } from '../api'

const ALLOWED_DOMAIN = 'sabanciuniv.edu'

type Step = 'start' | 'verify' | 'done'

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('start')
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [info, setInfo] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)
  const [countdown, setCountdown] = useState(5)

  useEffect(() => {
    if (step !== 'done') return
    const interval = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) { navigate('/login'); return 0 }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [step, navigate])

  const start = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setInfo('')
    setLoading(true)
    try {
      const resp = await forgotPassword({ email: email.trim().toLowerCase() })
      setInfo(resp.message)
      setExpiresAt(resp.expires_at)
      setStep('verify')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'İstek başlatılamadı.')
    } finally {
      setLoading(false)
    }
  }

  const verify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await resetPassword({
        email: email.trim().toLowerCase(),
        otp,
        new_password: newPassword,
      })
      setStep('done')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Şifre sıfırlanamadı.')
    } finally {
      setLoading(false)
    }
  }

  if (step === 'done') {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl border border-[#dde3ec] shadow-sm p-8 text-center">
            <div className="flex items-center justify-center w-14 h-14 rounded-full bg-emerald-100 mx-auto mb-4">
              <svg className="w-7 h-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="serif text-2xl font-bold text-[#0A1733] mb-2">Şifre Güncellendi</h1>
            <p className="text-sm text-gray-600 mb-6">
              Şifreni başarıyla değiştirdin. Yeni şifrenle giriş yapabilirsin.
            </p>
            <Link
              to="/login"
              className="block w-full bg-[#003087] hover:bg-[#002060] text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
            >
              Giriş Yap
            </Link>
            <p className="text-xs text-gray-400 mt-3">{countdown} saniye içinde yönlendiriliyorsun…</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl border border-[#dde3ec] shadow-sm p-8">
          <h1 className="serif text-2xl font-bold text-[#0A1733] mb-1">Şifremi Unuttum</h1>
          <p className="text-sm text-gray-600 mb-6">
            {step === 'start'
              ? `Kayıtlı @${ALLOWED_DOMAIN} adresine sıfırlama kodu gönderelim.`
              : `${email} adresine gelen 6 haneli kodu ve yeni şifreni gir.`}
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
                disabled={loading}
                className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                {loading ? 'Kod gönderiliyor...' : 'Sıfırlama Kodu Gönder'}
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

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Yeni şifre</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  className="w-full border border-[#dde3ec] rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-[#003087]"
                />
              </div>

              {error && <p className="text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                {loading ? 'Şifre güncelleniyor...' : 'Şifreyi Güncelle'}
              </button>

              <div className="flex items-center justify-between text-xs text-gray-600 pt-1">
                <button
                  type="button"
                  onClick={() => { setStep('start'); setOtp(''); setNewPassword(''); setError(''); setInfo('') }}
                  className="hover:underline"
                >
                  ← E-postayı düzenle
                </button>
                <button
                  type="button"
                  onClick={() => setStep('start')}
                  className="hover:underline"
                >
                  Yeni kod iste
                </button>
              </div>
            </form>
          )}

          <div className="mt-6 pt-6 border-t border-[#eef1f6] text-sm text-gray-600 text-center">
            Şifreni hatırladın mı?{' '}
            <Link to="/login" className="font-medium text-[#003087] hover:underline">
              Giriş yap
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
