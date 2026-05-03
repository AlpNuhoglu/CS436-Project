"""
SUIS Scraper — Sabancı Üniversitesi Ders Programı Verisi

Banner sistemi (bwckschd) üzerinden Fall 2024 ve sonraki dönemlerin
(yaz dönemleri hariç) ders + hoca verilerini çeker ve PostgreSQL'e yazar.

Kullanım (proje kök dizininde):
    python suis_scraper.py

Gereksinimler (zaten requirements.txt'te olması lazım):
    pip install requests beautifulsoup4 sqlalchemy psycopg2-binary python-dotenv

Çevre değişkeni:
    DATABASE_URL  —  .env dosyasından otomatik okunur.
                     Yoksa localhost:5432 üzerindeki ders_forumu'na bağlanır.

Notlar:
  - Mevcut kayıtlar silinmez; sadece yeni kayıtlar eklenir (idempotent).
  - Hoca isimlerindeki "Staff" / boş değerler atlanır.
  - Ders kodu ön ekine göre fakülte otomatik atanır.
"""

import os
import re
import sys
import time
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── Yol ayarı ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

from app.models import Professor, Course, ProfessorCourse  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("suis_scraper")

# ── Sabitler ──────────────────────────────────────────────────────────────────
BASE_URL    = "https://suis.sabanciuniv.edu/prod"
SCHED_URL   = f"{BASE_URL}/bwckschd.p_disp_dyn_sched"
SUBJECT_URL = f"{BASE_URL}/bwckgens.p_proc_term_date"   # Term seçildikten sonra konu listesi
COURSE_URL  = f"{BASE_URL}/bwckschd.p_get_crse_unsec"   # Konu seçildikten sonra ders listesi

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

# İki istek arasındaki bekleme süresi (saniye) — sunucuyu yormamak için
REQUEST_DELAY = 1.5

# ── Fakülte eşlemesi ──────────────────────────────────────────────────────────
# Ders kodu öneki → fakülte kısaltması
# Listedeki sıra önemli: uzun önekler önce gelir (ör. "ENS" > "EN")
FACULTY_MAP: list[tuple[str, str]] = [
    # FENS
    ("CS",    "FENS"),
    ("EE",    "FENS"),
    ("IE",    "FENS"),
    ("ME",    "FENS"),
    ("MAT",   "FENS"),
    ("BIO",   "FENS"),
    ("PHYS",  "FENS"),
    ("CHEM",  "FENS"),
    ("ENS",   "FENS"),
    ("IF",    "FENS"),
    ("MFGE",  "FENS"),
    ("NSE",   "FENS"),
    ("NANO",  "FENS"),
    # FASS
    ("HIST",  "FASS"),
    ("POLS",  "FASS"),
    ("IR",    "FASS"),
    ("SPS",   "FASS"),
    ("CULT",  "FASS"),
    ("VA",    "FASS"),
    ("ECON",  "FASS"),
    ("PSY",   "FASS"),
    ("PHIL",  "FASS"),
    ("SOC",   "FASS"),
    ("HART",  "FASS"),
    ("COMD",  "FASS"),
    ("ART",   "FASS"),
    # SBS
    ("BA",    "SBS"),
    ("MGMT",  "SBS"),
    ("FIN",   "SBS"),
    ("MAN",   "SBS"),
    ("ACC",   "SBS"),
    ("MKT",   "SBS"),
    ("OPIM",  "SBS"),
    # SL (School of Languages) prefix'leri — ENG/TLL/GER/FRE/JPN/SPA/ITA/ARA/CHI —
    # sistemden çıkarıldı. Aşağıdaki SL_PREFIXES set'i scraper'ın bu kodları
    # tamamen atlamasını sağlar.
]

