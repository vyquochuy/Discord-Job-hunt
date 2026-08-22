"""Add contact_email and apply_url to jobs table

Revision ID: 005_add_job_contact_fields
Revises: 004_job_match_models
Create Date: 2026-08-22 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_add_job_contact_fields"
down_revision: Union[str, None] = "004_job_match_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("contact_email", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("apply_url", sa.String(length=1024), nullable=True))
    op.create_index("ix_jobs_contact_email", "jobs", ["contact_email"])


def downgrade() -> None:
    op.drop_index("ix_jobs_contact_email", table_name="jobs")
    op.drop_column("jobs", "apply_url")
    op.drop_column("jobs", "contact_email")
