"""add faculty to professors; faculty/difficulty/workload to courses

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-23

- professors.faculty          (VARCHAR(8), nullable)           FENS/FASS/SBS/SL
- courses.faculty             (VARCHAR(8), nullable)           FENS/FASS/SBS/SL
- courses.difficulty          (INTEGER,    nullable, 1..5)
- courses.workload_hours      (INTEGER,    nullable, 0..60)
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # professors.faculty
    op.add_column(
        "professors",
        sa.Column("faculty", sa.String(length=8), nullable=True),
    )

    # courses.*
    op.add_column(
        "courses",
        sa.Column("faculty", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "courses",
        sa.Column("difficulty", sa.Integer(), nullable=True),
    )
    op.add_column(
        "courses",
        sa.Column("workload_hours", sa.Integer(), nullable=True),
    )

    op.create_check_constraint(
        "ck_courses_difficulty",
        "courses",
        "difficulty IS NULL OR (difficulty >= 1 AND difficulty <= 5)",
    )
    op.create_check_constraint(
        "ck_courses_workload_hours",
        "courses",
        "workload_hours IS NULL OR (workload_hours >= 0 AND workload_hours <= 60)",
    )

    # Fakülte filtrelerini hızlandırmak için indeksler
    op.create_index("ix_professors_faculty", "professors", ["faculty"])
    op.create_index("ix_courses_faculty", "courses", ["faculty"])
    op.create_index("ix_courses_difficulty", "courses", ["difficulty"])


def downgrade() -> None:
    op.drop_index("ix_courses_difficulty", table_name="courses")
    op.drop_index("ix_courses_faculty", table_name="courses")
    op.drop_index("ix_professors_faculty", table_name="professors")

    op.drop_constraint("ck_courses_workload_hours", "courses", type_="check")
    op.drop_constraint("ck_courses_difficulty", "courses", type_="check")

    op.drop_column("courses", "workload_hours")
    op.drop_column("courses", "difficulty")
    op.drop_column("courses", "faculty")

    op.drop_column("professors", "faculty")
