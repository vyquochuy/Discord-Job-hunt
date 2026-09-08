from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Khởi tạo Async Engine cho PostgreSQL
connect_args = {}
db_url = settings.DATABASE_URL
if "supabase.com" in db_url or "neon.tech" in db_url or "ssl=require" in db_url:
    connect_args["ssl"] = "require"

engine = create_async_engine(
    db_url,
    echo=(settings.LOG_LEVEL.lower() == "debug"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Lớp cơ sở cho tất cả các SQLAlchemy ORM Models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency: Cung cấp AsyncSession cho mỗi HTTP request.
    Async context manager tự động quản lý lifecycle và giải phóng session an toàn.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_health() -> bool:
    """Kiểm tra kết nối thực tế tới PostgreSQL."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False
