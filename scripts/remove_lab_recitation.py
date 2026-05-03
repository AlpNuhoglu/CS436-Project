"""
Lab (L) ve Recitation (R) section'larını DB'den temizle.

CS401L / CHEM201R / PHYS101L gibi kodlar SUIS'te ana dersin alt section'ı.
Yorum platformunda ana ders (CS401, CHEM201) zaten var; bunlar listeyi
şişiriyor. Eşleşme: rakamlardan sonra TEK harf 'L' veya 'R'.

Önce dry-run rapor verir; gerçek silme için `--apply`.

Kullanım:
    python scripts/remove_lab_recitation.py            # rapor
    python scripts/remove_lab_recitation.py --apply    # gerçekten sil

Silinen course'a bağlı:
  - ProfessorCourse satırları CASCADE ile silinir.
  - Review satırları course_id'yi NULL yapar (FK ondelete='SET NULL').
    Hem prof hem ders NULL olan tamamen orphan review'lar da silinir.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from app.models import Professor, Course, ProfessorCourse  # noqa: E402
from app.models.review import Review  # noqa: E402


# Ana ders + L/R suffix paterni — boşluklu ve boşluksuz iki form
_PATTERN = re.compile(r"^[A-Z]+\s*\d+[LR]$")


def is_lab_or_recitation(code: str) -> bool:
    return bool(_PATTERN.match(code.upper().strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove L/R suffix courses")
    parser.add_argument("--apply", action="store_true", help="Gerçekten sil (default: dry-run)")
    args = parser.parse_args()

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ders_forumu",
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        # Önce LIKE ile ön-eleme yap (DB'ye yük binmesin), sonra Python'da
        # tam regex eşleşmesi: "IR301" gibi sondaki R harfi prefix'in parçası
        # olan kodlar düşmesin.
        candidates = (
            db.query(Course)
            .filter(or_(Course.code.like("%L"), Course.code.like("%R")))
            .all()
        )
        targets = [c for c in candidates if is_lab_or_recitation(c.code)]
        target_ids = [c.id for c in targets]

        # Etkilenen ilişkiler / yorumlar
        link_count = (
            db.query(ProfessorCourse)
            .filter(ProfessorCourse.course_id.in_(target_ids))
            .count()
            if target_ids
            else 0
        )
        affected_reviews = (
            db.query(Review)
            .filter(Review.course_id.in_(target_ids))
            .count()
            if target_ids
            else 0
        )

        # Eşleşen ama atlanan örnekler (kullanıcıyı bilgilendir)
        skipped = [c.code for c in candidates if c not in targets]

        print("─── Lab / Recitation temizlik raporu " + "─" * 24)
        print(f"  Aday (kodu L/R ile biten)   : {len(candidates):>4}")
        print(f"  Hedef (rakam + L/R)         : {len(targets):>4}")
        if skipped:
            print(f"  Atlandı (prefix harfi olabilir, ders kodu rakamla bitiyor):")
            for code in sorted(skipped)[:10]:
                print(f"      {code}")
            if len(skipped) > 10:
                print(f"      … ve {len(skipped) - 10} tane daha")
        print(f"  Etkilenen ders-hoca link'i  : {link_count:>4}")
        print(f"  Etkilenen yorum (NULL'lanır): {affected_reviews:>4}")
        print("─" * 60)

        if targets:
            print("İlk 15 hedef ders kodu:")
            for c in targets[:15]:
                print(f"  {c.code:<10} {c.name[:50]}")
            if len(targets) > 15:
                print(f"  … ve {len(targets) - 15} tane daha")
        print("─" * 60)

        if not args.apply:
            print("Dry-run modu. Silmek için: python scripts/remove_lab_recitation.py --apply")
            return 0

        # Sil
        for c in targets:
            db.delete(c)

        # Tamamen orphan review'lar (hem course_id hem professor_id NULL)
        orphans = (
            db.query(Review)
            .filter(Review.professor_id.is_(None), Review.course_id.is_(None))
            .all()
        )
        for r in orphans:
            db.delete(r)

        db.commit()
        print(f"✓ {len(targets)} ders silindi. Orphan review temizlendi: {len(orphans)}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
