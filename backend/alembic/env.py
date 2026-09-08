import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 - Register models with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_async_database_url() -> str:
    """
    Lấy Database URL từ biến môi trường DATABASE_URL hoặc Settings.
    Chuẩn hóa sang postgresql+asyncpg:// và loại bỏ sslmode không hỗ trợ bởi asyncpg.
    """
    url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL is not set. Please configure it in your environment or .env file.")

    parsed = make_url(url.strip())

    # Normalize driver
    if parsed.drivername in {"postgres", "postgresql", "postgresql+psycopg2"}:
        parsed = parsed.set(drivername="postgresql+asyncpg")

    # asyncpg không dùng sslmode trong query string
    query = dict(parsed.query)
    query.pop("sslmode", None)
    parsed = parsed.set(query=query)

    return str(parsed)


def get_sync_database_url() -> str:
    """Lấy Database URL cho chế độ offline."""
    url = get_async_database_url()
    return url.replace("+asyncpg", "")


def run_migrations_offline() -> None:
    """Chạy migrations ở chế độ offline."""
    url = get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Chạy migrations ở chế độ online với Async Engine."""
    configuration = config.get_section(config.config_ini_section, {})
    db_url = get_async_database_url()
    configuration["sqlalchemy.url"] = db_url

    # Với Supabase hoặc các host cloud PostgreSQL, asyncpg yêu cầu ssl='require'
    connect_args = {}
    if "supabase.com" in db_url or "pooler.supabase.com" in db_url or "neon.tech" in db_url:
        connect_args["ssl"] = "require"

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Điểm chạy migrations online."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()