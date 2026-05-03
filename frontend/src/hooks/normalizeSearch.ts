/**
 * Search input ve aranan değerler için tek bir normalizasyon fonksiyonu.
 *
 * Üst search bar'ın (Navbar → /search endpoint'i) davranışıyla eşitler:
 *   - büyük/küçük harf duyarsız  (Türkçe locale: "İ" → "i", "I" → "ı")
 *   - tüm boşluk karakterlerini siler ("CS 4 36" eşittir "cs436")
 *
 * Hem kullanıcının girdiği `q`'ya hem karşılaştırılan field'a (code, name,
 * department vs.) aynısını uygulayınca her iki taraf da aynı düzleme inmiş
 * olur, böylece "ders adında 'Cloud Computing' yazılı, kullanıcı 'cloudcomputing'
 * arıyor" durumu da çalışır.
 */
export function normalizeSearch(s: string | null | undefined): string {
  if (!s) return ''
  return s.toLocaleLowerCase('tr').replace(/\s+/g, '')
}