# SL fakültesi sistemden çıkarıldı. SUIS'te bu prefix'lerle gelen tüm dersler
# scraper tarafından görmezden gelinir; eski DB kayıtları için ayrıca cleanup
# script'ine bakın (scripts/remove_sl.py).
SL_PREFIXES: set[str] = {
    "ENG", "TLL", "GER", "FRE", "JPN", "SPA", "ITA", "ARA", "CHI",
}


def is_sl_prefix(course_code: str) -> bool:
    """Ders kodu SL fakültesine mi ait? Scraper bu kodları atlamak için kullanır."""
    m = re.match(r"^([A-Z]+)", course_code.upper())
    return bool(m and m.group(1) in SL_PREFIXES)


# CS401L / CHEM201R / PHYS101L gibi Lab + Recitation section kodları.
# Bunlar SUIS'te bağımsız ders gibi görünüyor ama gerçekte ana dersin
# (CS401, CHEM201, PHYS101) bir alt bileşeni. Yorum platformunda gereksiz
# tekrar oluşturup listeyi kalabalıklaştırıyorlar — scraper bunları atlar.
_LAB_RECITATION_RE = re.compile(r"^[A-Z]+\s*\d+[LR]$")


def is_lab_or_recitation(course_code: str) -> bool:
    """
    Ders kodu rakamlardan sonra L veya R harfiyle bitiyor mu?

    True: 'CS 401L', 'CHEM201R', 'PHYS101L'
    False: 'CS 401', 'IR301' (IR prefix, sondaki R değil), 'ENS204'
    """
    return bool(_LAB_RECITATION_RE.match(course_code.upper()))

def get_faculty(course_code: str) -> Optional[str]:
    """Ders kodundan fakülte kısaltmasını döner; bulunamazsa None."""
    prefix = re.match(r"^([A-Z]+)", course_code.upper())
    if not prefix:
        return None
    p = prefix.group(1)
    for code, fac in FACULTY_MAP:
        if p == code:
            return fac
    # Kısmi eşleşme dene (örn. "MFGE" bulunmazsa "MF" ile başlayana bak)
    for code, fac in FACULTY_MAP:
        if p.startswith(code):
            return fac
    return None


# ── Department / konu haritası ────────────────────────────────────────────────
# Ders kodu öneki → okunabilir bölüm adı
DEPT_MAP: dict[str, str] = {
    "CS":   "Computer Science & Engineering",
    "EE":   "Electronics Engineering",
    "IE":   "Industrial Engineering",
    "ME":   "Mechanical Engineering",
    "MAT":  "Mathematics",
    "BIO":  "Biological Sciences & Bioengineering",
    "PHYS": "Physics",
    "CHEM": "Chemistry",
    "ENS":  "Engineering Sciences",
    "IF":   "Computer Science & Engineering",
    "MFGE": "Manufacturing Engineering",
    "NSE":  "Materials Science & Nanoengineering",
    "NANO": "Materials Science & Nanoengineering",
    "HIST": "History",
    "POLS": "Political Science",
    "IR":   "International Relations",
    "SPS":  "Social & Political Sciences",
    "CULT": "Cultural Studies",
    "VA":   "Visual Arts & Visual Communication Design",
    "ECON": "Economics",
    "PSY":  "Psychology",
    "PHIL": "Philosophy",
    "SOC":  "Sociology",
    "HART": "History of Art",
    "COMD": "Communication Design",
    "ART":  "Performing Arts",
    "BA":   "Business Administration",
    "MGMT": "Management Sciences",
    "FIN":  "Finance",
    "MAN":  "Management Sciences",
    "ACC":  "Accounting",
    "MKT":  "Marketing",
    "OPIM": "Operations & Information Management",
    # SL (School of Languages) bölümleri kaldırıldı — yorum platformuna alınmıyor.
}

def get_department(course_code: str) -> Optional[str]:
    """Ders kodundan bölüm adını döner."""
    prefix = re.match(r"^([A-Z]+)", course_code.upper())
    if not prefix:
        return None
    p = prefix.group(1)
    if p in DEPT_MAP:
        return DEPT_MAP[p]
    for key in DEPT_MAP:
        if p.startswith(key):
            return DEPT_MAP[key]
    return None


