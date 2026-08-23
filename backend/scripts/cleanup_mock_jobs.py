import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.job import RawJob, Job

async def delete_mock_jobs():
    async with AsyncSessionLocal() as session:
        # Find raw jobs with source = 'mock'
        stmt = select(RawJob).where(RawJob.source == "mock")
        result = await session.execute(stmt)
        raw_mock_jobs = result.scalars().all()
        count = len(raw_mock_jobs)
        
        print(f"Found {count} raw mock jobs to delete.")
        
        if count > 0:
            # Delete them (cascading will delete associated Jobs, Matches, Skills, Resumes, Applications)
            del_stmt = delete(RawJob).where(RawJob.source == "mock")
            await session.execute(del_stmt)
            await session.commit()
            print(f"Successfully deleted {count} mock jobs from database.")
        else:
            print("No mock jobs found in database.")

if __name__ == "__main__":
    asyncio.run(delete_mock_jobs())
