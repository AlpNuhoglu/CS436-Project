"""add first_name and last_name to users and pending registrations

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-30
"""
import sqlalchemy as sa
from alembic import op


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=64), nullable=True))

    # Pending registration kayıtları kısa ömürlüdür; yeni akışla uyumlu
    # olmayan bekleyen kayıtları temizleyip zorunlu isim alanlarını ekliyoruz.
    op.execute("DELETE FROM pending_registrations")
    op.add_column("pending_registrations", sa.Column("first_name", sa.String(length=64), nullable=False))
    op.add_column("pending_registrations", sa.Column("last_name", sa.String(length=64), nullable=False))


def downgrade() -> None:
    op.drop_column("pending_registrations", "last_name")
    op.drop_column("pending_registrations", "first_name")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
