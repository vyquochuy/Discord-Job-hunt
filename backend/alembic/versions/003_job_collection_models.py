"""Job collection and normalization data models

Revision ID: 003_job_collection_models
Revises: 002_candidate_profile_models
Create Date: 2026-08-20 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "003_job_collection_models"
down_revision: Union[str, None] = "002_candidate_profile_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Bảng raw_jobs
    op.create_table(
        "raw_jobs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("source_job_id", sa.String(length=255), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("fetch_status", sa.String(length=50), server_default="FETCHED", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_raw_jobs_source", "raw_jobs", ["source"])
    op.create_index("ix_raw_jobs_source_url", "raw_jobs", ["source_url"])
    op.create_index("ix_raw_jobs_source_job_id", "raw_jobs", ["source_job_id"])
    op.create_index("ix_raw_jobs_content_hash", "raw_jobs", ["content_hash"])
    op.create_index("ix_raw_jobs_fetch_status", "raw_jobs", ["fetch_status"])
    op.create_index("ix_raw_jobs_source_source_job_id", "raw_jobs", ["source", "source_job_id"])

    # 2. Bảng skills
    op.create_table(
        "skills",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("canonical_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), server_default="OTHER", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_skills_canonical_name", "skills", ["canonical_name"], unique=True)
    op.create_index("ix_skills_category", "skills", ["category"])

    # 3. Bảng skill_aliases
    op.create_table(
        "skill_aliases",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("skill_id", sa.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias", sa.String(length=100), nullable=False),
    )
    op.create_index("ix_skill_aliases_skill_id", "skill_aliases", ["skill_id"])
    op.create_index("ix_skill_aliases_alias", "skill_aliases", ["alias"], unique=True)

    # 4. Bảng jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("raw_job_id", sa.UUID(as_uuid=True), sa.ForeignKey("raw_jobs.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("normalized_title", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("normalized_location", sa.String(length=255), nullable=True),
        sa.Column("work_mode", sa.String(length=50), server_default="ONSITE", nullable=False),
        sa.Column("level", sa.String(length=50), server_default="UNKNOWN", nullable=False),
        sa.Column("min_salary", sa.Float(), nullable=True),
        sa.Column("max_salary", sa.Float(), nullable=True),
        sa.Column("salary_currency", sa.String(length=10), nullable=True),
        sa.Column("is_salary_negotiable", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements_summary", sa.Text(), nullable=True),
        sa.Column("benefits_summary", sa.Text(), nullable=True),
        sa.Column("dedup_signature", sa.String(length=64), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="ACTIVE", nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_jobs_raw_job_id", "jobs", ["raw_job_id"])
    op.create_index("ix_jobs_normalized_title", "jobs", ["normalized_title"])
    op.create_index("ix_jobs_normalized_company", "jobs", ["normalized_company"])
    op.create_index("ix_jobs_normalized_location", "jobs", ["normalized_location"])
    op.create_index("ix_jobs_work_mode", "jobs", ["work_mode"])
    op.create_index("ix_jobs_level", "jobs", ["level"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_dedup_signature", "jobs", ["dedup_signature"])
    op.create_index("ix_jobs_company_title", "jobs", ["normalized_company", "normalized_title"])

    # 5. Bảng job_skills
    op.create_table(
        "job_skills",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("source", sa.String(length=50), server_default="explicit", nullable=False),
    )
    op.create_index("ix_job_skills_job_id", "job_skills", ["job_id"])
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])
    op.create_index("ix_job_skills_job_skill", "job_skills", ["job_id", "skill_id"], unique=True)


def downgrade() -> None:
    op.drop_table("job_skills")
    op.drop_table("jobs")
    op.drop_table("skill_aliases")
    op.drop_table("skills")
    op.drop_table("raw_jobs")
