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
    String,
    Text,
    func,
    JSON,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")


class ResumeStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    COMPILED = "COMPILED"
    APPLIED = "APPLIED"
    FAILED = "FAILED"


class ApplicationStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    SENT = "SENT"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    INTERVIEW = "INTERVIEW"


class ApplicationChannelEnum(str, enum.Enum):
    EMAIL = "EMAIL"
    PORTAL = "PORTAL"
    MANUAL = "MANUAL"


class TailoredResume(Base):
    """
    Model lưu trữ bản CV LaTeX được tinh chỉnh (Tailored Resume) cho 1 vị trí cụ thể.
    Lưu trữ mã nguồn LaTeX, đường dẫn PDF đã build, điểm Provenance và danh sách kỹ năng nổi bật.
    """
    __tablename__ = "tailored_resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    target_title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # LaTeX Source Code & Artifact Paths
    latex_source: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Điểm xác minh tính xác thực (Zero-Hallucination Provenance Score: 0.0 - 100.0)
    provenance_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    is_provenance_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Danh sách kỹ năng và dự án được ưu tiên làm nổi bật
    matched_skills: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    highlighted_projects: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )

    status: Mapped[ResumeStatusEnum] = mapped_column(
        Enum(ResumeStatusEnum, native_enum=False, name="resume_status_enum"),
        nullable=False,
        default=ResumeStatusEnum.DRAFT,
        index=True,
    )
    compilation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate")  # type: ignore
    job: Mapped["Job"] = relationship("Job")  # type: ignore
    evidence_items: Mapped[List["EvidenceMap"]] = relationship(
        "EvidenceMap",
        back_populates="tailored_resume",
        cascade="all, delete-orphan",
        order_by="EvidenceMap.section, EvidenceMap.bullet_index",
    )
    cover_letter: Mapped[Optional["CoverLetter"]] = relationship(
        "CoverLetter",
        back_populates="tailored_resume",
        uselist=False,
        cascade="all, delete-orphan",
    )
    applications: Mapped[List["ApplicationLog"]] = relationship(
        "ApplicationLog",
        back_populates="tailored_resume",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tailored_resumes_candidate_job", "candidate_id", "job_id"),
    )


class EvidenceMap(Base):
    """
    Model lưu trữ bản đồ kiểm chứng sự thật (Provenance Evidence Mapping) cho từng claim/bullet point.
    Đảm bảo mọi claim trong CV được sinh ra đều có bằng chứng gốc từ candidate profile/master resume.
    """
    __tablename__ = "evidence_maps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    tailored_resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("tailored_resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section: Mapped[str] = mapped_column(String(50), nullable=False)  # PROJECTS, EXPERIENCE, SKILLS, SUMMARY
    bullet_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)

    source_entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # PROJECT, EXPERIENCE, SKILL, EDUCATION
    source_entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    original_fact: Mapped[str] = mapped_column(Text, nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    tailored_resume: Mapped["TailoredResume"] = relationship(
        "TailoredResume", back_populates="evidence_items"
    )

    __table_args__ = (
        Index("ix_evidence_maps_resume_section", "tailored_resume_id", "section"),
    )


class CoverLetter(Base):
    """
    Model lưu trữ Cover Letter được viết riêng cho từng tin tuyển dụng.
    Văn phong ngắn gọn, chân thực, khiêm tốn và tập trung vào điểm mạnh phù hợp thực tế.
    """
    __tablename__ = "cover_letters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    tailored_resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("tailored_resumes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    salutation: Mapped[str] = mapped_column(String(255), default="Dear Hiring Team,", nullable=False)

    hook_statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    key_alignments: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tailored_resume: Mapped["TailoredResume"] = relationship(
        "TailoredResume", back_populates="cover_letter"
    )
    candidate: Mapped["Candidate"] = relationship("Candidate")  # type: ignore
    job: Mapped["Job"] = relationship("Job")  # type: ignore


class ApplicationLog(Base):
    """
    Model theo dõi lịch sử và trạng thái nộp đơn ứng tuyển cho từng vị trí.
    Tránh nộp trùng lặp, ghi nhận kênh ứng tuyển (Email, Web Portal, Manual).
    """
    __tablename__ = "application_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tailored_resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE,
        ForeignKey("tailored_resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cover_letter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID_TYPE,
        ForeignKey("cover_letters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    channel: Mapped[ApplicationChannelEnum] = mapped_column(
        Enum(ApplicationChannelEnum, native_enum=False, name="application_channel_enum"),
        nullable=False,
        default=ApplicationChannelEnum.EMAIL,
        index=True,
    )
    status: Mapped[ApplicationStatusEnum] = mapped_column(
        Enum(ApplicationStatusEnum, native_enum=False, name="application_status_enum"),
        nullable=False,
        default=ApplicationStatusEnum.DRAFT,
        index=True,
    )

    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job")  # type: ignore
    tailored_resume: Mapped["TailoredResume"] = relationship(
        "TailoredResume", back_populates="applications"
    )
    cover_letter: Mapped[Optional["CoverLetter"]] = relationship("CoverLetter")

    __table_args__ = (
        Index("ix_application_logs_job_status", "job_id", "status"),
    )
