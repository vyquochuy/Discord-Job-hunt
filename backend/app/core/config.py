from typing import Optional
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    DISCORD_WEBHOOK_URL: Optional[str] = None
    ADMIN_EMAIL: str = "vyquochuy3005@gmail.com"
    ADMIN_INITIAL_PASSWORD: str = "vyquochuy300600"

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
