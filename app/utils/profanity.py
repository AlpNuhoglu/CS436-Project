"""
Hafif içerik filtresi — yorumlardaki açık küfürleri yakalar.

Yaklaşım:
  1) Metni normalize et:
     - lowercase
     - Türkçe diakritik kaldır (ş→s, ç→c, ğ→g, ı→i, ö→o, ü→u, â/î/û → a/i/u)
     - l33t-speak: 0→o, 1→i, 3→e, 4→a, 5→s, 7→t, 8→b, 9→g, @→a, $→s
     - aynı harfin 3+ tekrarını 2'ye indir ("siktirrr" → "siktirr")
     - alfabetik olmayan karakterleri boşluğa çevir
     - tekil boşluklara collapse et
  2) Bilinen küfür listesinden herhangi biri **kelime sınırıyla** geçiyor mu kontrol et.
  3) Bazı kökler için çekimli / çoğul formları ekstra regex ile yakala.

Bu basit bir filtre — niyet, agresif moderasyon değil; en yaygın açık küfürleri tutmak.
False positive ihtimalini düşürmek için liste kısa ve kelime-sınırı kontrolü kullanılıyor.

Kullanım:
    from app.utils.profanity import contains_profanity
    bad, word = contains_profanity("merhaba dünya")
    # bad: bool, word: yakalanan kelime (debug için, kullanıcıya gösterme)
"""
from __future__ import annotations

import re
import unicodedata
from typing import Final

# ── 1) Açık Türkçe küfürler (yaygın varyantları normalize sonrası yakalanır) ──
_TR_PROFANITY: Final[tuple[str, ...]] = (
    "amk", "amq", "aq",
    "amcik", "amcigi", "amina", "aminakoyim", "aminakoyayim",
    "amina koyim", "amina koyayim",
    "anasini", "anasinin",
    "ananin", "ananı", "ananin ami",
    "orospu", "oc", "ococugu", "orospucocugu",
    "pic", "piç",  # piç hala latin1, normalize sonrası "pic" olur
    "sik", "sikim", "sikiyim", "sikeyim", "sikerim", "siktir", "sikt",
    "siktirgit", "siktir git",
    "sikis", "sikisme",
    "yarrak", "yarak", "yaragi",
    "got", "gotveren", "gotlek", "gotluk",
    "ibne", "ipne", "ibine",
    "kahpe", "kahbe",
    "salak", "gerizekali", "gerizekâli",
    "mal", "aptal",  # not: bunlar borderline; aşağıda kelime sınırlı olduğu için yan etki azalır
    "puşt", "pust", "pezevenk",
    "kaltak",
    "sürtük", "surtuk",
    "dallama",
    "kerhane",
    "dı̇bı̇nesı̇kim", "dibinesikim",
)

# ── 2) İngilizce yaygın küfürler ──────────────────────────────────────────────
_EN_PROFANITY: Final[tuple[str, ...]] = (
    "fuck", "fucking", "fucker", "motherfucker", "mf",
    "shit", "bullshit",
    "bitch", "bastard",
    "asshole",  # NB: "ass" alone çıkarıldı — "Asmin", "asgari" gibi gerçek kelimelere yan etki yapıyordu.
    "dick", "cock", "pussy",
    "cunt",
    "retard", "retarded",
    "faggot", "fag",
    "nigger", "nigga",
    "whore", "slut",
)

# Birleşik liste — boş string'leri at, set'e çevir
_PROFANE_SET: Final[frozenset[str]] = frozenset(
    w.strip() for w in (*_TR_PROFANITY, *_EN_PROFANITY) if w.strip()
)

# Bazı kelimeler çok kısa / aşırı yaygın yan eşleşme yapabilir — özel kelime sınırı şart.
# (Aşağıdaki normalize aşamasından sonra bu kelimeler regex \b ile aranıyor.)

# l33t-speak çevirisi (normalize aşamasında uygulanır)
_LEET_MAP: Final[dict[str, str]] = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "9": "g",
    "@": "a", "$": "s",
}

