import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import GuidelinesModal from '../components/GuidelinesModal'

const ALLOWED_DOMAIN = 'sabanciuniv.edu'

type Step = 'form' | 'verify'

interface PasswordStrength {
  score: number        // 0–4
  label: string
  color: string        // Tailwind bg class
  checks: { label: string; ok: boolean }[]
}

function passwordStrength(pw: string): PasswordStrength {
  const checks = [
    { label: 'En az 8 karakter', ok: pw.length >= 8 },
    { label: 'Büyük harf (A–Z)', ok: /[A-Z]/.test(pw) },
    { label: 'Küçük harf (a–z)', ok: /[a-z]/.test(pw) },
    { label: 'Rakam (0–9)', ok: /[0-9]/.test(pw) },
    { label: 'Özel karakter (!@#…)', ok: /[^A-Za-z0-9]/.test(pw) },
  ]
  const score = checks.filter(c => c.ok).length
  const labels = ['', 'Çok zayıf', 'Zayıf', 'Orta', 'İyi', 'Güçlü']
  const colors = ['', 'bg-red-500', 'bg-orange-400', 'bg-yellow-400', 'bg-emerald-400', 'bg-emerald-600']
  return { score, label: labels[score] ?? '', color: colors[score] ?? '', checks }
}

export default function RegisterPage() {
  const { registerStart, registerVerify } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState<Step>('form')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [guidelinesOpen, setGuidelinesOpen] = useState(false)
  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)

  const startSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setInfo('')

    const emailLc = email.trim().toLowerCase()
    if (!emailLc.endsWith(`@${ALLOWED_DOMAIN}`)) {
      setError(`Email adresi @${ALLOWED_DOMAIN} ile bitmelidir.`)
      return
    }
    if (firstName.trim().length < 2 || lastName.trim().length < 2) {
      setError('İsim ve soyisim en az 2 karakter olmalı.')
      return
    }
    if (passwordStrength(password).score < 3) {
      setError('Şifre yeterince güçlü değil. Büyük/küçük harf, rakam ve özel karakter kullan.')
      return
    }
    if (!acceptedTerms) {
      setError('Devam etmek için topluluk kurallarını kabul etmen gerekir.')
      return
    }

    setLoading(true)
    try {
      const resp = await registerStart({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: emailLc,
        password,
      })
      setInfo(resp.message)
      setExpiresAt(resp.expires_at)
      setStep('verify')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Kayıt başlatılamadı.')
    } finally {
      setLoading(false)
    }
  }

  const verifySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (otp.length !== 6) {
      setError('Kod 6 haneli olmalıdır.')
      return
    }

    setLoading(true)
    try {
      await registerVerify(email.trim().toLowerCase(), otp)
      navigate('/', { replace: true })
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Doğrulama başarısız.')
    } finally {
      setLoading(false)
    }
  }

  const resend = async () => {
    setError(''); setInfo('')
    setLoading(true)
    try {
      const resp = await registerStart({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim().toLowerCase(),
        password,
      })
      setInfo('Yeni kod gönderildi.')
      setExpiresAt(resp.expires_at)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Yeniden gönderilemedi.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl border border-[#dde3ec] shadow-sm p-8">
          <h1 className="serif text-2xl font-bold text-[#0A1733] mb-1">
            {step === 'form' ? 'Kayıt Ol' : 'E-posta Doğrulama'}
          </h1>
          {step === 'verify' && (
            <p className="text-sm text-gray-600 mb-6">
              {email} adresine 6 haneli bir kod gönderdik.
            </p>
          )}

          {step === 'form' ? (
            <form onSubmit={startSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">İsim</label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={e => setFirstName(e.target.value)}
                    required
                    minLength={2}
                    autoFocus
                    className="w-full border border-[#dde3ec] rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-[#003087]"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Soyisim</label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={e => setLastName(e.target.value)}
                    required
                    minLength={2}
                    className="w-full border border-[#dde3ec] rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-[#003087]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sabancı e-posta adresi
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  placeholder={`isim.soyisim@${ALLOWED_DOMAIN}`}
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

                {/* Şifre güç göstergesi — sadece bir şeyler yazılmaya başlanınca */}
                {password.length > 0 && (() => {
                  const s = passwordStrength(password)
                  return (
                    <div className="mt-2 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 flex gap-0.5 h-1.5">
                          {[1, 2, 3, 4, 5].map(n => (
                            <div
                              key={n}
                              className={`flex-1 rounded-full transition-colors ${n <= s.score ? s.color : 'bg-gray-200'}`}
                            />
                          ))}
                        </div>
                        <span className={`text-[11px] font-semibold min-w-[52px] text-right ${
                          s.score <= 2 ? 'text-red-500' : s.score === 3 ? 'text-yellow-600' : 'text-emerald-600'
                        }`}>{s.label}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
                        {s.checks.map(c => (
                          <div key={c.label} className={`flex items-center gap-1 text-[11px] ${c.ok ? 'text-emerald-600' : 'text-gray-400'}`}>
                            <svg className="w-3 h-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              {c.ok
                                ? <path d="M5 13l4 4L19 7"/>
                                : <path d="M18 6L6 18M6 6l12 12"/>
                              }
                            </svg>
                            {c.label}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })()}
              </div>

              {/* Topluluk kuralları onayı — modal ile, sona kadar kaydırmadan kabul edilemez */}
              {acceptedTerms ? (
                <div className="flex items-center gap-2.5 text-sm bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2.5">
                  <svg
                    className="w-5 h-5 text-emerald-600 shrink-0"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.4"
                  >
                    <path d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="flex-1 text-emerald-800">
                    Topluluk kurallarını okudun ve kabul ettin.
                  </span>
                  <button
                    type="button"
                    onClick={() => setGuidelinesOpen(true)}
                    className="text-xs text-emerald-700 hover:text-emerald-900 hover:underline font-medium"
                  >
                    Tekrar gör
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setGuidelinesOpen(true)}
                  className="w-full flex items-center justify-between gap-3 text-left text-sm bg-[#f8faff] border-2 border-dashed border-[#003087]/30 hover:border-[#003087]/60 hover:bg-[#003087]/5 rounded-lg px-3 py-2.5 transition-colors"
                >
                  <span className="flex items-center gap-2.5 text-navy-700">
                    <svg
                      className="w-5 h-5 text-[#003087] shrink-0"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
                    </svg>
                    <span>
                      <span className="block font-medium text-navy-900">
                        Topluluk kurallarını oku ve onayla
                      </span>
                      <span className="block text-[11px] text-navy-500 mt-0.5">
                        Devam etmek için zorunludur.
                      </span>
                    </span>
                  </span>
                  <span className="text-xs font-semibold text-[#003087]">
                    Aç →
                  </span>
                </button>
              )}

              {error && <p className="text-sm text-[#E3001B] bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

              <button
                type="submit"
                disabled={loading || !acceptedTerms}
                className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                {loading ? 'Kod gönderiliyor...' : 'Doğrulama Kodu Gönder'}
              </button>
            </form>
          ) : (
            <form onSubmit={verifySubmit} className="space-y-4">
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
                disabled={loading}
                className="w-full bg-[#003087] hover:bg-[#002060] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                {loading ? 'Doğrulanıyor...' : 'Doğrula ve Giriş Yap'}
              </button>

              <div className="flex items-center justify-between text-xs text-gray-600 pt-1">
                <button
                  type="button"
                  onClick={() => { setStep('form'); setOtp(''); setError(''); setInfo('') }}
                  className="hover:underline"
                >
                  ← E-postayı düzenle
                </button>
                <button
                  type="button"
                  onClick={resend}
                  disabled={loading}
                  className="hover:underline disabled:opacity-50"
                >
                  Kodu yeniden gönder
                </button>
              </div>
            </form>
          )}

          <div className="mt-6 pt-6 border-t border-[#eef1f6] text-sm text-gray-600 text-center">
            Zaten hesabın var mı?{' '}
            <Link to="/login" className="font-medium text-[#003087] hover:underline">
              Giriş yap
            </Link>
          </div>
        </div>
      </div>

      <GuidelinesModal
        open={guidelinesOpen}
        onClose={() => setGuidelinesOpen(false)}
        onAccept={() => {
          setAcceptedTerms(true)
          setGuidelinesOpen(false)
        }}
      />
    </div>
  )
}
