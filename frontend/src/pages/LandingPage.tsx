import { Link } from 'react-router-dom'

const FEATURES = [
  {
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-4l-4 4z" />
      </svg>
    ),
    title: 'Gerçek Öğrenci Yorumları',
    desc: 'Hocalar ve dersler hakkında Sabancı öğrencilerinden gelen dürüst ve ayrıntılı değerlendirmeler.',
  },
  {
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    title: 'SUIS ile Doğrulanmış',
    desc: 'Yorumlar SUIS veritabanıyla çapraz kontrol edilir. Hoca, ders ve dönem bilgileri gerçek verilerle eşleştirilir.',
  },
  {
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0" />
      </svg>
    ),
    title: 'Sadece Sabancılılar',
    desc: 'Kayıt için "sabanciuniv.edu" uzantılı e-posta adresi gerekir. Topluluk güvenli ve üniversiteye özel kalır.',
  },
  {
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    title: 'Zorluk Seviyesi',
    desc: 'Sadece yıldız puanı değil, her ders için öğrencilerin hissettiği zorluk seviyesi de paylaşılıyor.',
  },
]

const STEPS = [
  { num: '01', title: 'Sabancı e-postanla kayıt ol', desc: '@sabanciuniv.edu adresiyle doğrulama kodu alırsın.' },
  { num: '02', title: 'Hoca veya dersi ara', desc: 'SUIS\'ten çekilen gerçek ders ve hoca veritabanına ulaş.' },
  { num: '03', title: 'Oku, değerlendir, karar ver', desc: 'Kayıt döneminden önce gerçek deneyimleri oku; kendi yorumunu yaz.' },
]

