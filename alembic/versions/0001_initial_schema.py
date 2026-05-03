"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-21

Tüm başlangıç tablolarını oluşturur:
  users, professors, courses, professor_courses, reviews, upvotes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("cognito_sub", sa.String(128), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("cognito_sub", name="uq_users_cognito_sub"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    # ── professors ─────────────────────────────────────────────────────────
    op.create_table(
        "professors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("title", sa.String(64), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── courses ────────────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", name="uq_courses_code"),
    )

    # ── professor_courses ──────────────────────────────────────────────────
    op.create_table(
        "professor_courses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "professor_id",
            sa.Integer(),
            sa.ForeignKey("professors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("semester", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "professor_id", "course_id", "semester",
            name="uq_professor_course_semester",
        ),
    )

    # ── reviews ────────────────────────────────────────────────────────────
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "professor_id",
            sa.Integer(),
            sa.ForeignKey("professors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating"),
    )

    # ── upvotes ────────────────────────────────────────────────────────────
    op.create_table(
        "upvotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "review_id",
            sa.Integer(),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "review_id", name="uq_upvote_user_review"),
    )

    # ── İndeksler ──────────────────────────────────────────────────────────
    op.create_index("ix_reviews_professor_id", "reviews", ["professor_id"])
    op.create_index("ix_reviews_course_id", "reviews", ["course_id"])
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
    op.create_index("ix_upvotes_review_id", "upvotes", ["review_id"])


def downgrade() -> None:
    op.drop_index("ix_upvotes_review_id", table_name="upvotes")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_index("ix_reviews_course_id", table_name="reviews")
    op.drop_index("ix_reviews_professor_id", table_name="reviews")
    op.drop_table("upvotes")
    op.drop_table("reviews")
    op.drop_table("professor_courses")
    op.drop_table("courses")
    op.drop_table("professors")
    op.drop_table("users")
