import uuid
from datetime import datetime
from typing import Any, List, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User

# Tương thích chéo: sử dụng native PostgreSQL JSONB/UUID trên Postgres, fallback sang JSON/Uuid trên SQLite (Unit tests)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")


class Candidate(Base):
    """
    Model đại diện cho hồ sơ gốc của Ứng viên (Source of Truth).
    Chứa thông tin liên hệ, học vấn, mục tiêu nghề nghiệp và các quan hệ tới kỹ năng, kinh nghiệm, dự án.
    """
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    github_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # JSON lưu trữ cấu trúc linh hoạt
    # education: List[{institution, degree, field, graduation_year, gpa, coursework}]
    education: Mapped[Optional[List[dict[str, Any]]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    # target_roles: List[str] ví dụ ["System Intern", "Backend Developer", "DevOps Engineer"]
    target_roles: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    # target_locations: List[str] ví dụ ["Ho Chi Minh City", "Remote"]
    target_locations: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    # preferences: {employment_types: [...], remote: bool|str, minimum_salary: int|null, currency: str}
    preferences: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True, default=dict
    )

    # Bản sao nội dung văn bản thô để tham chiếu provenance
    raw_master_resume_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_master_resume_tex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="candidate"
    )
    skills: Mapped[List["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateSkill.category, CandidateSkill.name",
    )
    experiences: Mapped[List["CandidateExperience"]] = relationship(
        "CandidateExperience",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateExperience.order",
    )
    projects: Mapped[List["CandidateProject"]] = relationship(
        "CandidateProject",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateProject.order",
    )
    certifications: Mapped[List["CandidateCertification"]] = relationship(
        "CandidateCertification",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateCertification.issue_year.desc()",
    )


class CandidateSkill(Base):
    """
    Model lưu trữ từng kỹ năng của ứng viên kèm theo danh mục.
    """
    __tablename__ = "candidate_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # programming, frameworks, tools_databases, security, soft_skills, languages, ai_ml
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    proficiency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="skills")


class CandidateExperience(Base):
    """
    Model lưu trữ kinh nghiệm làm việc và các thành tựu định lượng.
    """
    __tablename__ = "candidate_experiences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # achievements: List[str] các bullet points thành tựu đã được kiểm chứng
    achievements: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="experiences"
    )


class CandidateProject(Base):
    """
    Model lưu trữ dự án cá nhân/học thuật và các minh chứng kỹ thuật (evidence).
    """
    __tablename__ = "candidate_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    demo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # technologies: List[str] ví dụ ["React", "TypeScript", "Cloudflare Workers", "Durable Objects"]
    technologies: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    # evidence_points: List[{title, description, metrics}]
    evidence_points: Mapped[Optional[List[dict[str, Any]]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="projects"
    )


class CandidateCertification(Base):
    """
    Model lưu trữ chứng chỉ của ứng viên.
    """
    __tablename__ = "candidate_certifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    issue_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    credential_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="certifications"
    )
