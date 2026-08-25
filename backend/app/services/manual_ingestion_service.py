import logging
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import (
    Job,
    JobSkill,
    JobStatusEnum,
    RawJob,
    RawJobStatusEnum,
    Skill,
)
from app.schemas.job import (
    ExtractionMetadata,
    JobDetailResponse,
    ManualJobIngestRequest,
    ManualJobIngestResponse,
)
from app.services.ai.embedding_service import embedding_service
from app.services.collectors.base import BaseJobCollector
from app.services.deduplication.dedup_service import dedup_service
from app.services.extraction.extraction_pipeline import extraction_pipeline
from app.services.extraction.url_fetcher import url_fetcher
from app.services.matching.match_service import job_match_service
from app.services.normalization.job_normalizer import job_normalizer
from app.services.normalization.skill_normalizer import skill_normalizer

logger = logging.getLogger("manual_ingestion_service")


class ManualJobIngestionService:
    """
    Orchestration Service cho luồng Manual & Ad-hoc Job Ingestion (Phase 2.5):
    Raw Text / URL -> Content Extract -> Heuristic/LLM Pipeline -> Normalization
    -> Lazy Dedup -> Persist (RawJob + Job + JobSkills) -> Lazy Embedding -> Instant 7-Signal Match.
    """

    async def ingest(
        self,
        db: AsyncSession,
        payload: ManualJobIngestRequest,
    ) -> ManualJobIngestResponse:
        mode = payload.mode.strip().lower()
        clean_text = ""
        initial_title = None
        source_url = None
        source_domain = None
        raw_html = None

        # ----------------------------------------------------------------------
        # 1. INPUT PREPARATION
        # ----------------------------------------------------------------------
        if mode == "text":
            raw_text = (payload.raw_text or "").strip()
            if len(raw_text) < 30:
                return ManualJobIngestResponse(
                    status="failed",
                    message="Nội dung JD thô quá ngắn (yêu cầu tối thiểu 30 ký tự để trích xuất).",
                    extraction_metadata=ExtractionMetadata(
                        method="heuristic",
                        overall_confidence=0.0,
                        extraction_status="FAILED",
                        fields=[],
                        warnings=["Text length is under 30 characters."],
                    ),
                )
            clean_text = raw_text

        elif mode == "url":
            url = (payload.url or "").strip()
            if not url.startswith(("http://", "https://")):
                return ManualJobIngestResponse(
                    status="failed",
                    message="Đường dẫn URL không hợp lệ (phải bắt đầu bằng http:// hoặc https://).",
                    extraction_metadata=ExtractionMetadata(
                        method="heuristic",
                        overall_confidence=0.0,
                        extraction_status="FAILED",
                        fields=[],
                        warnings=["Invalid URL scheme."],
                    ),
                )

            source_url = url
            try:
                parsed_url = urllib.parse.urlparse(url)
                source_domain = parsed_url.netloc.replace("www.", "")
            except Exception:
                source_domain = "unknown"

            doc = await url_fetcher.fetch(url)
            if doc.fetch_method == "failed":
                error_msg = "Không thể lấy nội dung từ đường dẫn này."
                if doc.error == "JS_REQUIRED":
                    error_msg = (
                        "Trang web này sử dụng JavaScript Rendering (SPA/React/Vue) hoặc chặn bot. "
                        "Vui lòng copy và dán trực tiếp nội dung JD ở tab 'Dán văn bản'."
                    )
                elif doc.error and doc.error.startswith("HTTP_"):
                    error_msg = f"Máy chủ tuyển dụng trả về lỗi {doc.error}."
                elif doc.error == "TIMEOUT":
                    error_msg = "Hết thời gian chờ khi kết nối tới máy chủ tuyển dụng (Timeout)."

                return ManualJobIngestResponse(
                    status="failed",
                    message=error_msg,
                    extraction_metadata=ExtractionMetadata(
                        method="url_fetcher",
                        overall_confidence=0.0,
                        extraction_status="FAILED",
                        fields=[],
                        warnings=[f"URL fetch failed: {doc.error}"],
                    ),
                )

            clean_text = doc.clean_text
            initial_title = doc.title or doc.og_title
            raw_html = doc.html
        else:
            return ManualJobIngestResponse(
                status="failed",
                message=f"Chế độ nạp không hợp lệ '{payload.mode}'. Hỗ trợ 'text' hoặc 'url'.",
                extraction_metadata=ExtractionMetadata(
                    method="heuristic",
                    overall_confidence=0.0,
                    extraction_status="FAILED",
                    fields=[],
                    warnings=["Invalid ingestion mode."],
                ),
            )

        # ----------------------------------------------------------------------
        # 2. EXTRACTION (Heuristic + Taxonomy + Confidence-based LLM Fallback)
        # ----------------------------------------------------------------------
        extraction_res = await extraction_pipeline.extract(
            clean_text=clean_text,
            initial_title=initial_title,
            use_llm=payload.use_llm,
        )

        extracted = extraction_res.data
        metadata = ExtractionMetadata(
            method=extraction_res.method,
            overall_confidence=extraction_res.overall_confidence,
            extraction_status=extraction_res.extraction_status,
            fields=[f.model_dump() for f in extraction_res.fields],
            warnings=extraction_res.warnings,
        )

        if extraction_res.extraction_status == "FAILED":
            return ManualJobIngestResponse(
                status="failed",
                message="Không thể trích xuất các trường thông tin cốt lõi từ nội dung được cung cấp.",
                extraction_metadata=metadata,
            )

        # ----------------------------------------------------------------------
        # 3. NORMALIZATION
        # ----------------------------------------------------------------------
        norm_title = job_normalizer.normalize_title(extracted.title)
        norm_company = job_normalizer.normalize_company(extracted.company_name)
        norm_loc, inferred_mode = job_normalizer.normalize_location(extracted.location)
        work_mode = extracted.work_mode if extracted.work_mode != "ONSITE" else inferred_mode
        level = (
            extracted.level
            if extracted.level.value != "UNKNOWN"
            else job_normalizer.normalize_level(extracted.title, extracted.description)
        )
        min_sal, max_sal, curr, is_neg = job_normalizer.normalize_salary(
            extracted.min_salary,
            extracted.max_salary,
            extracted.salary_currency,
            extracted.description,
        )
        contact_email, apply_url = job_normalizer.extract_contact_info(
            extracted.description, source_url=source_url
        )
        if extracted.contact_email:
            contact_email = extracted.contact_email
        if extracted.apply_url:
            apply_url = extracted.apply_url

        dedup_sig = job_normalizer.compute_dedup_signature(
            norm_company, norm_title, norm_loc
        )

        # ----------------------------------------------------------------------
        # 4. LAZY DEDUPLICATION (L1 Exact Hash -> L2 RapidFuzz)
        # ----------------------------------------------------------------------
        dedup_res = await dedup_service.check_duplicate(
            db=db,
            dedup_signature=dedup_sig,
            normalized_company=norm_company,
            normalized_title=norm_title,
            normalized_location=norm_loc,
            job_level=level.value,
        )

        if dedup_res.is_duplicate:
            logger.info(
                f"[Manual Ingestion] Duplicate detected via {dedup_res.strategy}: "
                f"'{norm_title}' at '{norm_company}' (Existing Job ID: {dedup_res.duplicate_job_id})"
            )
            # Load existing job detail
            existing_job = await self._load_job_detail(db, dedup_res.duplicate_job_id)
            match_data = None
            if payload.auto_match and existing_job:
                try:
                    match_obj = await job_match_service.calculate_match_for_job(
                        db, existing_job.id, force_refresh=True
                    )
                    match_data = self._format_match_summary(match_obj)
                except Exception as e:
                    logger.warning(f"Error calculating match for duplicate job: {e}")

            return ManualJobIngestResponse(
                status="duplicate",
                job=JobDetailResponse.model_validate(existing_job) if existing_job else None,
                match=match_data,
                extraction_metadata=metadata,
                message="Tin tuyển dụng này đã tồn tại trong hệ thống. Đã mở bản ghi hiện có.",
            )

        # ----------------------------------------------------------------------
        # 5. PERSIST RAW JOB (Source of Truth with Provenance Metadata)
        # ----------------------------------------------------------------------
        content_hash = BaseJobCollector.compute_content_hash(clean_text)
        raw_payload_data = {
            "original_input": clean_text,
            "ingestion_method": mode,
            "source_domain": source_domain,
            "extraction_method": extraction_res.method,
            "extraction_confidence": extraction_res.overall_confidence,
            "extraction_status": extraction_res.extraction_status,
            "field_confidences": [f.model_dump() for f in extraction_res.fields],
            "warnings": extraction_res.warnings,
        }

        raw_job = RawJob(
            source="manual",
            source_url=source_url or "",
            source_job_id=None,
            content_hash=content_hash,
            raw_payload=raw_payload_data,
            raw_html=raw_html,
            fetch_status=extraction_res.extraction_status,
        )
        db.add(raw_job)
        await db.flush()

        # ----------------------------------------------------------------------
        # 6. LAZY EMBEDDING GENERATION (Only for new non-duplicate jobs)
        # ----------------------------------------------------------------------
        emb_text = f"{norm_title} at {norm_company}. {norm_loc or ''}. {extracted.requirements_summary or extracted.description[:400]}"
        embedding_vec = await embedding_service.generate_embedding(emb_text)

        # ----------------------------------------------------------------------
        # 7. PERSIST STANDARDIZED JOB & SKILLS
        # ----------------------------------------------------------------------
        job = Job(
            raw_job_id=raw_job.id,
            title=extracted.title,
            normalized_title=norm_title,
            company_name=extracted.company_name,
            normalized_company=norm_company,
            location=extracted.location,
            normalized_location=norm_loc,
            work_mode=work_mode,
            level=level,
            min_salary=min_sal,
            max_salary=max_sal,
            salary_currency=curr,
            is_salary_negotiable=is_neg,
            contact_email=contact_email,
            apply_url=apply_url,
            description=clean_text,
            requirements_summary=extracted.requirements_summary,
            benefits_summary=extracted.benefits_summary,
            dedup_signature=dedup_sig,
            embedding=embedding_vec,
            status=JobStatusEnum.ACTIVE,
            posted_at=extracted.posted_at or datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        # Lưu JobSkills
        norm_required_skills = skill_normalizer.normalize_skills(extracted.skills_required)
        norm_nice_skills = skill_normalizer.normalize_skills(extracted.skills_nice_to_have)

        await self._save_job_skills(
            db, job.id, norm_required_skills, is_required=True, confidence=1.0, source="heuristic"
        )
        await self._save_job_skills(
            db, job.id, norm_nice_skills, is_required=False, confidence=0.85, source="inferred"
        )

        await db.commit()

        # ----------------------------------------------------------------------
        # 8. INSTANT MATCH (Deterministic 7-Signal Matching)
        # ----------------------------------------------------------------------
        match_data = None
        if payload.auto_match:
            try:
                match_obj = await job_match_service.calculate_match_for_job(
                    db, job.id, force_refresh=True
                )
                match_data = self._format_match_summary(match_obj)
            except Exception as e:
                logger.warning(f"Error executing instant match for manual job {job.id}: {e}")

        # ----------------------------------------------------------------------
        # 9. ASSEMBLE RESPONSE
        # ----------------------------------------------------------------------
        loaded_job = await self._load_job_detail(db, job.id)
        res_status = "created" if extraction_res.extraction_status == "PARSED" else "partial"
        success_msg = (
            f"Đã nạp và chuẩn hóa thành công tin tuyển dụng '{norm_title}' tại '{norm_company}'!"
            if res_status == "created"
            else f"Đã nạp tin tuyển dụng '{norm_title}' với một số trường suy luận/thiếu."
        )

        return ManualJobIngestResponse(
            status=res_status,
            job=JobDetailResponse.model_validate(loaded_job) if loaded_job else None,
            match=match_data,
            extraction_metadata=metadata,
            message=success_msg,
        )

    async def _load_job_detail(self, db: AsyncSession, job_id) -> Optional[Job]:
        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except Exception:
                pass

        stmt = (
            select(Job)
            .where(Job.id == job_id)
            .options(
                selectinload(Job.skills).selectinload(JobSkill.skill),
                selectinload(Job.raw_job),
            )
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def _save_job_skills(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        skills_list: list,
        is_required: bool,
        confidence: float,
        source: str,
    ):
        for canonical_name, category in skills_list:
            if not canonical_name:
                continue

            stmt = select(Skill).where(Skill.canonical_name == canonical_name)
            res = await db.execute(stmt)
            skill = res.scalars().first()

            if not skill:
                skill = Skill(canonical_name=canonical_name, category=category)
                db.add(skill)
                await db.flush()

            stmt_js = select(JobSkill).where(
                JobSkill.job_id == job_id, JobSkill.skill_id == skill.id
            )
            res_js = await db.execute(stmt_js)
            existing_js = res_js.scalars().first()

            if not existing_js:
                job_skill = JobSkill(
                    job_id=job_id,
                    skill_id=skill.id,
                    is_required=is_required,
                    confidence=confidence,
                    source=source,
                )
                db.add(job_skill)

    def _format_match_summary(self, match_obj) -> dict:
        return {
            "score": match_obj.score,
            "eligibility": match_obj.eligibility.value if hasattr(match_obj.eligibility, "value") else str(match_obj.eligibility),
            "recommendation": match_obj.recommendation.value if hasattr(match_obj.recommendation, "value") else str(match_obj.recommendation),
            "matched_skills": match_obj.matched_skills or [],
            "missing_required_skills": match_obj.missing_required_skills or [],
            "missing_preferred_skills": match_obj.missing_preferred_skills or [],
            "explanation": match_obj.explanation,
            "warnings": match_obj.warnings or [],
        }


manual_ingestion_service = ManualJobIngestionService()
