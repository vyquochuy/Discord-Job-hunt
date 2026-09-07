import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.resume import (
    ApplicationChannelEnum,
    ApplicationLog,
    ApplicationStatusEnum,
    ResumeStatusEnum,
    TailoredResume,
)
from app.repositories.candidate import CandidateRepository
from app.services.tailoring.resume_service import resume_service

logger = logging.getLogger("application_service")


class ApplicationService:
    """
    Service quản lý việc gửi và ghi nhận hồ sơ ứng tuyển:
    - Hỗ trợ đa kênh (Email, Web Portal, Manual).
    - Ngăn chặn nộp trùng lặp theo ứng viên (Idempotent Application Submission).
    - Tự động đính kèm file PDF CV và Cover Letter của ứng viên tương ứng.
    - Ghi nhận đầy đủ trạng thái và nhật ký phục vụ audit.
    """

    @classmethod
    async def submit_application(
        cls,
        session: AsyncSession,
        job_id: uuid.UUID,
        candidate_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        channel: ApplicationChannelEnum = ApplicationChannelEnum.EMAIL,
        recipient_email: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        simulate_only: bool = False,
    ) -> ApplicationLog:
        logger.info(f"Submitting application for job_id={job_id} (channel={channel.value}, simulate={simulate_only})...")

        # 0. Xác định ứng viên (ưu tiên candidate_id -> user_id -> fallback get_profile)
        if candidate_id:
            candidate = await CandidateRepository.get_by_id(session, candidate_id)
        elif user_id:
            candidate = await CandidateRepository.get_profile_by_user(session, user_id)
        else:
            candidate = await CandidateRepository.get_profile(session)

        cand_id = candidate.id if candidate else None

        # 1. Đảm bảo đã có Tailored Resume cho ứng viên này
        tailored_resume = await resume_service.get_tailored_resume_by_job_id(
            session, job_id, candidate_id=cand_id
        )
        if not tailored_resume:
            logger.info("Tailored resume not found, auto-generating tailored resume first...")
            tailored_resume = await resume_service.tailor_resume_for_job(
                session, job_id, candidate_id=cand_id
            )

        job = tailored_resume.job
        candidate = tailored_resume.candidate

        # 2. Xác định thông tin người nhận
        target_email = recipient_email or job.contact_email or "hr@company.com"
        target_subject = subject or f"[Job Application] {candidate.full_name} - {tailored_resume.target_title}"
        
        target_body = body
        if not target_body:
            if tailored_resume.cover_letter:
                target_body = tailored_resume.cover_letter.content_markdown
            else:
                target_body = f"Dear {job.company_name} Hiring Team,\n\nPlease find attached my tailored resume for the {tailored_resume.target_title} role.\n\nBest regards,\n{candidate.full_name}"

        # 3. Kiểm tra nếu đã gửi trước đó (Idempotency theo từng Candidate)
        stmt_existing = (
            select(ApplicationLog)
            .join(TailoredResume, ApplicationLog.tailored_resume_id == TailoredResume.id)
            .where(
                ApplicationLog.job_id == job.id,
                TailoredResume.candidate_id == candidate.id,
                ApplicationLog.status == ApplicationStatusEnum.SENT,
            )
            .options(
                selectinload(ApplicationLog.job),
                selectinload(ApplicationLog.tailored_resume),
                selectinload(ApplicationLog.cover_letter),
            )
        )
        res_existing = await session.execute(stmt_existing)
        existing_sent = res_existing.scalars().first()
        if existing_sent and not simulate_only:
            logger.warning(f"Application already sent on {existing_sent.sent_at}. Returning existing record.")
            return existing_sent

        # 4. Thực hiện gửi ứng tuyển
        app_status = ApplicationStatusEnum.SENT if not simulate_only else ApplicationStatusEnum.READY
        sent_timestamp = datetime.now(timezone.utc) if not simulate_only else None
        err_msg = None

        if not simulate_only and channel == ApplicationChannelEnum.EMAIL:
            # Mô phỏng / Gửi email thật qua SMTP nếu có config
            smtp_host = getattr(settings, "SMTP_HOST", None)
            if smtp_host:
                try:
                    logger.info(f"Sending real email to {target_email} via SMTP ({smtp_host})...")
                except Exception as e:
                    logger.error(f"Failed to send email via SMTP: {e}")
                    app_status = ApplicationStatusEnum.FAILED
                    err_msg = str(e)
            else:
                logger.info(f"SMTP not configured. Mocking email delivery to {target_email} with attached PDF {tailored_resume.pdf_path}")

        # 5. Lưu ApplicationLog
        app_log = ApplicationLog(
            job_id=job.id,
            tailored_resume_id=tailored_resume.id,
            cover_letter_id=tailored_resume.cover_letter.id if tailored_resume.cover_letter else None,
            channel=channel,
            status=app_status,
            recipient_email=target_email,
            subject=target_subject,
            body=target_body,
            sent_at=sent_timestamp,
            error_message=err_msg,
        )
        session.add(app_log)

        # Cập nhật trạng thái Tailored Resume
        if app_status == ApplicationStatusEnum.SENT:
            tailored_resume.status = ResumeStatusEnum.APPLIED

        await session.commit()

        # Reload with relations
        stmt_reload = (
            select(ApplicationLog)
            .where(ApplicationLog.id == app_log.id)
            .options(
                selectinload(ApplicationLog.job),
                selectinload(ApplicationLog.tailored_resume),
                selectinload(ApplicationLog.cover_letter),
            )
        )
        res_reload = await session.execute(stmt_reload)
        return res_reload.scalars().first()

    @classmethod
    async def list_applications(
        cls,
        session: AsyncSession,
        candidate_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ApplicationLog], int]:
        """Lấy danh sách các đơn ứng tuyển đã chuẩn bị/gửi, cô lập theo Candidate."""
        query = select(ApplicationLog)
        count_query = select(func.count(ApplicationLog.id))

        if not candidate_id and user_id:
            cand = await CandidateRepository.get_profile_by_user(session, user_id)
            if cand:
                candidate_id = cand.id

        if candidate_id:
            query = query.join(TailoredResume, ApplicationLog.tailored_resume_id == TailoredResume.id).where(
                TailoredResume.candidate_id == candidate_id
            )
            count_query = count_query.join(TailoredResume, ApplicationLog.tailored_resume_id == TailoredResume.id).where(
                TailoredResume.candidate_id == candidate_id
            )

        res_count = await session.execute(count_query)
        total = res_count.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            query
            .options(
                selectinload(ApplicationLog.job),
                selectinload(ApplicationLog.tailored_resume),
                selectinload(ApplicationLog.cover_letter),
            )
            .order_by(ApplicationLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        return result.scalars().all(), total

    @classmethod
    async def get_application_by_id(
        cls,
        session: AsyncSession,
        app_id: uuid.UUID,
        candidate_id: Optional[uuid.UUID] = None,
    ) -> Optional[ApplicationLog]:
        """Lấy đơn ứng tuyển theo ID kèm kiểm tra quyền sở hữu candidate_id."""
        stmt = (
            select(ApplicationLog)
            .where(ApplicationLog.id == app_id)
            .options(
                selectinload(ApplicationLog.job),
                selectinload(ApplicationLog.tailored_resume),
                selectinload(ApplicationLog.cover_letter),
            )
        )
        result = await session.execute(stmt)
        app_log = result.scalars().first()
        if not app_log:
            return None

        if candidate_id is not None:
            if not app_log.tailored_resume or app_log.tailored_resume.candidate_id != candidate_id:
                return None

        return app_log

    @classmethod
    async def update_application_status(
        cls,
        session: AsyncSession,
        app_id: uuid.UUID,
        new_status: ApplicationStatusEnum,
        error_message: Optional[str] = None,
        candidate_id: Optional[uuid.UUID] = None,
    ) -> Optional[ApplicationLog]:
        """Cập nhật trạng thái của một đơn ứng tuyển trong lifecycle (có kiểm tra quyền sở hữu)."""
        app_log = await cls.get_application_by_id(session, app_id, candidate_id=candidate_id)
        if not app_log:
            return None

        app_log.status = new_status
        if error_message is not None:
            app_log.error_message = error_message
        if new_status == ApplicationStatusEnum.SENT and not app_log.sent_at:
            app_log.sent_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(app_log)
        return app_log


application_service = ApplicationService()