# ── Dönem yardımcıları ────────────────────────────────────────────────────────

def parse_term_label(label: str) -> Optional[str]:
    """
    Banner dönem etiketini 'Fall 2024' gibi normalize edilmiş formata çevirir.
    Tanımlanamayan / yaz dönemleri için None döner.

    Örnek Banner etiketleri:
      "Fall 2024", "Spring 2025",
      "Güz 2024-2025", "Bahar 2024-2025",
      "2024-2025 Güz Dönemi", "2024-2025 Bahar Dönemi"
    """
    label_l = label.lower().strip()

    # Yaz dönemlerini atla
    summer_keywords = ["summer", "yaz", "summer i", "summer ii", "yaz i", "yaz ii"]
    if any(kw in label_l for kw in summer_keywords):
        return None

    # Sonbahar / Güz
    fall_keywords = ["fall", "güz", "guz", "autumn"]
    spring_keywords = ["spring", "bahar"]

    is_fall   = any(kw in label_l for kw in fall_keywords)
    is_spring = any(kw in label_l for kw in spring_keywords)

    # Yıl bul — 4 haneli sayı(lar)
    years = re.findall(r"\d{4}", label)
    if not years:
        return None

    if is_fall:
        # "Güz 2024-2025" → Fall döneminin başlangıç yılı (2024)
        year = years[0]
        return f"Fall {year}"
    elif is_spring:
        # "Bahar 2024-2025" → Spring döneminin bitiş yılı (2025)
        year = years[-1]
        return f"Spring {year}"

    return None


def is_target_term(normalized_label: str) -> bool:
    """
    Fall 2024 ve sonrasını (yaz hariç) hedefler.
    """
    m = re.match(r"^(Fall|Spring)\s+(\d{4})$", normalized_label)
    if not m:
        return False
    season, year_s = m.group(1), m.group(2)
    year = int(year_s)
    if year < 2024:
        return False
    if year == 2024 and season == "Spring":
        return False  # 2024 Spring'i alma, Fall 2024'ten başla
    return True


# ── HTML parse yardımcıları ───────────────────────────────────────────────────

def clean_text(s: str) -> str:
    """Birden fazla boşluğu ve satır sonlarını temizler."""
    return re.sub(r"\s+", " ", s).strip()


def split_instructors(blob: str) -> list[str]:
    """
    Birden fazla hocayı barındıran bir metni (virgül / ';' / 'and' / '&' / '/'
    ile ayrılmış) ayrı isimlere böler. Boş parçaları atar.
    """
    if not blob:
        return []
    blob = clean_text(blob)
    # Önce parantezli abbr/marker'ları kaldır ki içlerindeki virgüller bizi
    # yanıltmasın. (örn. "Ad Soyad (P, Lab)")
    blob = re.sub(r"\(.*?\)", "", blob)
    pieces = re.split(r"\s*(?:,|;|\band\b|&|/)\s*", blob)
    return [clean_text(p) for p in pieces if clean_text(p)]


def parse_instructor_name(raw: str) -> Optional[str]:
    """
    Tek bir hoca adını temizler ve döner.
      • Parantezli "(P)", "(Primary)", "(Lab)" gibi işaretleri atar.
      • "Staff", "TBA", boş, "-" gibi placeholder'ları None döner.
      • SUIS isimleri "Ad Soyad" formatında verdiği için ters çevirme yapılmaz.
      • Aşırı uzun (>120 karakter) ya da rakam içeren bozuk girdileri reddeder.
    """
    raw = clean_text(raw)
    raw = re.sub(r"\(.*?\)", "", raw)
    raw = clean_text(raw).strip(" ,;-")
    if not raw:
        return None
    if raw.lower() in ("staff", "tba", "to be announced", "to be assigned", "?", "-", "n/a", "na"):
        return None
    if len(raw) > 120:
        return None
    # Hoca adında rakam olmaz (yer/CRN bilgisi sızmışsa filtre)
    if re.search(r"\d", raw):
        return None
    return raw


