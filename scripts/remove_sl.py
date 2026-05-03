"""
SL (School of Languages) temizlik script'i.

Sistemden SL fakültesi kaldırıldığı için mevcut DB'deki SL kayıtlarını siler:
  - faculty='SL' olan tüm Course'lar
  - faculty='SL' olan tüm Professor'lar (başka bir fakültede dersi yoksa)
  - bunlara bağlı ProfessorCourse ve Review satırları (FK CASCADE / SET NULL)

Hangi kayıtları silmediğine dair raporu önce ekrana basar; gerçekten silmek
için `--apply` bayrağıyla çalıştır.

Kullanım:
    python scripts/remove_sl.py            # dry-run (sadece raporlar)
    python scripts/remove_sl.py --apply    # gerçekten siler

Not: Reviewlar Course/Professor FK'larında ondelete='SET NULL' olduğu için
silinmez, sadece referansları boşalır. Tamamen orphan review kalmasın diye
review.professor_id=NULL AND review.course_id=NULL olan satırlar da silinir.
"""
from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from app.models import Professor, Course, ProfessorCourse  # noqa: E402
from app.models.review import Review  # noqa: E402


SL_PREFIXES = {"ENG", "TLL", "GER", "FRE", "JPN", "SPA", "ITA", "ARA", "CHI"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove SL faculty data")
    parser.add_argument("--apply", action="store_true", help="Gerçekten sil (default: dry-run)")
    args = parser.parse_args()

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ders_forumu",
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        # SL course'lar — hem faculty='SL' hem prefix bazlı yakala (eski kayıtlar
        # için faculty boş olabilir).
        sl_courses = (
            db.query(Course)
            .filter(
                or_(
                    Course.faculty == "SL",
                    *[Course.code.like(f"{p}%") for p in SL_PREFIXES],
                )
            )
            .all()
        )

        # SL professor'lar — faculty='SL' (başka fakültede dersi olanları
        # koruyacağız ki yanlışlıkla bir CS hocasını silmeyelim).
        sl_profs = db.query(Professor).filter(Professor.faculty == "SL").all()

        # Hangi hocalar tamamen SL'de? = sadece SL course'larda dersi olan
        sl_course_ids = {c.id for c in sl_courses}
        truly_sl_profs: list[Professor] = []
        for p in sl_profs:
            other_links = (
                db.query(ProfessorCourse)
                .filter(
                    ProfessorCourse.professor_id == p.id,
                    ~ProfessorCourse.course_id.in_(sl_course_ids) if sl_course_ids else True,
                )
                .first()
            )
            if other_links is None:
                truly_sl_profs.append(p)

        # Bu course'lara bağlı linkler / yorumlar
        link_count = (
            db.query(ProfessorCourse)
            .filter(ProfessorCourse.course_id.in_(sl_course_ids))
            .count()
            if sl_course_ids
            else 0
        )
        review_count = (
            db.query(Review)
            .filter(Review.course_id.in_(sl_course_ids))
            .count()
            if sl_course_ids
            else 0
        )

        print("─── SL temizlik raporu " + "─" * 40)
        print(f"  SL course'lar           : {len(sl_courses):>4}")
        print(f"  SL hocalar (sadece SL)  : {len(truly_sl_profs):>4}")
        print(f"  Etkilenen ders-hoca     : {link_count:>4}")
        print(f"  Etkilenen review (NULL'lanır): {review_count:>4}")
        print("─" * 60)

        if not args.apply:
            print("Dry-run modu. Gerçek silme için: python scripts/remove_sl.py --apply")
            return 0

        # Sil
        for c in sl_courses:
            db.delete(c)  # CASCADE → professor_courses, SET NULL → reviews
        for p in truly_sl_profs:
            db.delete(p)

        # Tamamen orphan kalan review'lar (course_id ve professor_id ikisi de NULL)
        orphans = (
            db.query(Review)
            .filter(Review.professor_id.is_(None), Review.course_id.is_(None))
            .all()
        )
        for r in orphans:
            db.delete(r)

        db.commit()
        print(f"✓ Silindi. Orphan review temizlendi: {len(orphans)}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
