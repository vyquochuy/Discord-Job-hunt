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
    String,
    Text,
    func,
    JSON,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.services.matching.models import Eligibility, RecommendationCategory

# Cross-DB compatibility: native PostgreSQL JSONB/UUID, fallback to JSON/Uuid on SQLite
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")


class JobMatch(Base):
    """
    Model lưu trữ kết quả phân tích mức độ phù hợp giữa Ứng viên và Tin tuyển dụng (Job Intelligence).
    Tách biệt rõ ràng giữa Eligibility (Tư cách) và Score (Điểm số 0 - 100).
    Lưu trữ Snapshots và Versioning phục vụ kiểm tra/truy vết.
    """
    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Điểm số thực tế (0.0 - 100.0)
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Tư cách ứng tuyển (ELIGIBLE / BLOCKED / UNCERTAIN)
    eligibility: Mapped[Eligibility] = mapped_column(
        Enum(Eligibility, native_enum=False, name="eligibility_enum"),
        nullable=False,
        default=Eligibility.ELIGIBLE,
        index=True,
    )
    eligibility_reasons: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )

    # Phân loại khuyến nghị (STRONG_MATCH, GOOD_MATCH, WEAK_MATCH, POOR_MATCH, DO_NOT_APPLY, REVIEW_REQUIRED)
    recommendation: Mapped[RecommendationCategory] = mapped_column(
        Enum(RecommendationCategory, native_enum=False, name="recommendation_enum"),
        nullable=False,
        default=RecommendationCategory.POOR_MATCH,
        index=True,
    )

    is_passed_hard_filters: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hard_filter_results: Mapped[Optional[List[dict[str, Any]]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )

    # Chi tiết kỹ năng so khớp
    matched_skills: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    missing_required_skills: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    missing_preferred_skills: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )

    # 7 Tín hiệu thành phần
    signals: Mapped[Optional[List[dict[str, Any]]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )
    warnings: Mapped[Optional[List[str]]] = mapped_column(
        JSON_TYPE, nullable=True, default=list
    )

    # Nhận xét / Giải thích
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_explanation_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True, default=dict
    )

    # Versioning
    scoring_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    # Data Snapshots (Pydantic models serialized to JSON)
    candidate_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True, default=dict
    )
    job_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON_TYPE, nullable=True, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate")  # type: ignore
    job: Mapped["Job"] = relationship("Job")  # type: ignore

    __table_args__ = (
        Index("ix_job_matches_candidate_job", "candidate_id", "job_id", unique=True),
        Index("ix_job_matches_score_created", "score", "created_at"),
    )
