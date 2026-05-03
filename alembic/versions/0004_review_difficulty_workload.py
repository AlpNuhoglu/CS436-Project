"""add difficulty and workload_hours to reviews

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-24

Öğrencilerin yorum yazarken zorluk (1-5) ve haftalık iş yükü (0-60) belirtmeleri için
reviews tablosuna iki yeni nullable kolon eklenir. Mevcut yorumlarda NULL kalır.
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column("difficulty", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reviews",
        sa.Column("workload_hours", sa.Integer(), nullable=True),
    )

    op.create_check_constraint(
        "ck_reviews_difficulty",
        "reviews",
        "difficulty IS NULL OR (difficulty >= 1 AND difficulty <= 5)",
    )
    op.create_check_constraint(
        "ck_reviews_workload_hours",
        "reviews",
        "workload_hours IS NULL OR (workload_hours >= 0 AND workload_hours <= 60)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_reviews_workload_hours", "reviews", type_="check")
    op.drop_constraint("ck_reviews_difficulty", "reviews", type_="check")
    op.drop_column("reviews", "workload_hours")
    op.drop_column("reviews", "difficulty")
