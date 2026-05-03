"""
Veritabanı seed script.

Gerçekçi Sabancı Üniversitesi verilerini tablolara ekler:
  - 13 hoca  (FENS / FASS / SBS — SL kaldırıldı)
  - 26 ders  (fakülte, zorluk, haftalık iş yükü bilgileriyle)
  - Hoca-ders ilişkileri (dönem bilgisiyle)

Kullanım:
  python seed.py

Mevcut veriler silinmez; idempotent çalışır.
Yeni alanlar (faculty/difficulty/workload_hours) mevcut kayıtlarda None ise
bu script eksik değerleri günceller (UPDATE ile).
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models import Professor, Course, ProfessorCourse  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.review import Review  # noqa: E402

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/ders_forumu",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)


# ── Seed verisi ──────────────────────────────────────────────────────────────
#
# Fakülte kısaltmaları:
#   FENS = Faculty of Engineering & Natural Sciences
#   FASS = Faculty of Arts & Social Sciences
#   SBS  = School of Management
# (SL = School of Languages — sistemden çıkarıldı.)

PROFESSORS = [
    # FENS
    {"name": "Hüsnü Yenigün",      "title": "Prof. Dr.",    "department": "Computer Science & Engineering", "faculty": "FENS"},
    {"name": "Erkay Savaş",        "title": "Prof. Dr.",    "department": "Computer Science & Engineering", "faculty": "FENS"},
    {"name": "Cemal Yılmaz",       "title": "Prof. Dr.",    "department": "Computer Science & Engineering", "faculty": "FENS"},
    {"name": "Yücel Saygın",       "title": "Prof. Dr.",    "department": "Computer Science & Engineering", "faculty": "FENS"},
    {"name": "Özgür Gürbüz",       "title": "Prof. Dr.",    "department": "Electronics Engineering",        "faculty": "FENS"},
    {"name": "Ahmet Oğuz Akyüz",   "title": "Assoc. Prof.", "department": "Computer Science & Engineering", "faculty": "FENS"},
    {"name": "Hazım Kemal Ekenel", "title": "Assoc. Prof.", "department": "Computer Science & Engineering", "faculty": "FENS"},
    {"name": "Tuna Tuğcu",         "title": "Prof. Dr.",    "department": "Computer Science & Engineering", "faculty": "FENS"},
    {"name": "Kamer Kaya",         "title": "Assoc. Prof.", "department": "Computer Science & Engineering", "faculty": "FENS"},
    # FASS
    {"name": "Ayşe Demir",         "title": "Assoc. Prof.", "department": "Political Science",              "faculty": "FASS"},
    {"name": "Selin Öztürk",       "title": "Assist. Prof.","department": "Visual Arts & Visual Communication", "faculty": "FASS"},
    # SBS
    {"name": "Can Akın",           "title": "Prof. Dr.",    "department": "Management Sciences",            "faculty": "SBS"},
    {"name": "Deniz Aksoy",        "title": "Assoc. Prof.", "department": "Finance",                        "faculty": "SBS"},
    # SL (School of Languages) sistemden kaldırıldı.
]

# difficulty: 1 (kolay) – 5 (çok zor)
# workload_hours: haftalık ders + ödev + çalışma saati tahmini
COURSES = [
    # FENS — CS
    {"code": "CS301",  "name": "Algorithms",                                "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 11},
    {"code": "CS303",  "name": "Logic and Digital Systems",                 "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 3, "workload_hours": 9},
    {"code": "CS306",  "name": "Database Systems",                          "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 3, "workload_hours": 10},
    {"code": "CS308",  "name": "Computer Organization",                     "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 12},
    {"code": "CS401",  "name": "Cryptography",                              "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 5, "workload_hours": 14},
    {"code": "CS402",  "name": "Software Verification",                     "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 12},
    {"code": "CS421",  "name": "Machine Learning",                          "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 13},
    {"code": "CS436",  "name": "Cloud Computing & Distributed Systems",     "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 14},
    {"code": "CS442",  "name": "Computer Vision",                           "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 12},
    {"code": "CS458",  "name": "Computer Security",                         "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 11},
    {"code": "CS461",  "name": "Artificial Intelligence",                   "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 4, "workload_hours": 12},
    {"code": "CS464",  "name": "Introduction to Machine Learning",          "department": "Computer Science & Engineering", "faculty": "FENS", "difficulty": 3, "workload_hours": 10},
    # FENS — ENS / EE
    {"code": "ENS204", "name": "Introduction to Probability",               "department": "Engineering Sciences",           "faculty": "FENS", "difficulty": 4, "workload_hours": 10},
    {"code": "ENS208", "name": "Introduction to Linear Algebra",            "department": "Engineering Sciences",           "faculty": "FENS", "difficulty": 3, "workload_hours": 9},
    {"code": "ENS311", "name": "Signals & Systems",                         "department": "Engineering Sciences",           "faculty": "FENS", "difficulty": 4, "workload_hours": 12},
    {"code": "EE402",  "name": "Wireless Communications",                   "department": "Electronics Engineering",        "faculty": "FENS", "difficulty": 4, "workload_hours": 11},
    {"code": "EE541",  "name": "Digital Image Processing",                  "department": "Electronics Engineering",        "faculty": "FENS", "difficulty": 4, "workload_hours": 12},
    {"code": "IF100",  "name": "Computational Approaches to Problem Solving","department": "Computer Science & Engineering","faculty": "FENS", "difficulty": 2, "workload_hours": 7},
    # FASS
    {"code": "SPS101", "name": "Humanity and Society I",                    "department": "Social & Political Sciences",    "faculty": "FASS", "difficulty": 2, "workload_hours": 6},
    {"code": "POLS210","name": "Introduction to Political Theory",          "department": "Political Science",              "faculty": "FASS", "difficulty": 3, "workload_hours": 8},
    {"code": "IR301",  "name": "International Relations Theory",            "department": "Political Science",              "faculty": "FASS", "difficulty": 3, "workload_hours": 9},
    {"code": "VA101",  "name": "Introduction to Visual Arts",               "department": "Visual Arts & Visual Communication","faculty": "FASS", "difficulty": 2, "workload_hours": 7},
    {"code": "VA203",  "name": "Drawing and Composition",                   "department": "Visual Arts & Visual Communication","faculty": "FASS", "difficulty": 3, "workload_hours": 8},
    # SBS
    {"code": "MGMT301","name": "Principles of Management",                  "department": "Management Sciences",            "faculty": "SBS",  "difficulty": 3, "workload_hours": 8},
    {"code": "MGMT403","name": "Strategic Management",                      "department": "Management Sciences",            "faculty": "SBS",  "difficulty": 3, "workload_hours": 8},
    {"code": "FIN302", "name": "Corporate Finance",                         "department": "Finance",                        "faculty": "SBS",  "difficulty": 4, "workload_hours": 10},
    # SL (Diller Okulu) dersleri kaldırıldı — platformda yer almıyor.
]

# (hoca_adı, ders_kodu, dönem)
PROFESSOR_COURSES = [
    ("Hüsnü Yenigün",      "CS303",   "Spring 2025"),
    ("Hüsnü Yenigün",      "CS402",   "Fall 2024"),
    ("Erkay Savaş",        "CS401",   "Spring 2025"),
    ("Erkay Savaş",        "CS458",   "Fall 2024"),
    ("Cemal Yılmaz",       "CS306",   "Spring 2025"),
    ("Cemal Yılmaz",       "CS306",   "Fall 2024"),
    ("Yücel Saygın",       "CS421",   "Spring 2025"),
    ("Yücel Saygın",       "CS464",   "Fall 2024"),
    ("Özgür Gürbüz",       "EE402",   "Spring 2025"),
    ("Özgür Gürbüz",       "ENS311",  "Fall 2024"),
    ("Ahmet Oğuz Akyüz",   "CS442",   "Spring 2025"),
    ("Ahmet Oğuz Akyüz",   "EE541",   "Fall 2024"),
    ("Hazım Kemal Ekenel", "CS442",   "Fall 2024"),
    ("Hazım Kemal Ekenel", "CS461",   "Spring 2025"),
    ("Tuna Tuğcu",         "CS436",   "Spring 2025"),
    ("Tuna Tuğcu",         "CS308",   "Fall 2024"),
    ("Kamer Kaya",         "CS301",   "Spring 2025"),
    ("Kamer Kaya",         "IF100",   "Fall 2024"),
    ("Kamer Kaya",         "IF100",   "Spring 2025"),
    # FASS
    ("Ayşe Demir",         "POLS210", "Spring 2025"),
    ("Ayşe Demir",         "IR301",   "Fall 2024"),
    ("Selin Öztürk",       "VA101",   "Spring 2025"),
    ("Selin Öztürk",       "VA203",   "Fall 2024"),
    # SBS
    ("Can Akın",           "MGMT301", "Fall 2024"),
    ("Can Akın",           "MGMT403", "Spring 2025"),
    ("Deniz Aksoy",        "FIN302",  "Spring 2025"),
    # SL ders/hoca eşleşmeleri kaldırıldı.
]


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def seed_professors(db) -> dict[str, Professor]:
    """Hocaları ekle. Mevcut olan kayıtların faculty alanı boşsa doldur."""
    name_to_prof: dict[str, Professor] = {}
    existing = {p.name: p for p in db.query(Professor).all()}

    added = 0
    updated = 0
    for data in PROFESSORS:
        if data["name"] in existing:
            prof = existing[data["name"]]
            # Yeni alanları doldur (varolan kayıtlar migrasyondan sonra None olabilir)
            changed = False
            if prof.faculty is None and data.get("faculty"):
                prof.faculty = data["faculty"]
                changed = True
            if prof.department is None and data.get("department"):
                prof.department = data["department"]
                changed = True
            if changed:
                updated += 1
            name_to_prof[data["name"]] = prof
            continue
        prof = Professor(**data)
        db.add(prof)
        db.flush()
        name_to_prof[data["name"]] = prof
        added += 1

    print(f"  Professors : {added} yeni · {updated} güncellendi · {len(existing)} zaten vardı.")
    return name_to_prof


def seed_courses(db) -> dict[str, Course]:
    """Dersleri ekle. Mevcut kayıtların yeni alanlarını (faculty/difficulty/workload) doldur."""
    code_to_course: dict[str, Course] = {}
    existing = {c.code: c for c in db.query(Course).all()}

    added = 0
    updated = 0
    for data in COURSES:
        if data["code"] in existing:
            course = existing[data["code"]]
            changed = False
            for k in ("faculty", "difficulty", "workload_hours"):
                if getattr(course, k) is None and data.get(k) is not None:
                    setattr(course, k, data[k])
                    changed = True
            if changed:
                updated += 1
            code_to_course[data["code"]] = course
            continue
        course = Course(**data)
        db.add(course)
        db.flush()
        code_to_course[data["code"]] = course
        added += 1

    print(f"  Courses    : {added} yeni · {updated} güncellendi · {len(existing)} zaten vardı.")
    return code_to_course


# ── Demo kullanıcılar ve yorumlar ────────────────────────────────────────────
#
# HomePage'deki "trending / en çok yorumlu / son yorum" bölümleri canlı veri
# gerektiriyor. Demo olması için birkaç kullanıcı ve yorum yaratıyoruz.
# Cognito kullanılmadan "demo" kullanıcıları eklenir.

# Demo kullanıcılar artık sadece username + password_hash ile yaratılır
# (email DB'de tutulmuyor; gerçek kayıtta sadece geçici tablodadır).
# Demo şifresi: "demo1234" (tüm demo kullanıcılar için aynı).
DEMO_USERS = [
    {"username": "ceren"},
    {"username": "ahmet"},
    {"username": "zeynep"},
    {"username": "mert"},
    {"username": "elif"},
]
DEMO_PASSWORD = "demo1234"

# (username, professor_name, course_code, rating, difficulty, workload_hours, comment, days_ago, anon)
# difficulty: 1 (çok kolay) – 5 (çok zor) | workload_hours: haftalık saat (0-60)
DEMO_REVIEWS = [
    # Kamer Kaya / CS301 — yoğun yorum trafiği → trending
    ("ceren",  "Kamer Kaya",        "CS301",   5, 4, 12, "Dersin akışı çok iyi, ödevler zor ama adil. Çok şey öğrendim.",                     2,  False),
    ("ahmet",  "Kamer Kaya",        "CS301",   5, 5, 14, "Kamer hoca sınıfta gerçekten zaman ayırıyor. Kesinlikle öneririm.",                 4,  False),
    ("zeynep", "Kamer Kaya",        "CS301",   4, 4, 11, "Ödevleri yoğun ama hoca sorulara hemen cevap veriyor. Başarılı bir ders.",          1,  True),
    ("mert",   "Kamer Kaya",        "CS301",   5, 4, 13, "Algoritmalar konusu çok net anlatılıyor. Beklediğimden fazlasını aldım.",           6,  False),
    ("elif",   "Kamer Kaya",        "CS301",   4, 3, 10, "Proje kısmı çok öğretici. Grup çalışması biraz zorlayıcı olabilir.",                3,  False),

    # Erkay Savaş / CS401 - CS458
    ("ceren",  "Erkay Savaş",       "CS401",   5, 5, 15, "Kriptografi derslerinin en iyisi. Hoca konuya hakim, adil sınav.",                  8,  False),
    ("ahmet",  "Erkay Savaş",       "CS401",   4, 5, 16, "Biraz yoğun ama kesinlikle değer. Örnekler çok iyi.",                               12, False),
    ("elif",   "Erkay Savaş",       "CS458",   5, 4, 11, "Kavramsal anlatım mükemmel. Vize zordu ama hazırlanınca sorun olmuyor.",            20, False),

    # Hüsnü Yenigün / CS303
    ("mert",   "Hüsnü Yenigün",     "CS303",   5, 3, 9,  "Temelleri güzel oturtuyor. Başlangıç seviyesi için mükemmel.",                      10, False),
    ("zeynep", "Hüsnü Yenigün",     "CS303",   4, 3, 10, "Biraz teorik ama hoca çok ilgili. Ofis saatleri çok faydalı.",                      15, False),

    # Ahmet Oğuz Akyüz / CS442
    ("elif",   "Ahmet Oğuz Akyüz",  "CS442",   5, 4, 12, "Computer vision dersinin efsane hali. Projeler çok yaratıcı.",                      5,  False),
    ("ceren",  "Ahmet Oğuz Akyüz",  "CS442",   4, 4, 13, "Rendering konusunda çok şey öğrendim.",                                             18, True),

    # Ayşe Demir (FASS)
    ("ahmet",  "Ayşe Demir",        "POLS210", 4, 3, 8,  "Tartışma ortamı çok iyi. Okumalar yoğun ama keyifli.",                              7,  False),
    ("zeynep", "Ayşe Demir",        "POLS210", 5, 2, 7,  "Siyaset dersleri içinde en iyisi. Hoca konulara farklı açıdan bakıyor.",            11, False),

    # Can Akın (SBS) - orta yoğunluk
    ("mert",   "Can Akın",          "MGMT301", 4, 3, 8,  "Finans konularında iyi bir temel sağlıyor. Sunumu akıcı.",                          9,  False),
    ("elif",   "Can Akın",          "MGMT301", 3, 4, 9,  "Konular güzel ama sınavlar biraz beklenmedik yönde zor.",                           14, True),

    # Selin Öztürk (FASS - Visual Arts)
    ("ceren",  "Selin Öztürk",      "VA101",   5, 2, 6,  "Yaratıcı düşünmeyi gerçekten öğretiyor. Studio atmosferi harika.",                  3,  False),

    # Jane Roberts (SL)
    ("zeynep", "Jane Roberts",      "ENG101",  4, 2, 5,  "İngilizce için sağlam bir başlangıç. Hoca çok sabırlı.",                            13, False),
    ("ahmet",  "Jane Roberts",      "ENG101",  4, 2, 4,  "Yazılı ödevlerde detaylı geri dönüş veriyor.",                                      22, False),

    # Cemal Yılmaz / CS306 — tek düşük puan
    ("mert",   "Cemal Yılmaz",      "CS306",   3, 4, 12, "Ders içeriği iyi ama temposu çok hızlı. Takip etmek zorlayıcı.",                    19, True),
]


def seed_users(db) -> dict[str, User]:
    """Demo kullanıcılar ekle (idempotent). Şifre: 'demo1234'."""
    from app.auth.local import hash_password

    existing = {u.username: u for u in db.query(User).all()}
    added = 0
    pw_hash = hash_password(DEMO_PASSWORD)
    for u in DEMO_USERS:
        if u["username"] in existing:
            continue
        user = User(
            username=u["username"],
            password_hash=pw_hash,
        )
        db.add(user)
        db.flush()
        existing[u["username"]] = user
        added += 1
    print(f"  Users      : {added} yeni · {len(existing)} toplam (demo şifre: '{DEMO_PASSWORD}').")
    return existing


def seed_reviews(
    db,
    users: dict[str, User],
    name_to_prof: dict[str, Professor],
    code_to_course: dict[str, Course],
) -> None:
    """Demo yorumlar ekle (idempotent — user/prof/course üçlüsüne göre)."""
    from datetime import datetime, timedelta, timezone

    existing_keys = {
        (r.user_id, r.professor_id, r.course_id)
        for r in db.query(Review).all()
    }

    now = datetime.now(timezone.utc)
    added = 0
    skipped = 0
    for (username, prof_name, course_code, rating, difficulty,
         workload_hours, comment, days_ago, anon) in DEMO_REVIEWS:
        user = users.get(username)
        prof = name_to_prof.get(prof_name)
        course = code_to_course.get(course_code)
        if not user or not prof or not course:
            print(f"  [UYARI] Review atlandı: {username!r} / {prof_name!r} / {course_code!r}")
            continue
        key = (user.id, prof.id, course.id)
        if key in existing_keys:
            skipped += 1
            continue

        created = now - timedelta(days=days_ago)
        review = Review(
            user_id=user.id,
            professor_id=prof.id,
            course_id=course.id,
            rating=rating,
            difficulty=difficulty,
            workload_hours=workload_hours,
            comment=comment,
            is_anonymous=anon,
            created_at=created,
            updated_at=created,
        )
        db.add(review)
        existing_keys.add(key)
        added += 1

    print(f"  Reviews    : {added} yeni · {skipped} zaten vardı.")


def seed_professor_courses(
    db,
    name_to_prof: dict[str, Professor],
    code_to_course: dict[str, Course],
) -> None:
    """Hoca-ders ilişkilerini ekle, tekrarları atla."""
    existing_keys = {
        (pc.professor_id, pc.course_id, pc.semester)
        for pc in db.query(ProfessorCourse).all()
    }

    added = 0
    skipped = 0
    for prof_name, course_code, semester in PROFESSOR_COURSES:
        prof = name_to_prof.get(prof_name)
        course = code_to_course.get(course_code)
        if not prof or not course:
            print(f"  [UYARI] Bulunamadı: {prof_name!r} / {course_code!r}")
            continue

        key = (prof.id, course.id, semester)
        if key in existing_keys:
            skipped += 1
            continue

        db.add(ProfessorCourse(professor_id=prof.id, course_id=course.id, semester=semester))
        existing_keys.add(key)
        added += 1

    print(f"  Prof-Course: {added} yeni · {skipped} zaten vardı.")


# ── Ana fonksiyon ────────────────────────────────────────────────────────────

def main():
    print(f"\nBağlanılıyor → {DATABASE_URL}\n")
    with Session() as db:
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            print(f"[HATA] Veritabanına bağlanılamadı: {e}")
            sys.exit(1)

        print("Seed başlıyor...")
        name_to_prof = seed_professors(db)
        code_to_course = seed_courses(db)
        seed_professor_courses(db, name_to_prof, code_to_course)
        users = seed_users(db)
        db.flush()
        seed_reviews(db, users, name_to_prof, code_to_course)
        db.commit()

    print("\nSeed tamamlandı ✓\n")
    _print_summary()


def _print_summary():
    with Session() as db:
        prof_count   = db.query(Professor).count()
        course_count = db.query(Course).count()
        pc_count     = db.query(ProfessorCourse).count()
        user_count   = db.query(User).count()
        rev_count    = db.query(Review).count()

        fac_prof = dict(db.execute(text("""
            SELECT COALESCE(faculty,'—'), COUNT(*) FROM professors GROUP BY 1 ORDER BY 1
        """)).all())
        fac_course = dict(db.execute(text("""
            SELECT COALESCE(faculty,'—'), COUNT(*) FROM courses GROUP BY 1 ORDER BY 1
        """)).all())

    print("── Veritabanı özeti ───────────────────────")
    print(f"  Professors      : {prof_count}   {fac_prof}")
    print(f"  Courses         : {course_count}   {fac_course}")
    print(f"  Professor-Course: {pc_count}")
    print(f"  Users           : {user_count}")
    print(f"  Reviews         : {rev_count}")
    print("───────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
