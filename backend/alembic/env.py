import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 - Register models with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Lấy DATABASE_URL từ env var (raw string, không qua make_url).
    Tự chuẩn hóa prefix sang postgresql+asyncpg://.
    """
    raw = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if not raw:
        raise ValueError("DATABASE_URL is not set.")
    url = raw.strip()
    # Normalize prefix
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+" not in url.split("://")[0]:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    # Remove sslmode from query string (asyncpg không hỗ trợ)
    if "sslmode=" in url:
        import re
        url = re.sub(r"[?&]sslmode=[^&]*", "", url).rstrip("?")
    return url


def get_sync_database_url() -> str:
    """Lấy Database URL cho chế độ offline (loại bỏ +asyncpg driver)."""
    url = get_database_url()
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
    db_url = get_database_url()

    # Với Supabase / Neon cloud: asyncpg cần ssl='require'
    connect_args = {}
    if "supabase.com" in db_url or "neon.tech" in db_url:
        connect_args["ssl"] = "require"

    # Dùng create_async_engine trực tiếp — tránh make_url parse URL Supabase sai
    engine = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_online() -> None:
    """Điểm chạy migrations online."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()