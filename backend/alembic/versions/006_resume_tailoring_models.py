"""Resume tailoring, evidence maps, cover letters, and application logs

Revision ID: 006_resume_tailoring_models
Revises: 005_add_job_contact_fields
Create Date: 2026-08-22 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_resume_tailoring_models"
down_revision: Union[str, None] = "005_add_job_contact_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Bảng tailored_resumes
    op.create_table(
        "tailored_resumes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("candidate_id", sa.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("target_title", sa.String(length=255), nullable=False),
        sa.Column("summary_objective", sa.Text(), nullable=True),
        sa.Column("latex_source", sa.Text(), nullable=False),
        sa.Column("pdf_path", sa.String(length=1024), nullable=True),
        sa.Column("provenance_score", sa.Float(), server_default="100.0", nullable=False),
        sa.Column("is_provenance_verified", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("matched_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("highlighted_projects", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False),
        sa.Column("compilation_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tailored_resumes_candidate_id", "tailored_resumes", ["candidate_id"])
    op.create_index("ix_tailored_resumes_job_id", "tailored_resumes", ["job_id"])
    op.create_index("ix_tailored_resumes_candidate_job", "tailored_resumes", ["candidate_id", "job_id"])
    op.create_index("ix_tailored_resumes_status", "tailored_resumes", ["status"])

    # 2. Bảng evidence_maps
    op.create_table(
        "evidence_maps",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tailored_resume_id", sa.UUID(as_uuid=True), sa.ForeignKey("tailored_resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(length=50), nullable=False),
        sa.Column("bullet_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("source_entity_type", sa.String(length=50), nullable=False),
        sa.Column("source_entity_id", sa.String(length=255), nullable=True),
        sa.Column("original_fact", sa.Text(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("similarity_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_evidence_maps_tailored_resume_id", "evidence_maps", ["tailored_resume_id"])
    op.create_index("ix_evidence_maps_resume_section", "evidence_maps", ["tailored_resume_id", "section"])

    # 3. Bảng cover_letters
    op.create_table(
        "cover_letters",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tailored_resume_id", sa.UUID(as_uuid=True), sa.ForeignKey("tailored_resumes.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("candidate_id", sa.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("salutation", sa.String(length=255), server_default="Dear Hiring Team,", nullable=False),
        sa.Column("hook_statement", sa.Text(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("key_alignments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cover_letters_tailored_resume_id", "cover_letters", ["tailored_resume_id"])
    op.create_index("ix_cover_letters_candidate_id", "cover_letters", ["candidate_id"])
    op.create_index("ix_cover_letters_job_id", "cover_letters", ["job_id"])

    # 4. Bảng application_logs
    op.create_table(
        "application_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tailored_resume_id", sa.UUID(as_uuid=True), sa.ForeignKey("tailored_resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cover_letter_id", sa.UUID(as_uuid=True), sa.ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(length=50), server_default="EMAIL", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_application_logs_job_id", "application_logs", ["job_id"])
    op.create_index("ix_application_logs_tailored_resume_id", "application_logs", ["tailored_resume_id"])
    op.create_index("ix_application_logs_status", "application_logs", ["status"])
    op.create_index("ix_application_logs_job_status", "application_logs", ["job_id", "status"])


def downgrade() -> None:
    op.drop_table("application_logs")
    op.drop_table("cover_letters")
    op.drop_table("evidence_maps")
    op.drop_table("tailored_resumes")
