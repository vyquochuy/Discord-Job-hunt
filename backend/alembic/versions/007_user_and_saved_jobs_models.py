"""User authentication and saved jobs models

Revision ID: 007_user_and_saved_jobs_models
Revises: 006_resume_tailoring_models
Create Date: 2026-08-23 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_user_and_saved_jobs_models"
down_revision: Union[str, None] = "006_resume_tailoring_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Bảng users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. Thêm user_id vào candidates (quan hệ 1-1 với users)
    op.add_column(
        "candidates",
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_candidates_user_id_users",
        "candidates",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_candidates_user_id", "candidates", ["user_id"], unique=True)

    # 3. Bảng saved_jobs
    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_saved_jobs_user_id", "saved_jobs", ["user_id"])
    op.create_index("ix_saved_jobs_job_id", "saved_jobs", ["job_id"])
    op.create_index("ix_saved_jobs_user_job", "saved_jobs", ["user_id", "job_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_saved_jobs_user_job", table_name="saved_jobs")
    op.drop_index("ix_saved_jobs_job_id", table_name="saved_jobs")
    op.drop_index("ix_saved_jobs_user_id", table_name="saved_jobs")
    op.drop_table("saved_jobs")

    op.drop_constraint("fk_candidates_user_id_users", "candidates", type_="foreignkey")
    op.drop_index("ix_candidates_user_id", table_name="candidates")
    op.drop_column("candidates", "user_id")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
