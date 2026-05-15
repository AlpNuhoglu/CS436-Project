"""
force_seed.py — Minimal standalone seed for Ders Forumu.

Inserts 3 professors, 3 courses, and links them in professor_courses.
Idempotent: skips records that already exist.

Usage (local):
    python force_seed.py

Usage (inside Docker api container):
    docker exec ders_forumu_api python force_seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

from app.database import SessionLocal
from app.models.professor import Professor
from app.models.course import Course
from app.models.professor_course import ProfessorCourse

# ── Seed data ─────────────────────────────────────────────────────────────────

PROFESSORS = [
    {
        "name": "Kamer Kaya",
        "title": "Assoc. Prof.",
        "department": "Computer Science & Engineering",
        "faculty": "FENS",
    },
    {
        "name": "Ayşe Demir",
        "title": "Assoc. Prof.",
        "department": "Political Science",
        "faculty": "FASS",
    },
    {
        "name": "Can Akın",
        "title": "Prof. Dr.",
        "department": "Management Sciences",
        "faculty": "SBS",
    },
]

COURSES = [
    {
        "code": "CS306",
        "name": "Database Systems",
        "department": "Computer Science & Engineering",
        "faculty": "FENS",
        "difficulty": 3,
        "workload_hours": 10,
    },
    {
        "code": "IF100",
        "name": "Computational Approaches to Problem Solving",
        "department": "Computer Science & Engineering",
        "faculty": "FENS",
        "difficulty": 2,
        "workload_hours": 7,
    },
    {
        "code": "POLS210",
        "name": "Introduction to Political Theory",
        "department": "Political Science",
        "faculty": "FASS",
        "difficulty": 3,
        "workload_hours": 8,
    },
]

# (professor name, course code, semester)
LINKS = [
    ("Kamer Kaya",  "CS306",   "Spring 2025"),
    ("Kamer Kaya",  "IF100",   "Fall 2024"),
    ("Ayşe Demir",  "POLS210", "Spring 2025"),
    ("Can Akın",    "CS306",   "Fall 2024"),
]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"[ERROR] Cannot connect to DB: {exc}")
        db.close()
        sys.exit(1)

    try:
        # --- Professors ---
        existing_profs = {p.name: p for p in db.query(Professor).all()}
        name_to_prof: dict[str, Professor] = {}
        added_p = 0
        for data in PROFESSORS:
            if data["name"] in existing_profs:
                name_to_prof[data["name"]] = existing_profs[data["name"]]
                continue
            prof = Professor(**data)
            db.add(prof)
            db.flush()
            name_to_prof[data["name"]] = prof
            added_p += 1
        print(f"Professors : {added_p} added · {len(existing_profs)} already existed")

        # --- Courses ---
        existing_courses = {c.code: c for c in db.query(Course).all()}
        code_to_course: dict[str, Course] = {}
        added_c = 0
        for data in COURSES:
            if data["code"] in existing_courses:
                code_to_course[data["code"]] = existing_courses[data["code"]]
                continue
            course = Course(**data)
            db.add(course)
            db.flush()
            code_to_course[data["code"]] = course
            added_c += 1
        print(f"Courses    : {added_c} added · {len(existing_courses)} already existed")

        # --- ProfessorCourse links ---
        existing_links = {
            (pc.professor_id, pc.course_id, pc.semester)
            for pc in db.query(ProfessorCourse).all()
        }
        added_l = 0
        for prof_name, course_code, semester in LINKS:
            prof = name_to_prof.get(prof_name)
            course = code_to_course.get(course_code)
            if not prof or not course:
                print(f"  [WARN] Skipping link: {prof_name!r} / {course_code!r} — not found")
                continue
            key = (prof.id, course.id, semester)
            if key in existing_links:
                continue
            db.add(ProfessorCourse(professor_id=prof.id, course_id=course.id, semester=semester))
            existing_links.add(key)
            added_l += 1
        print(f"PC links   : {added_l} added")

        db.commit()
        print("\nforce_seed complete ✓")

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Seed failed, rolled back: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
