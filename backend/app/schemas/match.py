import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobLevelEnum, WorkModeEnum
from app.services.matching.models import (
    ConfidenceLevel,
    Eligibility,
    EvidenceItem,
    EvidenceStatus,
    FilterStatus,
    HardFilterResult,
    MatchSignal,
    RecommendationCategory,
    RequirementEvaluation,
    SkillMatchResult,
)


class MatchSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    score: float
    weight: float
    confidence: ConfidenceLevel
    evidence_status: EvidenceStatus = EvidenceStatus.SUPPORTED
    reason: str
    evidence: List[EvidenceItem] = []


class HardFilterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filter: str
    status: FilterStatus
    reason: str


class JobMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    score: float
    eligibility: Eligibility
    eligibility_reasons: List[str] = []
    recommendation: RecommendationCategory
    is_passed_hard_filters: bool
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []
    missing_preferred_skills: List[str] = []
    warnings: List[str] = []
    scoring_version: str = "v2"
    taxonomy_version: str = "v1"
    created_at: datetime
    updated_at: datetime


class JobMatchDetailResponse(JobMatchResponse):
    explanation: Optional[str] = None
    signals: List[MatchSignalResponse] = []
    hard_filter_results: List[HardFilterResponse] = []
    candidate_snapshot: Optional[dict[str, Any]] = None
    job_snapshot: Optional[dict[str, Any]] = None
    raw_explanation_payload: Optional[dict[str, Any]] = None


class MatchListResponse(BaseModel):
    items: List[JobMatchResponse]
    total: int
    page: int
    page_size: int


class TopRecommendationItem(BaseModel):
    job_id: uuid.UUID
    title: str
    company_name: str
    location: Optional[str] = None
    work_mode: WorkModeEnum
    level: JobLevelEnum
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    score: float
    eligibility: Eligibility
    recommendation: RecommendationCategory
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []
    source: Optional[str] = None
    source_url: Optional[str] = None
    posted_at: Optional[datetime] = None


class MatchCalculateRequest(BaseModel):
    force_refresh: bool = False


class BatchCalculateResponse(BaseModel):
    status: str = "queued"
    total_jobs: int
    message: str
