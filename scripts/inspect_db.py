"""
DB teşhis: fakülte / prefix dağılımı.

"FENS'te CS dersi yok, BIO/CHEM var" gibi şikayetlerde önce DB'de gerçekten
ne olduğuna bakmak için. Sadece SELECT yapar; veriyi değiştirmez.

Kullanım:
    python scripts/inspect_db.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter

from dotenv import load_dotenv
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from app.models import Professor, Course, ProfessorCourse  # noqa: E402
from app.models.review import Review  # noqa: E402


def prefix_of(code: str) -> str:
    m = re.match(r"^([A-Z]+)", code.upper())
    return m.group(1) if m else "?"


def main() -> int:
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ders_forumu",
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        n_courses = db.query(Course).count()
        n_profs = db.query(Professor).count()
        n_links = db.query(ProfessorCourse).count()
        n_reviews = db.query(Review).count()

        print("─── DB özet " + "─" * 50)
        print(f"  Toplam ders        : {n_courses}")
        print(f"  Toplam hoca        : {n_profs}")
        print(f"  Hoca-ders bağ      : {n_links}")
        print(f"  Yorum              : {n_reviews}")
        print("─" * 60)

        print("\n─── Fakülteye göre ders sayısı " + "─" * 30)
        rows = (
            db.query(Course.faculty, func.count(Course.id))
            .group_by(Course.faculty)
            .order_by(func.count(Course.id).desc())
            .all()
        )
        for fac, cnt in rows:
            print(f"  {str(fac or '(NULL)'):>8} : {cnt:>4}")

        print("\n─── Prefix'e göre ders sayısı (Top 25) " + "─" * 22)
        all_codes = [c.code for c in db.query(Course.code).all()]
        prefix_counts = Counter(prefix_of(c) for c in all_codes)
        for p, cnt in prefix_counts.most_common(25):
            print(f"  {p:>6} : {cnt:>4}")

        print("\n─── CS dersleri (varsa) " + "─" * 35)
        cs_courses = (
            db.query(Course)
            .filter(Course.code.like("CS%"))
            .order_by(Course.code)
            .limit(20)
            .all()
        )
        if not cs_courses:
            print("  ⚠ DB'de hiç CS dersi yok!")
        else:
            for c in cs_courses:
                print(f"  {c.code:<8} {c.faculty or '?':<5} {c.name[:50]}")

        print("\n─── FASS dersleri (varsa, ilk 20) " + "─" * 25)
        fass_courses = (
            db.query(Course)
            .filter(Course.faculty == "FASS")
            .order_by(Course.code)
            .limit(20)
            .all()
        )
        if not fass_courses:
            print("  ⚠ DB'de hiç FASS dersi yok!")
        else:
            for c in fass_courses:
                print(f"  {c.code:<8} {c.name[:60]}")

        print("\n─── Dönem dağılımı (professor_courses) " + "─" * 21)
        sem_rows = (
            db.query(ProfessorCourse.semester, func.count(ProfessorCourse.id))
            .group_by(ProfessorCourse.semester)
            .order_by(ProfessorCourse.semester.desc())
            .all()
        )
        for sem, cnt in sem_rows:
            print(f"  {str(sem or '(NULL)'):<20} : {cnt:>4}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
