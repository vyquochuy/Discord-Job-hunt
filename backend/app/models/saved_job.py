import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Index, Text, func, Uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

UUID_TYPE = Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.job import Job


class SavedJob(Base):
    """
    Model lưu trữ các tin tuyển dụng được người dùng đánh dấu Bookmark / Lưu lại trên Web.
    """
    __tablename__ = "saved_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Quan hệ
    user: Mapped["User"] = relationship("User", back_populates="saved_jobs")
    job: Mapped["Job"] = relationship("Job", back_populates="saved_jobs")

    __table_args__ = (
        Index("ix_saved_jobs_user_job", "user_id", "job_id", unique=True),
    )
