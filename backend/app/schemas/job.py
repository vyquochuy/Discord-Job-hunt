import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.job import (
    WorkModeEnum,
    JobLevelEnum,
    JobStatusEnum,
    RawJobStatusEnum,
    SkillCategoryEnum,
)


# ==============================================================================
# Raw Job Schemas (Source of Truth)
# ==============================================================================

class RawJobBase(BaseModel):
    source: str = Field(..., description="Nền tảng cào: itviec, remotive, etc.", examples=["itviec", "remotive"])
    source_url: str = Field(..., description="Đường dẫn gốc của tin tuyển dụng")
    source_job_id: Optional[str] = Field(None, description="ID của tin tuyển dụng trên sàn gốc")
    raw_payload: Optional[dict[str, Any]] = Field(default_factory=dict, description="Dữ liệu JSON gốc nếu có")
    raw_html: Optional[str] = Field(None, description="Mã nguồn HTML thô nếu cào bằng web scraping")


class RawJobCreate(RawJobBase):
    content_hash: str = Field(..., description="SHA-256 hash của nội dung JD thô")
    fetch_status: RawJobStatusEnum = Field(default=RawJobStatusEnum.FETCHED)


class RawJobResponse(RawJobBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_hash: str
    fetch_status: str
    error_message: Optional[str] = None
    fetched_at: datetime
    last_seen_at: datetime


# ==============================================================================
# Skill Taxonomy Schemas
# ==============================================================================

class SkillAliasBase(BaseModel):
    alias: str = Field(..., description="Từ đồng nghĩa/biến thể của kỹ năng (lowercase)", examples=["python3", "postgres"])


class SkillAliasCreate(SkillAliasBase):
    pass


class SkillAliasResponse(SkillAliasBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_id: uuid.UUID


class SkillTaxonomyBase(BaseModel):
    canonical_name: str = Field(..., description="Tên kỹ năng chuẩn hóa", examples=["Python", "PostgreSQL", "AWS"])
    category: SkillCategoryEnum = Field(default=SkillCategoryEnum.OTHER, description="Nhóm kỹ năng")


class SkillTaxonomyCreate(SkillTaxonomyBase):
    aliases: Optional[List[str]] = Field(default_factory=list, description="Danh sách từ đồng nghĩa khởi tạo")


class SkillTaxonomyResponse(SkillTaxonomyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    aliases: List[SkillAliasResponse] = []


# ==============================================================================
# Job Skill Association Schemas
# ==============================================================================

class JobSkillBase(BaseModel):
    skill_name: str = Field(..., description="Tên canonical của skill", examples=["Python", "FastAPI"])
    is_required: bool = Field(default=True, description="True nếu là bắt buộc, False nếu nice-to-have")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Độ tin cậy trích xuất")
    source: str = Field(default="explicit", description="Nguồn trích xuất: explicit, llm, inferred")


class JobSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_id: uuid.UUID
    canonical_name: str = ""
    category: str = "OTHER"
    is_required: bool
    confidence: float
    source: str


# ==============================================================================
# Extracted Job Data (Parser/LLM Output DTO)
# ==============================================================================

class JobExtractedData(BaseModel):
    """
    Dữ liệu trung gian sau khi trích xuất bằng Deterministic Parser và LLM
    trước khi được chuẩn hóa và lưu vào Database.
    """
    title: str
    company_name: str
    location: Optional[str] = None
    work_mode: WorkModeEnum = WorkModeEnum.ONSITE
    level: JobLevelEnum = JobLevelEnum.UNKNOWN
    
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    is_salary_negotiable: bool = False

    contact_email: Optional[str] = None
    apply_url: Optional[str] = None
    
    description: str
    requirements_summary: Optional[str] = None
    benefits_summary: Optional[str] = None
    
    skills_required: List[str] = Field(default_factory=list)
    skills_nice_to_have: List[str] = Field(default_factory=list)
    
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


# ==============================================================================
# Standardized Job Schemas
# ==============================================================================

class JobBase(BaseModel):
    title: str = Field(..., examples=["Senior Backend Developer"])
    company_name: str = Field(..., examples=["Tech Corp"])
    location: Optional[str] = Field(None, examples=["Ho Chi Minh City"])
    work_mode: WorkModeEnum = Field(default=WorkModeEnum.ONSITE)
    level: JobLevelEnum = Field(default=JobLevelEnum.UNKNOWN)
    
    min_salary: Optional[float] = Field(None, examples=[1500.0])
    max_salary: Optional[float] = Field(None, examples=[3000.0])
    salary_currency: Optional[str] = Field(None, examples=["USD", "VND"])
    is_salary_negotiable: bool = Field(default=False)

    contact_email: Optional[str] = Field(None, examples=["hr@company.com"])
    apply_url: Optional[str] = Field(None, examples=["https://company.com/careers/apply/123"])
    
    description: str = Field(..., description="Văn bản JD đầy đủ")
    requirements_summary: Optional[str] = None
    benefits_summary: Optional[str] = None
    status: JobStatusEnum = Field(default=JobStatusEnum.ACTIVE)
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class JobCreate(JobBase):
    raw_job_id: uuid.UUID
    normalized_title: str
    normalized_company: str
    normalized_location: Optional[str] = None
    dedup_signature: Optional[str] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[WorkModeEnum] = None
    level: Optional[JobLevelEnum] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    contact_email: Optional[str] = None
    apply_url: Optional[str] = None
    description: Optional[str] = None
    status: Optional[JobStatusEnum] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_job_id: uuid.UUID
    title: str
    normalized_title: str
    company_name: str
    normalized_company: str
    location: Optional[str] = None
    normalized_location: Optional[str] = None
    work_mode: WorkModeEnum
    level: JobLevelEnum
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    is_salary_negotiable: bool
    contact_email: Optional[str] = None
    apply_url: Optional[str] = None
    status: JobStatusEnum
    source: Optional[str] = None
    source_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime



class JobDetailResponse(JobResponse):
    description: str
    requirements_summary: Optional[str] = None
    benefits_summary: Optional[str] = None
    dedup_signature: Optional[str] = None
    raw_job: Optional[RawJobResponse] = None
    skills: List[JobSkillResponse] = []


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