# Türkçe karakter eşlemesi (NFKD ile çoğu hâlleder ama ı/İ farklı davranır)
_TR_FOLD: Final[dict[str, str]] = {
    "ş": "s", "Ş": "s",
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "İ": "i", "I": "i",
    "ö": "o", "Ö": "o",
    "ü": "u", "Ü": "u",
    "â": "a", "Â": "a",
    "î": "i", "Î": "i",
    "û": "u", "Û": "u",
}


def _strip_diacritics(s: str) -> str:
    """NFKD normalize + birleşik aksanları kırp."""
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _normalize(text: str) -> str:
    """Metni karşılaştırmaya hazırla: tr fold + leet + non-alpha→space + collapse."""
    if not text:
        return ""
    # 1) Türkçe karakterleri Latin'e indir (ı→i kritik!)
    text = "".join(_TR_FOLD.get(ch, ch) for ch in text)
    # 2) Diakritik temizle
    text = _strip_diacritics(text)
    # 3) lowercase
    text = text.lower()
    # 4) leet-speak
    text = "".join(_LEET_MAP.get(ch, ch) for ch in text)
    # 5) Aynı harfin 3+ tekrarını 2'ye indir ("siktirrr" → "siktirr").
    #    İçeride 2'li kalan harfleri korur (ör. "yarrak", "asshole").
    text = re.sub(r"([a-z])\1{2,}", r"\1\1", text)
    # 6) Alfabetik olmayan her şey → boşluk (kelime sınırını korumak için)
    text = re.sub(r"[^a-z]+", " ", text)
    # 7) Çoklu boşlukları tekleştir
    text = re.sub(r"\s+", " ", text).strip()
    # 8) Kelime sonlarındaki 2'li harf tekrarını teke indir ("siktirr" → "siktir",
    #    "fuckk" → "fuck"). Kelime ortasındaki çiftler ("yarrak", "asshole") etkilenmez.
    text = re.sub(r"([a-z])\1+(?=\s|$)", r"\1", text)
    return text


# Önceden derlenmiş regex — performans için modül yüklenirken bir kez kurulur.
# Her küfür için \b...\b ile kelime-sınırlı eşleşme; iki kelimelik ifadeler de
# normalize sonrası "amina koyim" → "amina koyim" olarak kalır, regex de \b ile boşluk
# arasında çalışır.
def _build_pattern(words: frozenset[str]) -> re.Pattern[str]:
    # Uzun ifadeleri önce, kısa olanlardan önce dene (overlap için)
    sorted_words = sorted(words, key=len, reverse=True)
    # Her kelimeyi normalize et — listede zaten Latin/lower; yine de güvene al
    parts = [re.escape(_normalize(w)) for w in sorted_words if _normalize(w)]
    # Tek/çok-kelimeli ifadeler için \b sınırları yeterli (boşluk zaten ayrılmış)
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b")


_PATTERN: Final[re.Pattern[str]] = _build_pattern(_PROFANE_SET)

# Kelime-listesiyle yakalanmayan yaygın çekimli biçimler.
# Amaç "sikerler", "sikiyor", "orospuluk" gibi açık varyasyonları tutmak.
_EXTRA_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bsik(?:er(?:ler|im|sin|siniz)?|iyor(?:lar)?|ti(?:m|n|k|lar)?|mis(?:im|in|iniz|ler)?|ecek(?:ler)?|eyim|iyim|mek|meden|ince)\b"),
    re.compile(r"\borospu(?:luk|lugu|lugu|lar|lari|cocugu|cocuklari)?\b"),
    re.compile(r"\bpic(?:ler|lik|ligi)?\b"),
    re.compile(r"\byarrak(?:lar|lari|gibi)?\b"),
)


def contains_profanity(text: str | None) -> tuple[bool, str | None]:
    """
    Metinde açık küfür var mı?

    Returns:
        (True, "yakalanan_kelime") — bulunduysa
        (False, None) — temizse veya text boşsa
    """
    if not text or not text.strip():
        return False, None
    normalized = _normalize(text)
    if not normalized:
        return False, None
    m = _PATTERN.search(normalized)
    if m:
        return True, m.group(0)
    for pattern in _EXTRA_PATTERNS:
        m = pattern.search(normalized)
        if m:
            return True, m.group(0)
    return False, None


__all__ = ["contains_profanity"]
