import enum
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    JSON,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Tương thích chéo: sử dụng native PostgreSQL JSONB/UUID/Vector trên Postgres, fallback sang JSON/Uuid trên SQLite (Unit tests)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")
VECTOR_TYPE = JSON().with_variant(Vector(1536), "postgresql")


class WorkModeEnum(str, enum.Enum):
    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"


class JobLevelEnum(str, enum.Enum):
    INTERN = "INTERN"
    FRESHER = "FRESHER"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD = "LEAD"
    MANAGER = "MANAGER"
    UNKNOWN = "UNKNOWN"


class JobStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    MERGED = "MERGED"


class RawJobStatusEnum(str, enum.Enum):
    FETCHED = "FETCHED"
    PARSED = "PARSED"
    ERROR = "ERROR"


class SkillCategoryEnum(str, enum.Enum):
    LANGUAGE = "LANGUAGE"
    FRAMEWORK = "FRAMEWORK"
    DATABASE = "DATABASE"
    CLOUD = "CLOUD"
    TOOL = "TOOL"
    CONCEPT = "CONCEPT"
    OTHER = "OTHER"


class RawJob(Base):
    """
    Model lưu trữ dữ liệu thô (Source of Truth) của tin tuyển dụng thu thập được từ các nguồn.
    Cho phép re-parse hoặc thay đổi schema / AI prompt mà không cần crawl lại.
    """
    __tablename__ = "raw_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # itviec, remotive, etc.
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    source_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # SHA-256 hash của raw payload/content để kiểm tra thay đổi nhanh (0 cost token)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True, default=dict)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    fetch_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RawJobStatusEnum.FETCHED.value, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Quan hệ 1-1 với Standardized Job
    job: Mapped[Optional["Job"]] = relationship(
        "Job", back_populates="raw_job", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_raw_jobs_source_source_job_id", "source", "source_job_id"),
    )


class Job(Base):
    """
    Model tin tuyển dụng đã chuẩn hóa (Standardized Job).
    Sử dụng cho tìm kiếm, phân tích, sinh vector embeddings và matching ở Phase 3.
    """
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    raw_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("raw_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    normalized_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    work_mode: Mapped[WorkModeEnum] = mapped_column(
        Enum(WorkModeEnum, native_enum=False, name="work_mode_enum"),
        nullable=False,
        default=WorkModeEnum.ONSITE,
        index=True
    )
    level: Mapped[JobLevelEnum] = mapped_column(
        Enum(JobLevelEnum, native_enum=False, name="job_level_enum"),
        nullable=False,
        default=JobLevelEnum.UNKNOWN,
        index=True
    )

    min_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_salary_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    benefits_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Chữ ký phục vụ Exact Deduplication: hash(normalized_company + ":" + normalized_title + ":" + location)
    dedup_signature: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Vector Embedding cho Semantic Deduplication & Phase 3 Matching
    embedding: Mapped[Optional[Any]] = mapped_column(VECTOR_TYPE, nullable=True)

    status: Mapped[JobStatusEnum] = mapped_column(
        Enum(JobStatusEnum, native_enum=False, name="job_status_enum"),
        nullable=False,
        default=JobStatusEnum.ACTIVE,
        index=True
    )

    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Quan hệ
    raw_job: Mapped["RawJob"] = relationship("RawJob", back_populates="job")
    skills: Mapped[List["JobSkill"]] = relationship(
        "JobSkill", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_jobs_company_title", "normalized_company", "normalized_title"),
    )


class Skill(Base):
    """
    Model danh mục kỹ năng chuẩn hóa (Canonical Skill Taxonomy).
    Dùng chung cho cả Ứng viên (Phase 1) và Tin tuyển dụng (Phase 2) phục vụ Matching (Phase 3).
    """
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    canonical_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[SkillCategoryEnum] = mapped_column(
        Enum(SkillCategoryEnum, native_enum=False, name="skill_category_enum"),
        nullable=False,
        default=SkillCategoryEnum.OTHER,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Quan hệ
    aliases: Mapped[List["SkillAlias"]] = relationship(
        "SkillAlias", back_populates="skill", cascade="all, delete-orphan"
    )
    job_skills: Mapped[List["JobSkill"]] = relationship(
        "JobSkill", back_populates="skill"
    )


class SkillAlias(Base):
    """
    Model ánh xạ các biến thể/từ đồng nghĩa về Skill chuẩn (Canonical).
    Ví dụ: 'python3', 'python 3.x' -> 'Python'
           'postgres', 'pgsql', 'postgresql' -> 'PostgreSQL'
    """
    __tablename__ = "skill_aliases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)  # Luôn lowercase

    # Quan hệ
    skill: Mapped["Skill"] = relationship("Skill", back_populates="aliases")


class JobSkill(Base):
    """
    Bảng liên kết Nhiều-Nhiều giữa Job và Skill kèm siêu dữ liệu (Metadata).
    Hỗ trợ giải thích lý do so khớp (Explainable Matching) ở Phase 3.
    """
    __tablename__ = "job_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="explicit", nullable=False)  # explicit, llm, inferred

    # Quan hệ
    job: Mapped["Job"] = relationship("Job", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="job_skills")

    @property
    def canonical_name(self) -> str:
        return self.skill.canonical_name if self.skill else ""

    @property
    def category(self) -> str:
        if self.skill:
            return self.skill.category.value if hasattr(self.skill.category, "value") else str(self.skill.category)
        return "OTHER"

    __table_args__ = (
        Index("ix_job_skills_job_skill", "job_id", "skill_id", unique=True),
    )
