"""Job intelligence and match data models

Revision ID: 004_job_match_models
Revises: 003_job_collection_models
Create Date: 2026-08-22 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_job_match_models"
down_revision: Union[str, None] = "003_job_collection_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_matches",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("candidate_id", sa.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("eligibility", sa.String(length=50), server_default="ELIGIBLE", nullable=False),
        sa.Column("eligibility_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendation", sa.String(length=50), server_default="POOR_MATCH", nullable=False),
        sa.Column("is_passed_hard_filters", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("hard_filter_results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("matched_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("missing_required_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("missing_preferred_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("raw_explanation_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("scoring_version", sa.String(length=20), server_default="v1", nullable=False),
        sa.Column("taxonomy_version", sa.String(length=20), server_default="v1", nullable=False),
        sa.Column("candidate_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("job_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_job_matches_candidate_id", "job_matches", ["candidate_id"])
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_score", "job_matches", ["score"])
    op.create_index("ix_job_matches_eligibility", "job_matches", ["eligibility"])
    op.create_index("ix_job_matches_recommendation", "job_matches", ["recommendation"])
    op.create_index("ix_job_matches_candidate_job", "job_matches", ["candidate_id", "job_id"], unique=True)
    op.create_index("ix_job_matches_score_created", "job_matches", ["score", "created_at"])


def downgrade() -> None:
    op.drop_table("job_matches")
