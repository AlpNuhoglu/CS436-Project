/**
 * Topluluk kuralları metni — sayfa wrapper'ından bağımsız.
 *
 * Hem `/guidelines` sayfasında hem de kayıt formundaki onay modal'inde
 * aynı içeriğin tek kaynaktan beslenmesi için ayrı dosyaya çıkarıldı.
 */
export default function GuidelinesContent() {
  return (
    <div className="space-y-6">
      {/* Giriş */}
      <p className="text-navy-500 text-[15px] leading-relaxed">
        Ders Forumu, Sabancı öğrencilerinin birbirine dürüst geri bildirim verdiği bir
        alandır. Bu ortamı faydalı ve saygılı tutmak için birkaç temel kural var.
      </p>

      {/* Beklediklerimiz */}
      <section className="bg-white border border-[#dde3ec] rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <span className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-700 grid place-items-center text-sm font-bold">
            ✓
          </span>
          <h2 className="serif text-xl text-navy-900">Beklediklerimiz</h2>
        </div>
        <ul className="space-y-2.5 text-[14px] text-navy-700 leading-relaxed pl-9">
          <li>• <b>Spesifik ol.</b> "Hocanın anlatımı net ama ödevler yoğun" gibi.</li>
          <li>• <b>Deneyimine dayan.</b> Kulaktan dolma şeyler yerine kendi yaşadığını yaz.</li>
          <li>• <b>Hem artıyı hem eksiyi belirt.</b> Gelecek yıl bu dersi alacak biri için en faydalısı budur.</li>
          <li>• <b>Zorluk derecesini doldur.</b> Dersin ne kadar zorlu olduğunu puanla, diğer öğrencilere yol gösterir.</li>
          <li>• <b>Saygılı bir dil kullan.</b> Eleştir ama incitme.</li>
        </ul>
      </section>

      {/* Kabul Edilmeyenler */}
      <section className="bg-white border border-[#dde3ec] rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <span className="w-7 h-7 rounded-full bg-red-100 text-red-600 grid place-items-center text-sm font-bold">
            ✕
          </span>
          <h2 className="serif text-xl text-navy-900">Kabul Edilmeyen İçerikler</h2>
        </div>
        <ul className="space-y-2.5 text-[14px] text-navy-700 leading-relaxed pl-9">
          <li>• <b>Küfür ve hakaret.</b> Açık küfür içeren yorumlar otomatik olarak reddedilir.</li>
          <li>• <b>Kişisel saldırı.</b> Bir hocanın görüşlerini eleştirebilirsin; kişiliğine, fiziğine, özel hayatına saldıramazsın.</li>
          <li>• <b>Asılsız iddia.</b> "Şu hoca puanları yükseltmek için para istiyor" gibi kanıtsız ağır iddialar.</li>
          <li>• <b>Spam veya reklam.</b> Tekrar eden mesajlar, link kalabalığı, alakasız içerik.</li>
          <li>• <b>Kişisel veri ifşası.</b> Başkalarının numarasını, mailini, adresini paylaşmak.</li>
        </ul>
      </section>

      {/* Yasal Uyarılar ve Akademik Kurallar */}
      <section className="bg-white border border-[#dde3ec] rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="w-7 h-7 rounded-full bg-navy-100 text-navy-700 grid place-items-center text-sm font-bold">
            §
          </span>
          <h2 className="serif text-xl text-navy-900">Yasal Uyarılar ve Akademik Kurallar</h2>
        </div>
        <div className="space-y-5 text-[14px] text-navy-700 leading-relaxed">
          <div>
            <p className="font-semibold text-navy-900 mb-1">1. Saygı ve Disiplin Kurallarına Uyum</p>
            <p>
              Platformumuzda yer alan yorumların şeffaf olması, resmi disiplin kurallarını ihlal etme hakkı vermez.
              Sitemizi kullanan tüm öğrenciler, yükseköğretim mevzuatına ve <em>Yükseköğretim Kurumları Öğrenci Disiplin Yönetmeliği</em>'ne tabidir.
              Öğretim üyelerine, dekanlara, öğretim görevlilerine veya diğer öğrencilere yönelik hakaret, onur kırıcı söylem,
              akademik etiğe aykırı teşvikler veya asılsız suçlamalar içeren paylaşımlar kesinlikle yasaktır.
            </p>
          </div>
          <div>
            <p className="font-semibold text-navy-900 mb-1">2. Danışman Yönlendirmesinin Esas Alınması</p>
            <p>
              Ders Forumu'nda paylaşılan yorumlar tamamen öğrencilerin kişisel deneyimlerini yansıtır ve resmi bir yönlendirme niteliği taşımaz.
              Üniversite yönetmeliği gereği ders kayıtları, ders ekleme-bırakma (add-drop) işlemleri ve dersten çekilme süreçleri
              bizzat akademik danışmanın görüşü alınarak yürütülmelidir. Platformdaki kullanıcı tavsiyeleri,
              atanmış akademik danışmanlığın yerine geçemez.
            </p>
          </div>
          <div>
            <p className="font-semibold text-navy-900 mb-1">3. Akademik Değerlendirme Esaslarına Saygı</p>
            <p>
              Her dersin değerlendirme esasları, dönem içi çalışmalar, sınav ağırlıkları ve devam zorunluluğu gibi kurallar
              dönem başında ilgili öğretim üyesi tarafından belirlenerek öğrencilere duyurulur.
              Derslerin zorluğu, işlenişi veya notlandırma sistemi hakkında yapılacak değerlendirmeler
              yapıcı eleştiri sınırları içinde kalmalı ve akademik değerlendirme özgürlüğüne saygı çerçevesinde yapılmalıdır.
            </p>
          </div>
          <div>
            <p className="font-semibold text-navy-900 mb-1">4. Not ve Sınav İtirazlarının Yapılacağı Merciler</p>
            <p>
              Ders Forumu resmi bir şikayet, itiraz veya uyuşmazlık çözüm mercii değildir.
              Sınav sonuçlarına ve harf notlarına yapılacak maddi hata itirazları, sonuçların ilanından itibaren
              en geç beş iş günü içinde ilgili fakülte dekanlığına yazılı dilekçe ile bizzat yapılmalıdır.
            </p>
          </div>
          <div>
            <p className="font-semibold text-navy-900 mb-1">5. Gerçek ve Şeffaf Bilgi Paylaşımı</p>
            <p>
              Platformumuzun temel amacı öğrencilere gerçek, şeffaf ve doğrulanmış deneyimler sunmaktır.
              Derslerin ön koşulları, kredi değerleri ya da devamsızlık sınırları hakkında asılsız veya
              kasten yanıltıcı bilgi paylaşımı topluluk kurallarımıza aykırıdır.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
