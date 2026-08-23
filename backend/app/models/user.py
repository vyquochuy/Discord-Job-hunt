import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, String, func, Uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

UUID_TYPE = Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.saved_job import SavedJob


class User(Base):
    """
    Model đại diện cho tài khoản người dùng đăng nhập hệ thống Web.
    Có quan hệ 1–1 với Candidate (Hồ sơ ứng viên).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Quan hệ 1–1 với Candidate Profile
    candidate: Mapped[Optional["Candidate"]] = relationship(
        "Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    
    # Quan hệ 1-N với SavedJobs
    saved_jobs: Mapped[list["SavedJob"]] = relationship(
        "SavedJob", back_populates="user", cascade="all, delete-orphan"
    )
