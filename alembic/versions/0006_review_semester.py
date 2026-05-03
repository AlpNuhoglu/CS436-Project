"""add semester field to reviews

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-26

reviews tablosuna `semester` (VARCHAR(32), nullable) kolonu eklenir ve
unique constraint güncellenir:
  ESKİ: (user_id, professor_id, course_id)              uq_review_user_professor_course
  YENİ: (user_id, professor_id, course_id, semester)    uq_review_user_prof_course_semester

Bu sayede aynı kullanıcı aynı hocayla aynı dersi farklı dönemlerde almışsa
her dönem için ayrı bir yorum yazabilir. semester opsiyoneldir; NULL
yorumlar eski davranışla uyumlu kalır (PostgreSQL'de NULL'lar UNIQUE'te
ayrı sayılır).
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column("semester", sa.String(32), nullable=True),
    )

    # Eski unique constraint'i kaldır
    op.drop_constraint(
        "uq_review_user_professor_course",
        "reviews",
        type_="unique",
    )

    # semester'ı içeren yeni unique constraint
    op.create_unique_constraint(
        "uq_review_user_prof_course_semester",
        "reviews",
        ["user_id", "professor_id", "course_id", "semester"],
    )

    # Filtre + sıralama için indeks (örn. "Spring 2025 yorumları")
    op.create_index(
        "ix_reviews_semester",
        "reviews",
        ["semester"],
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_semester", table_name="reviews")
    op.drop_constraint(
        "uq_review_user_prof_course_semester",
        "reviews",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_review_user_professor_course",
        "reviews",
        ["user_id", "professor_id", "course_id"],
    )
    op.drop_column("reviews", "semester")
