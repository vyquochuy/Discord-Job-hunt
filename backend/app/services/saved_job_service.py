import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.saved_job import SavedJob
from app.schemas.job import JobResponse
from app.schemas.saved_job import SavedJobCreate


class SavedJobService:
    """
    Service xử lý các nghiệp vụ lưu trữ, đánh dấu bookmark và quản lý Saved Jobs của người dùng.
    """

    @staticmethod
    async def list_saved_jobs(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Lấy danh sách các tin tuyển dụng đã lưu kèm chi tiết thông tin Job."""
        query = (
            select(SavedJob)
            .options(selectinload(SavedJob.job).selectinload(Job.raw_job))
            .where(SavedJob.user_id == user_id)
            .order_by(SavedJob.created_at.desc())
        )
        result = await session.execute(query)
        saved_list = result.scalars().all()

        items: List[Dict[str, Any]] = []
        for s in saved_list:
            job_data = JobResponse.model_validate(s.job).model_dump() if s.job else None
            items.append({
                "id": s.id,
                "user_id": s.user_id,
                "job_id": s.job_id,
                "notes": s.notes,
                "created_at": s.created_at,
                "job": job_data,
            })
        return items

    @staticmethod
    async def save_job(
        session: AsyncSession,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        payload: Optional[SavedJobCreate] = None,
    ) -> Dict[str, Any]:
        """Lưu hoặc cập nhật ghi chú của tin tuyển dụng đã đánh dấu."""
        # 1. Kiểm tra job có tồn tại không
        job_stmt = select(Job).where(Job.id == job_id)
        job_res = await session.execute(job_stmt)
        job = job_res.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID {job_id} not found",
            )

        # 2. Kiểm tra xem đã lưu chưa
        saved_stmt = select(SavedJob).where(
            SavedJob.user_id == user_id,
            SavedJob.job_id == job_id,
        )
        saved_res = await session.execute(saved_stmt)
        existing_saved = saved_res.scalar_one_or_none()

        if existing_saved:
            if payload and payload.notes is not None:
                existing_saved.notes = payload.notes
                await session.commit()
            return {"status": "already_saved", "saved_job_id": existing_saved.id}

        # 3. Tạo mới bản ghi SavedJob
        notes = payload.notes if payload else None
        saved_item = SavedJob(
            id=uuid.uuid4(),
            user_id=user_id,
            job_id=job_id,
            notes=notes,
        )
        session.add(saved_item)
        await session.commit()

        return {"status": "saved", "saved_job_id": saved_item.id}

    @staticmethod
    async def unsave_job(
        session: AsyncSession,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> Dict[str, str]:
        """Hủy lưu (bỏ đánh dấu) một tin tuyển dụng."""
        saved_stmt = select(SavedJob).where(
            SavedJob.user_id == user_id,
            SavedJob.job_id == job_id,
        )
        saved_res = await session.execute(saved_stmt)
        saved_item = saved_res.scalar_one_or_none()

        if not saved_item:
            return {"status": "not_found"}

        await session.delete(saved_item)
        await session.commit()

        return {"status": "unsaved"}


saved_job_service = SavedJobService()
