import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.resume import (
    ApplicationChannelEnum,
    ApplicationStatusEnum,
    ResumeStatusEnum,
)


class EvidenceMapItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = None
    section: str = Field(..., description="Mục CV: PROJECTS, EXPERIENCE, SKILLS, SUMMARY")
    bullet_index: int = 0
    claim_text: str = Field(..., description="Nội dung claim trong CV được tạo ra")
    source_entity_type: str = Field(..., description="PROJECT, EXPERIENCE, SKILL, EDUCATION")
    source_entity_id: Optional[str] = None
    original_fact: str = Field(..., description="Bằng chứng sự thật gốc trong profile / master resume")
    is_verified: bool = True
    similarity_score: float = 1.0
    notes: Optional[str] = None


class CoverLetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tailored_resume_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    recipient_name: Optional[str] = None
    company_name: str
    salutation: str = "Dear Hiring Team,"
    hook_statement: Optional[str] = None
    content_markdown: str
    key_alignments: List[str] = []
    created_at: datetime


class TailoredResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    version: int
    target_title: str
    summary_objective: Optional[str] = None
    latex_source: str
    pdf_path: Optional[str] = None
    provenance_score: float
    is_provenance_verified: bool
    matched_skills: List[str] = []
    highlighted_projects: List[str] = []
    status: ResumeStatusEnum
    compilation_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    evidence_items: List[EvidenceMapItem] = []
    cover_letter: Optional[CoverLetterResponse] = None


class TailoredResumeSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    target_title: str
    provenance_score: float
    is_provenance_verified: bool
    status: ResumeStatusEnum
    pdf_path: Optional[str] = None
    matched_skills: List[str] = []
    created_at: datetime


class TailorResumeRequest(BaseModel):
    candidate_id: Optional[uuid.UUID] = None
    force_regenerate: bool = False
    custom_tone: Optional[str] = Field("professional_and_humble", description="Văn phong: professional_and_humble, technical_detailed, concise")


class ApplicationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    tailored_resume_id: uuid.UUID
    cover_letter_id: Optional[uuid.UUID] = None
    channel: ApplicationChannelEnum
    status: ApplicationStatusEnum
    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


class ApplicationSubmitRequest(BaseModel):
    channel: ApplicationChannelEnum = ApplicationChannelEnum.EMAIL
    recipient_email: Optional[str] = Field(None, description="Email người nhận (nếu bỏ trống sẽ lấy từ Job contact_email)")
    subject: Optional[str] = None
    body: Optional[str] = None
    simulate_only: bool = Field(False, description="True nếu chỉ tạo draft / ghi log mà không gửi email thật")


class ApplicationStatusUpdateRequest(BaseModel):
    status: ApplicationStatusEnum
    error_message: Optional[str] = None

