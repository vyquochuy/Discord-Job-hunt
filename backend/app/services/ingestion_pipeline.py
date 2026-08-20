import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel
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
    SkillAlias,
)
from app.services.ai.embedding_service import embedding_service
from app.services.ai.llm_extractor import llm_extractor
from app.services.collectors.base import BaseJobCollector, RawJobData
from app.services.deduplication.dedup_service import dedup_service
from app.services.normalization.job_normalizer import job_normalizer
from app.services.normalization.skill_normalizer import skill_normalizer

logger = logging.getLogger("ingestion_pipeline")


class IngestionStats(BaseModel):
    source: str
    total_fetched: int = 0
    unchanged: int = 0
    duplicates_detected: int = 0
    created: int = 0
    errors: int = 0


class JobIngestionPipeline:
    """
    Toàn bộ luồng xử lý và chuẩn hóa tin tuyển dụng:
    Collector Fetch -> Content Hash Check -> Deterministic Parse -> LLM Extract
    -> Normalization -> Deduplication -> DB Storage + Embedding.
    """

    async def run(
        self,
        collector: BaseJobCollector,
        db: AsyncSession,
        limit: int = 20,
    ) -> IngestionStats:
        stats = IngestionStats(source=collector.source_name)
        logger.info(f"Starting job ingestion from source '{collector.source_name}' (limit={limit})...")

        # 1. Thu thập dữ liệu thô từ Collector
        raw_items: List[RawJobData] = await collector.fetch_jobs(limit=limit)
        stats.total_fetched = len(raw_items)

        # 2. Xử lý từng Raw Item
        for raw_data in raw_items:
            try:
                # BƯỚC 1: Kiểm tra Content Hash SHA-256 (0 cost token)
                stmt_hash = select(RawJob).where(RawJob.content_hash == raw_data.content_hash)
                res_hash = await db.execute(stmt_hash)
                existing_raw = res_hash.scalars().first()

                if existing_raw:
                    # Hash không đổi -> Cập nhật last_seen_at
                    existing_raw.last_seen_at = datetime.now(timezone.utc)
                    await db.commit()
                    stats.unchanged += 1
                    logger.debug(f"[Ingestion] Job unchanged (hash match): {raw_data.source_url}")
                    continue

                # BƯỚC 2: Lưu Raw Job vào Database (Source of Truth)
                stmt_url = select(RawJob).where(
                    RawJob.source == raw_data.source,
                    RawJob.source_url == raw_data.source_url,
                )
                res_url = await db.execute(stmt_url)
                raw_job = res_url.scalars().first()

                if raw_job:
                    raw_job.content_hash = raw_data.content_hash
                    raw_job.raw_payload = raw_data.raw_payload
                    raw_job.raw_html = raw_data.raw_html
                    raw_job.last_seen_at = datetime.now(timezone.utc)
                    raw_job.fetch_status = RawJobStatusEnum.FETCHED.value
                else:
                    raw_job = RawJob(
                        source=raw_data.source,
                        source_url=raw_data.source_url,
                        source_job_id=raw_data.source_job_id,
                        content_hash=raw_data.content_hash,
                        raw_payload=raw_data.raw_payload,
                        raw_html=raw_data.raw_html,
                        fetch_status=RawJobStatusEnum.FETCHED.value,
                    )
                    db.add(raw_job)

                await db.flush()

                # BƯỚC 3: Deterministic Parsing
                extracted = await collector.parse_raw(raw_data)

                # BƯỚC 4: LLM Extraction (Bóc tách skills/requirements chi tiết)
                extracted = await llm_extractor.extract_job_details(
                    extracted.description, extracted
                )

                # BƯỚC 5: Normalization
                norm_title = job_normalizer.normalize_title(extracted.title)
                norm_company = job_normalizer.normalize_company(extracted.company_name)
                norm_loc, inferred_mode = job_normalizer.normalize_location(extracted.location)
                
                work_mode = extracted.work_mode if extracted.work_mode != "ONSITE" else inferred_mode
                level = extracted.level if extracted.level.value != "UNKNOWN" else job_normalizer.normalize_level(extracted.title, extracted.description)
                min_sal, max_sal, curr, is_neg = job_normalizer.normalize_salary(
                    extracted.min_salary, extracted.max_salary, extracted.salary_currency, extracted.description
                )
                dedup_sig = job_normalizer.compute_dedup_signature(norm_company, norm_title, norm_loc)

                # BƯỚC 6: Deduplication Check (Exact -> Fuzzy -> Semantic)
                dedup_res = await dedup_service.check_duplicate(
                    db=db,
                    dedup_signature=dedup_sig,
                    normalized_company=norm_company,
                    normalized_title=norm_title,
                    normalized_location=norm_loc,
                    job_level=level.value,
                )

                if dedup_res.is_duplicate:
                    logger.info(f"[Ingestion] Duplicate detected via {dedup_res.strategy}: {extracted.title}")
                    raw_job.fetch_status = "DUPLICATE"
                    await db.commit()
                    stats.duplicates_detected += 1
                    continue

                # BƯỚC 7: Vector Embedding Generation (pgvector)
                emb_text = f"{norm_title} at {norm_company}. {norm_loc or ''}. {extracted.requirements_summary or extracted.description[:400]}"
                embedding_vec = await embedding_service.generate_embedding(emb_text)

                # BƯỚC 8: Lưu Standardized Job
                # Kiểm tra nếu job đã tồn tại với raw_job_id (trường hợp re-parse)
                stmt_job = select(Job).where(Job.raw_job_id == raw_job.id)
                res_job = await db.execute(stmt_job)
                job = res_job.scalars().first()

                if not job:
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
                        description=extracted.description,
                        requirements_summary=extracted.requirements_summary,
                        benefits_summary=extracted.benefits_summary,
                        dedup_signature=dedup_sig,
                        embedding=embedding_vec,
                        status=JobStatusEnum.ACTIVE,
                        posted_at=extracted.posted_at or datetime.now(timezone.utc),
                    )
                    db.add(job)
                    await db.flush()
                else:
                    # Update fields
                    job.title = extracted.title
                    job.normalized_title = norm_title
                    job.company_name = extracted.company_name
                    job.normalized_company = norm_company
                    job.location = extracted.location
                    job.normalized_location = norm_loc
                    job.work_mode = work_mode
                    job.level = level
                    job.min_salary = min_sal
                    job.max_salary = max_sal
                    job.salary_currency = curr
                    job.is_salary_negotiable = is_neg
                    job.description = extracted.description
                    job.requirements_summary = extracted.requirements_summary
                    job.benefits_summary = extracted.benefits_summary
                    job.dedup_signature = dedup_sig
                    job.embedding = embedding_vec
                    await db.flush()

                # BƯỚC 9: Chuẩn hóa Skill & Lưu JobSkill
                norm_required_skills = skill_normalizer.normalize_skills(extracted.skills_required)
                norm_nice_skills = skill_normalizer.normalize_skills(extracted.skills_nice_to_have)

                await self._save_job_skills(
                    db, job.id, norm_required_skills, is_required=True, confidence=1.0, source="explicit"
                )
                await self._save_job_skills(
                    db, job.id, norm_nice_skills, is_required=False, confidence=0.85, source="llm"
                )

                raw_job.fetch_status = RawJobStatusEnum.PARSED.value
                await db.commit()
                stats.created += 1
                logger.info(f"[Ingestion] Successfully ingested job: '{norm_title}' at '{norm_company}'")

            except Exception as e:
                logger.error(f"[Ingestion Error] Failed processing raw job {raw_data.source_url}: {e}", exc_info=True)
                stats.errors += 1
                await db.rollback()

        logger.info(
            f"Ingestion finished for {collector.source_name}: "
            f"Total={stats.total_fetched}, Created={stats.created}, "
            f"Unchanged={stats.unchanged}, Duplicates={stats.duplicates_detected}, Errors={stats.errors}"
        )
        return stats

    async def _save_job_skills(
        self,
        db: AsyncSession,
        job_id,
        skills_list: List[tuple],
        is_required: bool,
        confidence: float,
        source: str,
    ):
        """Helper tìm hoặc tạo Skill trong Taxonomy và liên kết JobSkill."""
        for canonical_name, category in skills_list:
            if not canonical_name:
                continue

            # Tìm canonical skill
            stmt = select(Skill).where(Skill.canonical_name == canonical_name)
            res = await db.execute(stmt)
            skill = res.scalars().first()

            if not skill:
                skill = Skill(canonical_name=canonical_name, category=category)
                db.add(skill)
                await db.flush()

            # Thêm JobSkill nếu chưa tồn tại
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


# Singleton Instance
ingestion_pipeline = JobIngestionPipeline()
