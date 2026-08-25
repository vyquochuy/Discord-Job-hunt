import os
import logging
import uuid
from pathlib import Path
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.resume import (
    CoverLetter,
    EvidenceMap,
    ResumeStatusEnum,
    TailoredResume,
)
from app.repositories.candidate import CandidateRepository
from app.services.matching.match_service import job_match_service
from app.services.tailoring.cover_letter_generator import cover_letter_generator
from app.services.tailoring.latex_compiler import latex_compiler
from app.services.tailoring.latex_generator import latex_generator
from app.services.tailoring.provenance_verifier import provenance_verifier

logger = logging.getLogger("resume_service")


class ResumeTailorService:
    """
    Orchestration service điều phối toàn bộ quy trình tinh chỉnh hồ sơ ứng tuyển:
    1. Chuẩn bị Context ứng viên và Tin tuyển dụng
    2. Sinh mã nguồn LaTeX (.tex) bám sát JD
    3. Kiểm chứng sự thật Provenance Verification (Zero Hallucination)
    4. Biên dịch mã nguồn thành tệp tin PDF (.pdf)
    5. Tạo Cover Letter Markdown (.md) chân thực và khiêm tốn
    6. Lưu trữ vào Database và hệ thống tệp tin
    """

    @classmethod
    async def tailor_resume_for_job(
        cls,
        session: AsyncSession,
        job_id: uuid.UUID,
        candidate_id: Optional[uuid.UUID] = None,
        force_regenerate: bool = False,
        custom_tone: str = "professional_and_humble",
    ) -> TailoredResume:
        logger.info(f"Starting resume tailoring for job_id={job_id} (force_regenerate={force_regenerate})...")

        # 1. Lấy thông tin ứng viên
        if candidate_id:
            candidate = await CandidateRepository.get_by_id(session, candidate_id)
        else:
            candidate = await CandidateRepository.get_profile(session)

        if not candidate:
            raise ValueError("Candidate profile not found. Please sync profile first.")

        # 2. Lấy thông tin công việc
        stmt_job = (
            select(Job)
            .where(Job.id == job_id)
            .options(selectinload(Job.skills), selectinload(Job.raw_job))
        )
        res_job = await session.execute(stmt_job)
        job = res_job.scalars().first()

        if not job:
            raise ValueError(f"Job with ID {job_id} not found.")

        # 3. Kiểm tra nếu đã có Tailored Resume trước đó
        if not force_regenerate:
            stmt_existing = (
                select(TailoredResume)
                .where(
                    TailoredResume.candidate_id == candidate.id,
                    TailoredResume.job_id == job.id,
                )
                .options(
                    selectinload(TailoredResume.evidence_items),
                    selectinload(TailoredResume.cover_letter),
                    selectinload(TailoredResume.job),
                    selectinload(TailoredResume.candidate),
                )
            )
            res_existing = await session.execute(stmt_existing)
            existing = res_existing.scalars().first()
            if existing and existing.status in (ResumeStatusEnum.COMPILED, ResumeStatusEnum.DRAFT):
                # Tự phục hồi (Self-healing): Kiểm tra file PDF trên đĩa phải thực sự tồn tại và > 1KB
                pdf_file = Path(existing.pdf_path) if existing.pdf_path else None
                if pdf_file and pdf_file.exists() and pdf_file.stat().st_size > 1000:
                    logger.info(f"Returning valid cached tailored resume (ID={existing.id})")
                    return existing
                else:
                    logger.warning(
                        f"Cached resume ID={existing.id} has missing or empty PDF artifact on disk. "
                        f"Auto-regenerating fresh PDF with LaTeX compiler..."
                    )

        # 4. Phân tích so khớp từ Phase 3 Job Intelligence
        match_record = await job_match_service.calculate_match_for_job(
            session=session, job_id=job.id, candidate_id=candidate.id
        )

        # 5. Xây dựng Chiến lược Tinh chỉnh Hồ sơ (Resume Intelligence Strategy)
        from app.services.tailoring.resume_intelligence import resume_intelligence
        logger.info("Building strategic positioning with Resume Intelligence Engine...")
        strategy = resume_intelligence.build_strategy(
            candidate=candidate,
            job=job,
            match_record=match_record,
            custom_tone=custom_tone,
        )

        matched_skills = strategy.matched_skills
        target_title = strategy.target_title

        # 6. Sinh mã nguồn LaTeX từ ResumeStrategy
        logger.info("Rendering tailored LaTeX source from strategy...")
        latex_source = latex_generator.generate_tailored_tex(
            candidate=candidate,
            strategy=strategy,
        )

        # 7. Kiểm chứng Provenance trên các nội dung thực sự được đưa vào CV
        logger.info("Running Provenance Verification on claims...")
        sections_dict = {
            "SUMMARY": [strategy.adaptive_summary],
            "PROJECTS": [],
        }
        for p in strategy.ranked_projects:
            for ev in p.ranked_evidence:
                sections_dict["PROJECTS"].append(ev.evidence_detail)

        evidence_items, provenance_score, is_verified = provenance_verifier.verify_resume(
            candidate=candidate,
            tailored_sections=sections_dict,
        )
        logger.info(f"Provenance Score: {provenance_score}% (Verified={is_verified})")

        # 8. Biên dịch LaTeX thành PDF
        logger.info("Compiling LaTeX to PDF...")
        compile_ok, pdf_path, comp_err = await latex_compiler.compile_tex(
            tex_content=latex_source,
            job_id=str(job.id),
            file_prefix=f"resume_{job.id}",
        )

        resume_status = ResumeStatusEnum.COMPILED if compile_ok else ResumeStatusEnum.FAILED

        # 9. Sinh Cover Letter động từ ResumeStrategy
        logger.info("Generating Tailored Cover Letter from strategy...")
        cover_letter_data = cover_letter_generator.generate_cover_letter(
            candidate=candidate,
            job=job,
            strategy=strategy,
            custom_tone=custom_tone,
        )

        # Lưu cover letter ra file .md cạnh resume
        storage_dir = latex_compiler.get_storage_root() / str(job.id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        cl_md_path = storage_dir / "cover_letter.md"
        cl_md_path.write_text(cover_letter_data["content_markdown"], encoding="utf-8")

        # 10. Lưu vào Cơ sở dữ liệu
        # Xóa bản ghi cũ nếu có
        stmt_del = (
            select(TailoredResume)
            .where(
                TailoredResume.candidate_id == candidate.id,
                TailoredResume.job_id == job.id,
            )
        )
        res_del = await session.execute(stmt_del)
        old_resumes = res_del.scalars().all()
        for old in old_resumes:
            await session.delete(old)
        await session.flush()

        tailored_resume = TailoredResume(
            candidate_id=candidate.id,
            job_id=job.id,
            version=1,
            target_title=target_title,
            summary_objective=strategy.adaptive_summary,
            latex_source=latex_source,
            pdf_path=pdf_path,
            provenance_score=provenance_score,
            is_provenance_verified=is_verified,
            matched_skills=matched_skills,
            highlighted_projects=[p.project.name for p in strategy.ranked_projects],
            status=resume_status,
            compilation_error=comp_err,
        )
        session.add(tailored_resume)
        await session.flush()

        # Lưu Evidence Maps
        for ev in evidence_items:
            ev_db = EvidenceMap(
                tailored_resume_id=tailored_resume.id,
                section=ev.section,
                bullet_index=ev.bullet_index,
                claim_text=ev.claim_text,
                source_entity_type=ev.source_entity_type,
                source_entity_id=ev.source_entity_id,
                original_fact=ev.original_fact,
                is_verified=ev.is_verified,
                similarity_score=ev.similarity_score,
                notes=ev.notes,
            )
            session.add(ev_db)

        # Lưu Cover Letter
        cover_letter = CoverLetter(
            tailored_resume_id=tailored_resume.id,
            candidate_id=candidate.id,
            job_id=job.id,
            recipient_name=cover_letter_data.get("recipient_name"),
            company_name=cover_letter_data["company_name"],
            salutation=cover_letter_data["salutation"],
            hook_statement=cover_letter_data.get("hook_statement"),
            content_markdown=cover_letter_data["content_markdown"],
            key_alignments=cover_letter_data.get("key_alignments", []),
        )
        session.add(cover_letter)
        await session.commit()

        # Reload with relationships
        return await cls.get_tailored_resume_by_id(session, tailored_resume.id)

    @classmethod
    async def get_tailored_resume_by_id(
        cls, session: AsyncSession, resume_id: uuid.UUID
    ) -> Optional[TailoredResume]:
        """Truy vấn bản Tailored Resume đầy đủ quan hệ theo ID."""
        stmt = (
            select(TailoredResume)
            .where(TailoredResume.id == resume_id)
            .options(
                selectinload(TailoredResume.evidence_items),
                selectinload(TailoredResume.cover_letter),
                selectinload(TailoredResume.job),
                selectinload(TailoredResume.candidate),
            )
        )
        res = await session.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def update_and_recompile_latex(
        cls, session: AsyncSession, resume_id: uuid.UUID, new_latex_source: str
    ) -> TailoredResume:
        """
        Cập nhật mã nguồn LaTeX đã chỉnh sửa và biên dịch lại tệp tin PDF.
        """
        resume = await cls.get_tailored_resume_by_id(session, resume_id)
        if not resume:
            raise ValueError(f"Tailored resume with ID {resume_id} not found.")

        resume.latex_source = new_latex_source
        compile_ok, pdf_path, comp_err = await latex_compiler.compile_tex(
            tex_content=new_latex_source,
            job_id=str(resume.job_id),
            file_prefix=f"resume_{resume.job_id}",
        )
        if pdf_path:
            resume.pdf_path = pdf_path
        resume.status = ResumeStatusEnum.COMPILED if compile_ok else ResumeStatusEnum.FAILED
        resume.compilation_error = comp_err
        await session.commit()
        await session.refresh(resume)
        return await cls.get_tailored_resume_by_id(session, resume.id)

    @classmethod
    async def get_tailored_resume_by_job_id(
        cls, session: AsyncSession, job_id: uuid.UUID, candidate_id: Optional[uuid.UUID] = None
    ) -> Optional[TailoredResume]:
        """Truy vấn bản Tailored Resume theo Job ID."""
        if not candidate_id:
            candidate = await CandidateRepository.get_profile(session)
            if not candidate:
                return None
            candidate_id = candidate.id

        stmt = (
            select(TailoredResume)
            .where(
                TailoredResume.candidate_id == candidate_id,
                TailoredResume.job_id == job_id,
            )
            .options(
                selectinload(TailoredResume.evidence_items),
                selectinload(TailoredResume.cover_letter),
                selectinload(TailoredResume.job),
                selectinload(TailoredResume.candidate),
            )
        )
        res = await session.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def delete_tailored_resume_by_job_id(
        cls, session: AsyncSession, job_id: uuid.UUID, candidate_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Xóa bản Tailored Resume và Cover Letter theo Job ID, đồng thời dọn dẹp artifacts trên ổ đĩa.
        """
        resume = await cls.get_tailored_resume_by_job_id(session, job_id, candidate_id=candidate_id)
        if not resume:
            return False

        # 1. Xóa file artifacts trên disk
        try:
            job_storage = latex_compiler.get_storage_root() / str(job_id)
            if job_storage.exists() and job_storage.is_dir():
                import shutil
                shutil.rmtree(job_storage, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to delete artifact directory for job {job_id}: {e}")

        # 2. Xóa khỏi database
        await session.delete(resume)
        await session.commit()
        logger.info(f"Deleted tailored resume & cover letter for job_id={job_id}")
        return True

    @classmethod
    async def delete_tailored_resume_by_id(
        cls, session: AsyncSession, resume_id: uuid.UUID
    ) -> bool:
        """
        Xóa bản Tailored Resume và Cover Letter theo ID.
        """
        resume = await cls.get_tailored_resume_by_id(session, resume_id)
        if not resume:
            return False

        # 1. Xóa file artifacts trên disk
        try:
            if resume.job_id:
                job_storage = latex_compiler.get_storage_root() / str(resume.job_id)
                if job_storage.exists() and job_storage.is_dir():
                    import shutil
                    shutil.rmtree(job_storage, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to delete artifact directory for resume {resume_id}: {e}")

        # 2. Xóa khỏi database
        await session.delete(resume)
        await session.commit()
        logger.info(f"Deleted tailored resume ID={resume_id}")
        return True


resume_service = ResumeTailorService()