# ── Banner HTTP işlemleri ─────────────────────────────────────────────────────

def fetch_terms(session: requests.Session) -> list[tuple[str, str]]:
    """
    SUIS ana sayfasından dönem listesini çeker.
    [(term_code, normalized_label), ...] döner.
    """
    log.info("Dönem listesi çekiliyor: %s", SCHED_URL)
    resp = session.get(SCHED_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    select = soup.find("select", {"id": "term_input_id"}) or \
             soup.find("select", {"name": "p_term"}) or \
             soup.find("select", attrs={"name": re.compile(r"term", re.I)})

    if not select:
        # Tüm select'leri dene
        for sel in soup.find_all("select"):
            opts = sel.find_all("option")
            if len(opts) > 2:  # en az 3 seçenek varsa muhtemelen dönem listesi
                select = sel
                break

    if not select:
        log.error("Dönem dropdown'ı bulunamadı. HTML:\n%s", resp.text[:2000])
        return []

    results = []
    for opt in select.find_all("option"):
        code = opt.get("value", "").strip()
        label = clean_text(opt.get_text())
        if not code or code.lower() in ("", "none", "select"):
            continue
        normalized = parse_term_label(label)
        if normalized:
            results.append((code, normalized))
            log.debug("  Dönem: %s → %s (kod: %s)", label, normalized, code)

    return results


def fetch_subjects(session: requests.Session, term_code: str) -> list[str]:
    """
    Verilen dönem için konu (subject) listesini çeker.

    Banner akışı:
      1. Kullanıcı bwckschd.p_disp_dyn_sched ana sayfasında dönem seçer.
      2. Form bwckgens.p_proc_term_date'e POST edilir; bu URL konu seçim
         sayfasını döner. Asıl <select name="sel_subj"> burada bulunur.
    """
    log.info("  Konu listesi çekiliyor (term=%s)...", term_code)
    resp = session.post(
        SUBJECT_URL,
        data={
            "p_calling_proc": "bwckschd.p_disp_dyn_sched",
            "p_term":         term_code,
        },
        headers={**HEADERS, "Referer": SCHED_URL},
        timeout=30,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    subj_select = (
        soup.find("select", {"id": "subj_id"}) or
        soup.find("select", {"name": "sel_subj"}) or
        soup.find("select", attrs={"name": re.compile(r"subj", re.I)})
    )

    if not subj_select:
        log.warning("  Konu dropdown'ı bulunamadı. HTML başlangıcı:\n%s", resp.text[:1500])
        return []

    codes: list[str] = []
    for opt in subj_select.find_all("option"):
        val = (opt.get("value") or "").strip()
        if val and val.lower() not in ("", "all", "dummy"):
            codes.append(val)

    log.info("  %d konu bulundu: %s%s",
             len(codes),
             ", ".join(codes[:8]),
             " ..." if len(codes) > 8 else "")
    return codes


def fetch_courses_for_term(
    session: requests.Session,
    term_code: str,
    subjects: list[str],
) -> list[dict]:
    """
    Belirtilen dönem + konu kombinasyonu için ders listesini çeker ve parse eder.

    Döndürülen her dict:
        {
            "code":        "CS401",
            "name":        "Cryptography",
            "instructors": ["Erkay Savaş"],
        }
    """
    log.info("  Dersler çekiliyor (term=%s, %d konu)...", term_code, len(subjects))
    time.sleep(REQUEST_DELAY)

    # Banner'ın beklediği POST gövdesi.
    # KRİTİK: Banner her "sel_*" alanı için ilk değer olarak "dummy" bekler;
    # gerçek seçim(ler) onun ardından gelir. dummy yoksa Banner formu reddeder
    # ve boş ~17KB'lık bir hata sayfası döner.
    post_data: list[tuple[str, str]] = [
        ("term_in",       term_code),
        ("sel_subj",      "dummy"),   # ← öncü dummy
        ("sel_day",       "dummy"),
        ("sel_schd",      "dummy"),
        ("sel_insm",      "dummy"),
        ("sel_camp",      "dummy"),
        ("sel_levl",      "dummy"),
        ("sel_sess",      "dummy"),
        ("sel_instr",     "dummy"),
        ("sel_ptrm",      "dummy"),
        ("sel_attr",      "dummy"),
        ("sel_crse",      ""),
        ("sel_title",     ""),
        ("sel_from_cred", ""),
        ("sel_to_cred",   ""),
        ("begin_hh",      "0"),
        ("begin_mi",      "0"),
        ("begin_ap",      "a"),
        ("end_hh",        "0"),
        ("end_mi",        "0"),
        ("end_ap",        "a"),
    ]

    for subj in subjects:
        post_data.append(("sel_subj", subj))

    try:
        resp = session.post(
            COURSE_URL,
            data=post_data,
            headers={
                **HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer":      SUBJECT_URL,
            },
            timeout=60,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        log.error("  HTTP hatası: %s", exc)
        return []

    return parse_course_table(resp.text)


def parse_course_table(html: str) -> list[dict]:
    """
    Sabancı SUIS (Banner) ders listesi HTML'inden ders bilgilerini çıkarır.

    Her ders SUIS'te iki ardışık <tr> olarak kodlanır:
      <tr>
        <th class="ddlabel" scope="row">
          <a href="...p_disp_detail_sched?...">
            "Programming Fundamentals - 20605 - CS 201 - B"
            (Ad - CRN - Kod - Şube)
          </a>
        </th>
      </tr>
      <tr>
        <td class="dddefault">
          ... "Course Instructor is: Müge Fidan." kırmızı yazısı ...
          ... iç tablo: "Scheduled Meeting Times" (sütunlardan biri Instructors) ...
        </td>
      </tr>

    Aynı ders birden fazla şubede geçebilir → şubeler birleştirilir,
    farklı hocalar tek listede toplanır.

    Her kayıt:
        {"code": str, "name": str, "instructors": [str]}
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: dict[tuple[str, str], dict] = {}
    results: list[dict] = []

    code_re = re.compile(r"^[A-Z]+\s*\d+[A-Z]?$")
    instr_text_re = re.compile(
        r"Course\s+Instructors?\s+(?:is|are)\s*:\s*([^.]+?)\.",
        re.IGNORECASE,
    )

    for th in soup.find_all("th", class_="ddlabel"):
        a = th.find("a")
        if not a:
            continue
        title_text = clean_text(a.get_text())
        # "Programming Fundamentals - 20605 - CS 201 - B"
        parts = [p.strip() for p in title_text.split(" - ")]
        if len(parts) < 3:
            continue

        # Ders kodu: "CS 201" / "PHYS101" gibi parçayı bul
        code_idx = None
        for idx, p in enumerate(parts):
            if code_re.match(p):
                code_idx = idx
                break
        if code_idx is None:
            continue

        course_code = re.sub(r"\s+", "", parts[code_idx])      # "CS 201" → "CS201"
        course_name = parts[0]                                 # ad ilk parça

        # Gövde: parent <tr>'nin sonraki kardeşindeki <td class="dddefault">
        parent_tr = th.find_parent("tr")
        body_td = None
        if parent_tr is not None:
            next_tr = parent_tr.find_next_sibling("tr")
            if next_tr is not None:
                body_td = next_tr.find("td", class_="dddefault")

        instructors: list[str] = []
        if body_td is not None:
            # 1) "Course Instructor is: NAME." kırmızı yazısı
            body_text = clean_text(body_td.get_text(" "))
            m = instr_text_re.search(body_text)
            if m:
                for piece in split_instructors(m.group(1)):
                    name = parse_instructor_name(piece)
                    if name and name not in instructors:
                        instructors.append(name)

            # 2) Yedek: iç "Scheduled Meeting Times" tablosundan Instructors sütunu
            if not instructors:
                inner_table = body_td.find("table")
                if inner_table is not None:
                    headers = inner_table.find_all("th", class_="ddheader")
                    instr_col = None
                    for idx, hdr in enumerate(headers):
                        if "instructor" in clean_text(hdr.get_text()).lower():
                            instr_col = idx
                            break
                    if instr_col is not None:
                        for row in inner_table.find_all("tr"):
                            cells = row.find_all("td", class_="dddefault")
                            if instr_col < len(cells):
                                cell_text = cells[instr_col].get_text(" ")
                                for piece in split_instructors(cell_text):
                                    name = parse_instructor_name(piece)
                                    if name and name not in instructors:
                                        instructors.append(name)

        key = (course_code, course_name)
        if key in seen:
            for instr in instructors:
                if instr not in seen[key]["instructors"]:
                    seen[key]["instructors"].append(instr)
        else:
            entry = {
                "code":        course_code,
                "name":        course_name,
                "instructors": instructors,
            }
            seen[key] = entry
            results.append(entry)

    if not results:
        log.warning("  Hiç ders parse edilemedi. HTML boyutu: %d karakter", len(html))
        # Hata ayıklama: HTML'i diske dök
        debug_path = os.path.join(os.path.dirname(__file__), "debug_courses.html")
        try:
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(html)
            log.warning("  HTML dökümü: %s", debug_path)
        except OSError as exc:
            log.warning("  HTML dökülemedi: %s", exc)

    return results


# ── Veritabanı işlemleri ──────────────────────────────────────────────────────

def upsert_course(db, code: str, name: str) -> Course:
    """Dersi ekle ya da mevcut olanı döndür; yeni alanları tamamla."""
    course = db.query(Course).filter_by(code=code).first()
    if not course:
        faculty = get_faculty(code)
        dept    = get_department(code)
        course = Course(
            code=code,
            name=name,
            department=dept,
            faculty=faculty,
        )
        db.add(course)
        db.flush()
        log.debug("    [+] Course: %s - %s", code, name)
    else:
        # Eksik alanları tamamla
        changed = False
        if not course.faculty:
            course.faculty = get_faculty(code)
            changed = True
        if not course.department:
            course.department = get_department(code)
            changed = True
        if changed:
            db.flush()
    return course


def upsert_professor(db, name: str, dept: Optional[str], faculty: Optional[str]) -> Professor:
    """Hocayı ekle ya da mevcut olanı döndür."""
    prof = db.query(Professor).filter_by(name=name).first()
    if not prof:
        prof = Professor(name=name, department=dept, faculty=faculty)
        db.add(prof)
        db.flush()
        log.debug("    [+] Professor: %s", name)
    else:
        changed = False
        if not prof.department and dept:
            prof.department = dept
            changed = True
        if not prof.faculty and faculty:
            prof.faculty = faculty
            changed = True
        if changed:
            db.flush()
    return prof


def upsert_professor_course(db, prof: Professor, course: Course, semester: str) -> bool:
    """Hoca-ders-dönem ilişkisini ekle; zaten varsa False döner."""
    exists = db.query(ProfessorCourse).filter_by(
        professor_id=prof.id,
        course_id=course.id,
        semester=semester,
    ).first()
    if exists:
        return False
    db.add(ProfessorCourse(
        professor_id=prof.id,
        course_id=course.id,
        semester=semester,
    ))
    return True


# ── Ana akış ─────────────────────────────────────────────────────────────────

def main():
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ders_forumu",
    )
    # Docker içinden çalıştırılıyorsa host=db, dışarıdan localhost
    # .env'de tanımlıysa otomatik kullanılır
    log.info("Veritabanı: %s", DATABASE_URL)

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    # Bağlantı testi
    with Session() as db:
        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:
            log.error("Veritabanına bağlanılamadı: %s", exc)
            log.error("Docker çalışıyor mu? `docker compose up -d` deneyin.")
            sys.exit(1)

    http = requests.Session()

    # 1) Dönem listesi
    terms = fetch_terms(http)
    if not terms:
        log.error("Dönem listesi boş geldi. SUIS erişilebilir mi?")
        sys.exit(1)

    target_terms = [(code, label) for code, label in terms if is_target_term(label)]
    log.info("Hedef dönemler: %s", [label for _, label in target_terms])

    if not target_terms:
        log.error("Fall 2024 sonrası uygun dönem bulunamadı!")
        sys.exit(1)

    # 2) Her dönem için ders çek
    stats = {"courses_new": 0, "profs_new": 0, "links_new": 0}

    for term_code, semester_label in target_terms:
        log.info("=" * 60)
        log.info("İşleniyor: %s (kod: %s)", semester_label, term_code)

        subjects = fetch_subjects(http, term_code)
        if not subjects:
            log.warning("  Konu listesi alınamadı; bu dönem atlanıyor.")
            continue
        time.sleep(REQUEST_DELAY)
        courses_data = fetch_courses_for_term(http, term_code, subjects)

        if not courses_data:
            log.warning("  Bu dönem için ders verisi bulunamadı.")
            continue

        log.info("  %d ders/bölüm bulundu, veritabanına yazılıyor...", len(courses_data))

        with Session() as db:
            for item in courses_data:
                code   = item["code"]
                name   = item["name"]
                instrs = item["instructors"]

                # SL (School of Languages) prefix'leri sistemden çıkarıldı —
                # ENG/TLL/GER/FRE/JPN/SPA/ITA/ARA/CHI dersleri artık DB'ye
                # yazılmıyor. Eski kayıtları silmek için scripts/remove_sl.py.
                if is_sl_prefix(code):
                    continue

                # Lab (L) ve Recitation (R) section'larını atla — ana ders zaten
                # ayrıca scrape ediliyor; bu suffix'liler ders listesini
                # şişiriyordu (örn. CS401L, CHEM201R).
                if is_lab_or_recitation(code):
                    continue

                # Ders
                before_c = db.query(Course).count()
                course = upsert_course(db, code, name)
                if db.query(Course).count() > before_c:
                    stats["courses_new"] += 1

                # Hoca(lar)
                for instr_name in instrs:
                    if not instr_name:
                        continue
                    if len(instr_name) > 120:
                        log.warning("    [!] Hoca adı çok uzun, atlanıyor (%s): %r",
                                    code, instr_name[:80])
                        continue
                    dept   = get_department(code)
                    fac    = get_faculty(code)
                    before_p = db.query(Professor).count()
                    prof = upsert_professor(db, instr_name, dept, fac)
                    if db.query(Professor).count() > before_p:
                        stats["profs_new"] += 1

                    # Bağlantı
                    added = upsert_professor_course(db, prof, course, semester_label)
                    if added:
                        stats["links_new"] += 1

            db.commit()
            log.info("  ✓ Commit tamamlandı.")

    # 3) Özet
    log.info("=" * 60)
    log.info("SCRAPE TAMAMLANDI")
    log.info("  Yeni ders       : %d", stats["courses_new"])
    log.info("  Yeni hoca       : %d", stats["profs_new"])
    log.info("  Yeni hoca-ders  : %d", stats["links_new"])

    # Genel tablo sayıları
    with Session() as db:
        c = db.execute(text("SELECT COUNT(*) FROM courses")).scalar()
        p = db.execute(text("SELECT COUNT(*) FROM professors")).scalar()
        pc = db.execute(text("SELECT COUNT(*) FROM professor_courses")).scalar()
    log.info("  Toplam courses          : %d", c)
    log.info("  Toplam professors       : %d", p)
    log.info("  Toplam professor_courses: %d", pc)


if __name__ == "__main__":
    main()
