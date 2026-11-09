"""Rename TopDev source to Saramin without merging or deleting history.

Duplicate IDs fail closed: resolve collisions explicitly before rerunning.
URLs/payloads stay unchanged as historical evidence; downgrade is intentionally
unsupported because new Saramin rows cannot be distinguished from renamed rows.
"""
from alembic import op

revision = "009_rename_topdev_saramin"
down_revision = "008_refresh_tokens_and_rotation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Block concurrent ingestion until collision check and rename both complete.
    op.execute("LOCK TABLE raw_jobs IN SHARE ROW EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT source_job_id FROM raw_jobs
                WHERE source IN ('topdev', 'saramin') AND source_job_id IS NOT NULL
                GROUP BY source_job_id HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'TopDev/Saramin source_job_id collision; resolve explicitly before migration 009';
            END IF;
        END $$;
    """)
    op.execute("UPDATE raw_jobs SET source = 'saramin' WHERE source = 'topdev'")


def downgrade() -> None:
    raise RuntimeError("009 cannot safely distinguish renamed history from new Saramin rows")
