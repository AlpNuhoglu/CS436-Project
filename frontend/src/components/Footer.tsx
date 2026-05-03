import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="bg-gradient-to-b from-navy-900 to-[#05091A] text-navy-200 pt-14 pb-8 px-6 rounded-t-[36px] mt-16">
      <div className="max-w-[1240px] mx-auto grid gap-10 md:grid-cols-[1.4fr_.7fr_.7fr_.7fr]">
        <div>
          <Link to="/" className="flex items-center gap-2.5">
            <span className="relative w-[34px] h-[34px] rounded-[10px] bg-navy-500 grid place-items-center text-white font-bold text-lg overflow-hidden">
              <span className="relative z-10 serif">D</span>
              <span className="absolute inset-x-0 bottom-0 h-[40%] bg-red-500" />
            </span>
            <span>
              <span className="block serif text-[20px] leading-none text-white">Ders Forumu</span>
              <span className="block text-[10px] tracking-[0.22em] text-navy-300 uppercase font-semibold mt-0.5">
                Sabancı Üniversitesi
              </span>
            </span>
          </Link>
          <p className="mt-4 text-[14px] leading-relaxed text-navy-300 max-w-sm">
            Öğrenciler tarafından, öğrenciler için. Her yorum SU e-postası ile doğrulanır;
            isim asla paylaşılmaz.
          </p>
        </div>

        <div>
          <div className="text-[11px] tracking-[0.16em] uppercase text-navy-300 mb-3 font-semibold">
            Keşfet
          </div>
          <Link to="/professors" className="block py-1 text-[14px] hover:text-white">Hocalar</Link>
          <Link to="/courses" className="block py-1 text-[14px] hover:text-white">Dersler</Link>
          <a className="block py-1 text-[14px] hover:text-white">Fakülteler</a>
          <a className="block py-1 text-[14px] hover:text-white">Öne çıkanlar</a>
        </div>

        <div>
          <div className="text-[11px] tracking-[0.16em] uppercase text-navy-300 mb-3 font-semibold">
            Topluluk
          </div>
          <Link to="/guidelines" className="block py-1 text-[14px] hover:text-white">
            Topluluk kuralları
          </Link>
          <Link to="/guidelines" className="block py-1 text-[14px] hover:text-white">
            Yorum rehberi
          </Link>
          <a className="block py-1 text-[14px] hover:text-white">SSS</a>
          <a className="block py-1 text-[14px] hover:text-white">İletişim</a>
        </div>

        <div>
          <div className="text-[11px] tracking-[0.16em] uppercase text-navy-300 mb-3 font-semibold">
            Proje
          </div>
          <a className="block py-1 text-[14px] hover:text-white">Hakkında</a>
          <a className="block py-1 text-[14px] hover:text-white">Roadmap</a>
          <a className="block py-1 text-[14px] hover:text-white">GitHub</a>
          <a className="block py-1 text-[14px] hover:text-white">Gizlilik</a>
        </div>
      </div>

      <div className="max-w-[1240px] mx-auto mt-8 pt-6 border-t border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-[13px] text-navy-300">
        <span>© 2026 Ders Forumu · CS436 Term Project · Sabancı Üniversitesi</span>
        <span className="flex gap-5">
          <a className="hover:text-white">Türkçe</a>
          <a className="hover:text-white">English</a>
          <a className="hover:text-white">v1.0.0-alpha</a>
        </span>
      </div>
    </footer>
  )
}
