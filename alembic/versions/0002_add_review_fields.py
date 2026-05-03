"""add review fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-23

reviews tablosuna eklenenler:
  - is_anonymous  (bool, default false)
  - uq_review_user_professor_course unique constraint
    (aynı user aynı hoca+ders çifti için tek yorum)
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "is_anonymous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_unique_constraint(
        "uq_review_user_professor_course",
        "reviews",
        ["user_id", "professor_id", "course_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_review_user_professor_course", "reviews", type_="unique")
    op.drop_column("reviews", "is_anonymous")
