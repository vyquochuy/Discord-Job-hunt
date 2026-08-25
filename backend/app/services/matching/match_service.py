import logging
import re
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.job import Job, JobSkill, JobStatusEnum
from app.models.match import JobMatch
from app.repositories.candidate import CandidateRepository
from app.repositories.match import match_repository
from app.services.matching.explanation_service import explanation_service
from app.services.matching.models import (
    CandidateEducationDTO,
    CandidateExperienceDTO,
    CandidateProfileDTO,
    CandidateProjectDTO,
    CandidateSnapshot,
    Eligibility,
    JobMatchInputDTO,
    JobSnapshot,
    RecommendationCategory,
)
from app.services.matching.scoring_engine import calculate_match_score
from app.services.matching.semantic_matcher import compute_project_relevance
from app.services.normalization.skill_normalizer import skill_normalizer

logger = logging.getLogger("match_service")


class JobMatchService:
    """
    Orchestration service điều phối toàn bộ luồng Job Intelligence:
    1. Chuẩn bị DTOs và Snapshot từ DB
    2. Gọi Pure Matching Engines (Hard filters, Skill matcher, Semantic matcher, Scoring engine)
    3. Sinh nhận xét (Deterministic / LLM)
    4. Lưu vết bền vững vào bảng job_matches
    """

    @staticmethod
    def candidate_to_dto(candidate: Candidate) -> CandidateProfileDTO:

        """Chuyển đổi ORM Candidate sang Pure Domain DTO."""
        projects = [
            CandidateProjectDTO(
                name=p.name,
                role=getattr(p, "role", None),
                summary=p.summary,
                technologies=p.technologies or [],
                evidence=p.evidence_points or [],
            )
            for p in candidate.projects
        ]

        experiences = [
            CandidateExperienceDTO(
                company=e.company,
                role=e.role,
                description=e.description,
                achievements=e.achievements or [],
            )
            for e in candidate.experiences
        ]

        education = []
        if candidate.education:
            for edu in candidate.education:
                if isinstance(edu, dict):
                    education.append(
                        CandidateEducationDTO(
                            institution=edu.get("institution", "University"),
                            degree=edu.get("degree"),
                            field=edu.get("field"),
                            graduation_year=edu.get("graduation_year"),
                            gpa=edu.get("gpa"),
                            coursework=edu.get("coursework", []),
                        )
                    )

        skills = [s.name for s in candidate.skills if s.name]
        soft_skills = [
            s.name for s in candidate.skills
            if getattr(s, "category", "") in ("SOFT_SKILL", "soft_skills", "COMPETENCY")
        ]
        if not soft_skills:
            soft_skills = ["Problem-solving", "System design thinking", "Technical documentation", "Teamwork"]

        return CandidateProfileDTO(
            id=candidate.id,
            full_name=candidate.full_name,
            headline=candidate.headline,
            location=candidate.location,
            summary=candidate.summary,
            target_roles=candidate.target_roles or [],
            target_locations=candidate.target_locations or [],
            preferences=candidate.preferences or {},
            skills=skills,
            soft_skills=soft_skills,
            projects=projects,
            experiences=experiences,
            education=education,
        )


    @staticmethod
    def job_to_dto(job: Job) -> JobMatchInputDTO:
        """Chuyển đổi ORM Job sang Pure Domain DTO."""
        req_skills: List[str] = []
        pref_skills: List[str] = []

        noise_patterns = [
            r"kinh nghi[ệe]m",
            r"\+\d+",
            r"soft\.\.\.",
            r"đ[ạa]i h[ọo]c",
            r"tr[ởo] l[êe]n",
            r"software engineer",
            r"it - ph",
        ]

        for js in job.skills:
            raw_name = js.canonical_name or (js.skill.canonical_name if js.skill else "")
            if not raw_name or not raw_name.strip():
                continue

            # Bỏ qua các chuỗi rác trích xuất từ HTML tags
            is_noise = any(re.search(pat, raw_name, re.IGNORECASE) for pat in noise_patterns)
            if is_noise or len(raw_name) > 35:
                continue

            canonical, category = skill_normalizer.normalize_skill(raw_name)
            # Chỉ nhận skill nếu thuộc Canonical Taxonomy hoặc category != OTHER
            if canonical and (skill_normalizer.is_known_skill(raw_name) or str(category).upper() != "OTHER"):
                if js.is_required:
                    req_skills.append(canonical)
                else:
                    pref_skills.append(canonical)

        return JobMatchInputDTO(

            id=job.id,
            title=job.title,
            company_name=job.company_name,
            location=job.location,
            normalized_location=job.normalized_location,
            work_mode=job.work_mode,
            level=job.level,
            min_salary=job.min_salary,
            max_salary=job.max_salary,
            salary_currency=job.salary_currency,
            is_salary_negotiable=job.is_salary_negotiable,
            description=job.description,
            requirements_summary=job.requirements_summary,
            required_skills=req_skills,
            preferred_skills=pref_skills,
            embedding=job.embedding,
        )

    @classmethod
    async def get_candidate_or_raise(
        cls, session: AsyncSession, candidate_id: Optional[uuid.UUID] = None
    ) -> Candidate:
        """Lấy hồ sơ ứng viên active từ DB."""
        if candidate_id:
            candidate = await CandidateRepository.get_by_id(session, candidate_id)
        else:
            candidate = await CandidateRepository.get_profile(session)

        if not candidate:
            raise ValueError(
                "Không tìm thấy hồ sơ ứng viên. Vui lòng đồng bộ profile qua /profile sync trước."
            )
        return candidate

    @classmethod
    async def calculate_match_for_job(
        cls,
        session: AsyncSession,
        job_id: uuid.UUID,
        candidate_id: Optional[uuid.UUID] = None,
        force_refresh: bool = False,
    ) -> JobMatch:
        """
        Tính toán và lưu trữ kết quả phân tích match cho 1 tin tuyển dụng.
        Nếu đã tồn tại và không yêu cầu force_refresh, trả về bản ghi cached.
        """
        candidate = await cls.get_candidate_or_raise(session, candidate_id)

        # Kiểm tra cache
        if not force_refresh:
            existing = await match_repository.get_match_by_job_id(
                session, candidate.id, job_id
            )
            if existing:
                return existing

        # Lấy chi tiết Job từ DB
        stmt = (
            select(Job)
            .where(Job.id == job_id)
            .options(
                selectinload(Job.skills).selectinload(JobSkill.skill),
                selectinload(Job.raw_job),
            )
        )
        result = await session.execute(stmt)
        job = result.scalars().first()

        if not job:
            raise ValueError(f"Không tìm thấy tin tuyển dụng với ID {job_id}")

        # 1. Chuyển đổi sang Domain DTOs
        cand_dto = cls.candidate_to_dto(candidate)
        job_dto = cls.job_to_dto(job)

        # 2. Chạy Pure Matching Engine
        score_res = calculate_match_score(
            candidate=cand_dto,
            job=job_dto,
        )


        # 3. Sinh nhận xét / giải thích
        explanation_text, raw_exp_payload = await explanation_service.generate_explanation(
            cand_dto, job_dto, score_res
        )

        # 4. Tạo Snapshots
        min_sal = cand_dto.preferences.get("minimum_salary") if cand_dto.preferences else None
        if isinstance(min_sal, dict):
            salary_curr = min_sal.get("currency") or cand_dto.preferences.get("currency", "VND")
            min_sal_val = min_sal.get("value")
        else:
            salary_curr = cand_dto.preferences.get("currency", "VND") if cand_dto.preferences else "VND"
            min_sal_val = min_sal

        cand_snapshot = CandidateSnapshot(
            skills=cand_dto.skills,
            target_roles=cand_dto.target_roles,
            target_locations=cand_dto.target_locations,
            location=cand_dto.location,
            work_mode_preference=cand_dto.preferences.get("remote") if cand_dto.preferences else None,
            minimum_salary=min_sal_val,
            salary_currency=salary_curr,
            education_count=len(cand_dto.education),
            experience_count=len(cand_dto.experiences),
            project_count=len(cand_dto.projects),
        ).model_dump()

        job_snapshot = JobSnapshot(
            title=job_dto.title,
            company=job_dto.company_name,
            required_skills=job_dto.required_skills,
            preferred_skills=job_dto.preferred_skills,
            work_mode=job_dto.work_mode.value,
            level=job_dto.level.value,
            location=job_dto.location,
            min_salary=job_dto.min_salary,
            max_salary=job_dto.max_salary,
            salary_currency=job_dto.salary_currency,
            is_salary_negotiable=job_dto.is_salary_negotiable,
        ).model_dump()

        # 5. Lưu vào Database
        match_obj = JobMatch(
            candidate_id=candidate.id,
            job_id=job.id,
            score=score_res.score,
            eligibility=score_res.eligibility,
            eligibility_reasons=score_res.eligibility_reasons,
            recommendation=score_res.recommendation,
            is_passed_hard_filters=(score_res.eligibility != Eligibility.BLOCKED),
            hard_filter_results=[f.model_dump() for f in score_res.hard_filter_results],
            matched_skills=score_res.skill_match.matched_required,
            missing_required_skills=score_res.skill_match.missing_required,
            missing_preferred_skills=score_res.skill_match.missing_preferred,
            signals=[s.model_dump() for s in score_res.signals],
            warnings=score_res.warnings,
            explanation=explanation_text,
            raw_explanation_payload=raw_exp_payload,
            scoring_version=score_res.scoring_version,
            taxonomy_version=score_res.taxonomy_version,
            candidate_snapshot=cand_snapshot,
            job_snapshot=job_snapshot,
        )

        return await match_repository.upsert_match(session, match_obj)

    @classmethod
    async def batch_calculate_all(
        cls, session: AsyncSession, candidate_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Tính toán match hàng loạt cho tất cả các tin tuyển dụng đang ACTIVE.
        """
        candidate = await cls.get_candidate_or_raise(session, candidate_id)

        stmt = select(Job.id).where(Job.status == JobStatusEnum.ACTIVE)
        result = await session.execute(stmt)
        job_ids = result.scalars().all()

        count = 0
        for j_id in job_ids:
            try:
                await cls.calculate_match_for_job(
                    session, j_id, candidate.id, force_refresh=True
                )
                count += 1
            except Exception as e:
                logger.error(f"Error calculating match for job {j_id}: {e}")

        return count

    @classmethod
    async def get_top_recommendations(
        cls,
        session: AsyncSession,
        candidate_id: Optional[uuid.UUID] = None,
        limit: int = 10,
        min_score: float = 60.0,
    ) -> List[JobMatch]:
        candidate = await cls.get_candidate_or_raise(session, candidate_id)
        return await match_repository.get_top_recommendations(
            session, candidate.id, limit=limit, min_score=min_score
        )

    @classmethod
    async def list_matches(
        cls,
        session: AsyncSession,
        candidate_id: Optional[uuid.UUID] = None,
        min_score: Optional[float] = None,
        eligibility: Optional[Eligibility] = None,
        recommendation: Optional[RecommendationCategory] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[JobMatch], int]:
        candidate = await cls.get_candidate_or_raise(session, candidate_id)
        return await match_repository.list_matches(
            session,
            candidate.id,
            min_score=min_score,
            eligibility=eligibility,
            recommendation=recommendation,
            page=page,
            page_size=page_size,
        )


job_match_service = JobMatchService()
