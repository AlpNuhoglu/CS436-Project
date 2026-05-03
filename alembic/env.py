"""
Alembic environment configuration.

DATABASE_URL ortam değişkeninden bağlantı URL'si okunur; bu sayede
docker-compose ve yerel geliştirme ortamında ayrı .ini düzenlemesi gerekmez.
"""
import os
from getpass import getuser
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic Config nesnesi — alembic.ini değerlerine erişim sağlar
config = context.config

# Python loglama ayarlarını yükle
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL env değişkeninden oku, yoksa alembic.ini'deki değeri kullan
default_pg_user = os.getenv("PGUSER") or getuser()
database_url = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{default_pg_user}@localhost:5432/ders_forumu",
)
config.set_main_option("sqlalchemy.url", database_url)

# Tüm modelleri import et → autogenerate "autogenerate" çalışsın
import app.models  # noqa: F401  (yan etki: tüm modelleri Base.metadata'ya kaydeder)
from app.database import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """'Offline' modda migration çalıştır.

    Veritabanına gerçek bağlantı olmaksızın SQL çıktısı üretir.
    CI/CD pipeline'larında veya diff kontrolünde kullanışlıdır.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """'Online' modda migration çalıştır.

    Canlı bir veritabanı bağlantısı üzerinden DDL uygular.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