export default function LandingPage() {
  return (
    <div>
      {/* ═══ HERO ═══ */}
      <section
        className="relative overflow-hidden text-white px-6 pt-20 pb-14"
        style={{
          backgroundImage:
            'radial-gradient(1000px 600px at 15% -10%, rgba(227,0,27,.18), transparent 60%), radial-gradient(800px 500px at 90% 20%, rgba(255,255,255,.07), transparent 60%), linear-gradient(180deg,#07102A 0%, #0F2047 60%, #14296A 100%)',
        }}
      >
        {/* Subtle grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        <div className="max-w-[860px] mx-auto text-center relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-white/8 border border-white/15 rounded-full px-4 py-1.5 text-[13px] font-medium text-white/80 mb-8 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Sabancı Üniversitesi · Öğrenci Platformu
          </div>

          <h1 className="serif font-semibold leading-[1.03] text-[clamp(42px,7vw,88px)] tracking-[-0.03em]">
            Bir dersi almadan önce,
            <br />
            <em className="not-italic italic font-normal relative">
              <span className="relative text-[#FFD99B]">
                gerçek deneyimleri
                <span className="absolute left-0 right-0 bottom-[.06em] h-[.1em] bg-gradient-to-r from-transparent via-[#FFD99B]/60 to-transparent" />
              </span>
            </em>{' '}
            oku.
          </h1>

          <p className="mt-6 text-white/65 text-[18px] leading-relaxed max-w-[56ch] mx-auto">
            Sabancı Üniversitesi öğrencilerinin hocalar ve dersler hakkında paylaştığı
            deneyimler, zorluk dereceleri, gerçek yorumlar ve daha fazlası.
          </p>

        </div>

        {/* Bottom fade */}
        <div className="absolute bottom-0 inset-x-0 h-24 bg-gradient-to-t from-[#F5F6F8] to-transparent" />
      </section>

      {/* ═══ FEATURES ═══ */}
      <section className="max-w-[1100px] mx-auto px-6 pt-10 pb-8">
        <div className="text-center mb-12">
          <div className="text-[12px] tracking-[0.22em] uppercase text-red-500 font-bold mb-3">Neden Ders Forumu?</div>
          <h2 className="serif font-semibold text-navy-900 text-[clamp(28px,3.5vw,44px)] tracking-[-0.02em] leading-tight">
            Kayıt dönemini daha akıllıca geç.
          </h2>
          <p className="mt-3 text-navy-400 text-[16px] max-w-[46ch] mx-auto leading-relaxed">
            Takvim dolmadan önce doğru dersi, doğru hocayla bul.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {FEATURES.map((f, i) => (
            <div
              key={i}
              className="bg-white rounded-[22px] border border-[#dde3ec] p-6 hover:-translate-y-1 transition-transform shadow-[0_4px_24px_-8px_rgba(10,23,51,0.08)]"
            >
              <div className="w-11 h-11 rounded-xl bg-navy-900 text-white flex items-center justify-center mb-4">
                {f.icon}
              </div>
              <h3 className="serif font-semibold text-navy-900 text-[17px] leading-snug mb-2">{f.title}</h3>
              <p className="text-navy-400 text-[14px] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ HOW IT WORKS ═══ */}
      <section className="max-w-[1100px] mx-auto px-6 pt-20 pb-8">
        <div className="text-center mb-12">
          <div className="text-[12px] tracking-[0.22em] uppercase text-red-500 font-bold mb-3">Nasıl Çalışır?</div>
          <h2 className="serif font-semibold text-navy-900 text-[clamp(28px,3.5vw,44px)] tracking-[-0.02em] leading-tight">
            Üç adımda başla.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
          {/* Connector line (desktop) */}
          <div className="hidden md:block absolute top-9 left-[calc(16.67%+1rem)] right-[calc(16.67%+1rem)] h-px bg-gradient-to-r from-[#dde3ec] via-red-200 to-[#dde3ec]" />

          {STEPS.map((s, i) => (
            <div key={i} className="relative flex flex-col items-center text-center">
              <div className="w-[52px] h-[52px] rounded-full bg-navy-900 text-white flex items-center justify-center serif font-semibold text-[18px] mb-5 shadow-[0_8px_20px_-8px_rgba(10,23,51,0.35)] z-10 relative">
                {i + 1}
              </div>
              <h3 className="serif font-semibold text-navy-900 text-[18px] mb-2">{s.title}</h3>
              <p className="text-navy-400 text-[14px] leading-relaxed max-w-[28ch]">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ CTA ═══ */}
      <section className="max-w-[1100px] mx-auto px-6 pt-16 pb-24">
        <div
          className="relative overflow-hidden rounded-[32px] px-8 py-16 text-center text-white"
          style={{
            backgroundImage:
              'radial-gradient(900px 400px at 50% 120%, rgba(227,0,27,.22), transparent 60%), linear-gradient(135deg,#09122B 0%, #0F2047 50%, #14296A 100%)',
          }}
        >
          {/* Dot pattern */}
          <div
            className="absolute inset-0 opacity-[0.06]"
            style={{
              backgroundImage: 'radial-gradient(circle, rgba(255,255,255,1) 1px, transparent 1px)',
              backgroundSize: '28px 28px',
            }}
          />

          <div className="relative z-10 max-w-[600px] mx-auto">
            <div className="serif font-semibold text-[clamp(28px,4vw,48px)] tracking-[-0.02em] leading-tight mb-4">
              Hazır mısın?
            </div>
            <p className="text-white/60 text-[16px] leading-relaxed mb-8">
              Binlerce Sabancı öğrencisinin deneyimlerine erişmek için sadece birkaç saniye.
            </p>
            <div className="flex items-center justify-center gap-3 flex-wrap">
              <Link
                to="/register"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-red-500 text-white font-semibold text-[15px] hover:bg-red-600 shadow-[0_20px_40px_-16px_rgba(227,0,27,0.55)] transition-all hover:-translate-y-0.5"
              >
                Kayıt Ol
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                  <path d="M5 12h14m-6-6 6 6-6 6" />
                </svg>
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-white/8 text-white border border-white/20 font-semibold text-[15px] hover:bg-white/15 backdrop-blur-sm transition-all hover:-translate-y-0.5"
              >
                Giriş Yap
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ DISCLAIMER ═══ */}
      <div className="max-w-[1100px] mx-auto px-6 pb-16">
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-5 py-4">
          <svg className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-[13px] text-amber-800 leading-relaxed">
            <span className="font-semibold">Bir not:</span> Platformdaki her yorum, o öğrencinin kişisel deneyimini yansıtır. Farklı öğrencilerin bakış açıları birbirinden farklılık gösterebilir. Karar vermeden önce birden fazla yorumu okumanızı ve kendi beklentilerinizle karşılaştırmanızı tavsiye ederiz.
          </p>
        </div>
      </div>
    </div>
  )
}
