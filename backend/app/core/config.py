import os
import logging
from typing import Optional
from pydantic import field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Quản lý toàn bộ biến môi trường của hệ thống Backend.
    Tự động đọc từ file .env nếu có.
    """
    # Thông tin dự án
    PROJECT_NAME: str = "AI Job Hunter Agent API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    # Server Configuration
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_API_URL: str = "http://localhost:8000"
    ALLOWED_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173"

    # Bảo mật API nội bộ & Web Auth
    INTERNAL_API_SECRET: str = "change_me_to_a_secure_random_string_32_chars"
    JWT_SECRET_KEY: str = "job_hunter_platform_secret_key_web_2026_flexible_auth"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 phút theo chuẩn bảo mật
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # 30 ngày cho refresh token
    ROTATION_GRACE_PERIOD_SECONDS: int = 15  # Cửa sổ ân hạn concurrency chống duplicate refresh
    DISCORD_WEBHOOK_URL: Optional[str] = None
    ADMIN_NAME: str = "Quoc Huy"
    ADMIN_EMAIL: str = "vyquochuy3005@gmail.com"
    ADMIN_INITIAL_PASSWORD: Optional[str] = None
    MAX_RESUME_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB

    @field_validator("JWT_SECRET_KEY", "INTERNAL_API_SECRET", mode="after")
    @classmethod
    def validate_secrets(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError(f"{field_name} must not be empty or whitespace.")

        cleaned = v.strip()
        insecure_defaults = {
            "change_me_to_a_secure_random_string_32_chars",
            "job_hunter_platform_secret_key_web_2026_flexible_auth",
        }

        env = (os.getenv("ENVIRONMENT") or "development").lower().strip()
        is_insecure = (cleaned in insecure_defaults) or (len(cleaned) < 32)

        if env == "production":
            if is_insecure:
                raise ValueError(
                    f"Production security violation: {field_name} must be a secure secret of at least 32 characters and cannot use default/insecure values."
                )
        else:
            if is_insecure:
                logging.getLogger("uvicorn.error").warning(
                    f"SECURITY WARNING: {field_name} appears to use an insecure/default value. Please configure a strong secret."
                )

        return cleaned

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Tự động chuẩn hóa postgres:// hoặc postgresql:// sang postgresql+asyncpg:// và loại bỏ sslmode cho asyncpg."""
        if not v or not isinstance(v, str):
            return v
        cleaned = v.strip()
        if cleaned.startswith("postgres://"):
            cleaned = cleaned.replace("postgres://", "postgresql+asyncpg://", 1)
        elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+"):
            cleaned = cleaned.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "sslmode=" in cleaned:
            import re
            cleaned = re.sub(r"[?&]sslmode=[^&]*", "", cleaned).rstrip("?")
        return cleaned


    # Cơ sở dữ liệu (PostgreSQL + pgvector)
    POSTGRES_USER: str = "jobhunter"
    POSTGRES_PASSWORD: str = "jobhunter_secure_password"
    POSTGRES_DB: str = "jobhunter_db"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://jobhunter:jobhunter_secure_password@127.0.0.1:5432/jobhunter_db"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql://jobhunter:jobhunter_secure_password@127.0.0.1:5432/jobhunter_db"
    )

    # Redis Queue & Cache
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # AI / LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL_EXTRACTION: str = "gpt-4o-mini"
    AI_MODEL_STANDARD: str = "gpt-4o"
    AI_MODEL_GENERATION: str = "gpt-4o"

    # Gemini Integration
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_API_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
