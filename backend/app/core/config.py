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

    # Bảo mật API nội bộ giữa Bot Discord và Backend
    INTERNAL_API_SECRET: str = "change_me_to_a_secure_random_string_32_chars"

    # Cơ sở dữ liệu (PostgreSQL + pgvector)
    POSTGRES_USER: str = "jobhunter"
    POSTGRES_PASSWORD: str = "jobhunter_secure_password"
    POSTGRES_DB: str = "jobhunter_db"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://jobhunter:jobhunter_secure_password@postgres:5432/jobhunter_db"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql://jobhunter:jobhunter_secure_password@postgres:5432/jobhunter_db"
    )

    # Redis Queue & Cache
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379/0"

    # AI / LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL_EXTRACTION: str = "gpt-4o-mini"
    AI_MODEL_STANDARD: str = "gpt-4o"
    AI_MODEL_GENERATION: str = "gpt-4o"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
