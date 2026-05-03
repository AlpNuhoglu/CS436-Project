"""local auth overhaul: drop email/cognito_sub, add password_hash, add pending_registrations

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-26

Bu migration:
  1. `users` tablosundan `email` ve `cognito_sub` sütunlarını düşürür.
  2. `users` tablosuna `password_hash` (NOT NULL) ekler.
  3. `pending_registrations` tablosunu yaratır — email + OTP doğrulaması
     bekleyen geçici kayıtlar burada tutulur, verify olunca silinir.

NOT: Mevcut user satırlarında `password_hash` olmadığı için, geçişte
varsayılan bir placeholder hash konur ve sonra çalıştırılan seed bunları
yeniden üretir. Üretim DB'sinde mevcut hesaplar invalid olur — local/demo
projemiz için kabul edilebilir.
"""
import sqlalchemy as sa
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pending_registrations ────────────────────────────────────────────────
    op.create_table(
        "pending_registrations",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── users tablosu güncellemeleri ─────────────────────────────────────────
    # password_hash önce nullable olarak eklenir, mevcut kayıtlara placeholder
    # değer atılır, sonra NOT NULL'a çevirilir.
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.execute(
        "UPDATE users SET password_hash = '!disabled-account-please-reseed' "
        "WHERE password_hash IS NULL"
    )
    op.alter_column("users", "password_hash", nullable=False)

    # email ve cognito_sub artık tutulmuyor.
    # NOT: `users.email` üzerinde unique constraint olabilir; düşürmek için
    # constraint adına bakmadan unique=False yapmıyoruz; doğrudan column drop
    # cascade etkisiyle constraint'i de düşürür.
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email")
        batch.drop_column("cognito_sub")


def downgrade() -> None:
    # Eski şemaya dönüş — kayıp veriler için placeholder kullanılır.
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("cognito_sub", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("email", sa.String(length=255), nullable=True))

    op.execute(
        "UPDATE users SET cognito_sub = id::text, email = username || '@unknown.local' "
        "WHERE cognito_sub IS NULL OR email IS NULL"
    )
    op.alter_column("users", "cognito_sub", nullable=False)
    op.alter_column("users", "email", nullable=False)
    op.create_unique_constraint("users_cognito_sub_key", "users", ["cognito_sub"])
    op.create_unique_constraint("users_email_key", "users", ["email"])

    op.drop_column("users", "password_hash")
    op.drop_table("pending_registrations")
