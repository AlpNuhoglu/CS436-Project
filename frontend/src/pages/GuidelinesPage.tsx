import { Link } from 'react-router-dom'
import GuidelinesContent from '../components/GuidelinesContent'

/**
 * /guidelines — Topluluk Kuralları sayfası.
 *
 * İçerik `GuidelinesContent` component'inde tutulur ve modal'de de aynısı kullanılır.
 */
export default function GuidelinesPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      {/* Başlık */}
      <div className="mb-10">
        <Link
          to="/"
          className="text-sm text-navy-500 hover:text-navy-900 inline-flex items-center gap-1 mb-4"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          Anasayfa
        </Link>
        <h1 className="serif text-4xl text-navy-900 leading-tight">
          Topluluk Kuralları
        </h1>
      </div>

      <GuidelinesContent />

      {/* Kapanış */}
      <section className="text-center pt-8">
        <Link
          to="/"
          className="inline-block px-5 py-2.5 rounded-full bg-navy-900 hover:bg-navy-700 text-white text-sm font-medium transition-colors"
        >
          Anladım, devam et
        </Link>
      </section>
    </div>
  )
}
