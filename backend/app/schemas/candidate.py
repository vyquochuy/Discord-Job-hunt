import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


# ==============================================================================
# Skill Schemas
# ==============================================================================

class SkillBase(BaseModel):
    category: str = Field(
        ...,
        description="Danh mục kỹ năng: programming, frameworks, tools_databases, security, soft_skills, languages, ai_ml",
        examples=["programming", "frameworks"],
    )
    name: str = Field(..., description="Tên kỹ năng", examples=["Python", "React"])
    proficiency: Optional[str] = Field(
        None, description="Trình độ: Native, B1, Advanced, etc.", examples=["Native", "B1"]
    )


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    proficiency: Optional[str] = None


class SkillResponse(SkillBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    created_at: datetime


# ==============================================================================
# Experience Schemas
# ==============================================================================

class ExperienceBase(BaseModel):
    company: str = Field(..., description="Tên công ty hoặc tổ chức")
    role: str = Field(..., description="Vị trí / chức danh")
    period: Optional[str] = Field(None, description="Khoảng thời gian, vd: '2023-01 to 2024-06'")
    location: Optional[str] = Field(None, description="Địa điểm làm việc")
    description: Optional[str] = Field(None, description="Mô tả công việc tổng quan")
    achievements: List[str] = Field(
        default_factory=list,
        description="Danh sách các minh chứng / thành tựu định lượng đã kiểm chứng",
    )
    order: int = Field(0, description="Thứ tự hiển thị")


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    period: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    achievements: Optional[List[str]] = None
    order: Optional[int] = None


class ExperienceResponse(ExperienceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    created_at: datetime


# ==============================================================================
# Project Schemas
# ==============================================================================

class ProjectEvidencePoint(BaseModel):
    title: str = Field(..., description="Tiêu đề thành phần kỹ thuật (vd: Cryptography & E2EE)")
    detail: str = Field(..., description="Chi tiết thực hiện kèm số liệu đo lường cụ thể")


class ProjectBase(BaseModel):
    name: str = Field(..., description="Tên dự án")
    role: Optional[str] = Field(None, description="Vai trò trong dự án")
    summary: Optional[str] = Field(None, description="Tóm tắt ngắn gọn dự án")
    period: Optional[str] = Field(None, description="Thời gian thực hiện dự án")
    repository_url: Optional[str] = Field(None, description="Link mã nguồn Git")
    demo_url: Optional[str] = Field(None, description="Link Demo / Production")
    technologies: List[str] = Field(
        default_factory=list, description="Danh sách công nghệ sử dụng (Ground Truth duy nhất)"
    )
    core: Optional[dict[str, Any]] = Field(
        None,
        description="Core Technical Differentiator / USP của dự án (Bắt buộc 1, bất biến)",
    )
    supporting_evidence: Optional[List[dict[str, Any]]] = Field(
        default_factory=list,
        description="Danh sách các minh chứng kỹ thuật bổ trợ",
    )
    evidence_points: List[dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách các minh chứng kỹ thuật sâu (E2EE, WebSocket, Rate-Limiting...)",
    )
    order: int = Field(0, description="Thứ tự hiển thị")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    summary: Optional[str] = None
    period: Optional[str] = None
    repository_url: Optional[str] = None
    demo_url: Optional[str] = None
    technologies: Optional[List[str]] = None
    core: Optional[dict[str, Any]] = None
    supporting_evidence: Optional[List[dict[str, Any]]] = None
    evidence_points: Optional[List[dict[str, Any]]] = None
    order: Optional[int] = None


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    created_at: datetime


# ==============================================================================
# Certification Schemas
# ==============================================================================

class CertificationBase(BaseModel):
    name: str = Field(..., description="Tên chứng chỉ")
    issuer: Optional[str] = Field(None, description="Đơn vị cấp")
    issue_year: Optional[int] = Field(None, description="Năm cấp")
    credential_url: Optional[str] = Field(None, description="Link xác thực chứng chỉ")


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    issue_year: Optional[int] = None
    credential_url: Optional[str] = None


class CertificationResponse(CertificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    created_at: datetime


# ==============================================================================
# Candidate Education & Preference Helpers
# ==============================================================================

class EducationItem(BaseModel):
    institution: str = Field(..., description="Trường / Tổ chức đào tạo")
    degree: Optional[str] = Field(None, description="Bằng cấp")
    field: Optional[str] = Field(None, description="Chuyên ngành")
    graduation_year: Optional[int] = Field(None, description="Năm tốt nghiệp (hoặc dự kiến)")
    gpa: Optional[str] = Field(None, description="Điểm GPA, vd: '3.15/4.0'")
    coursework: List[str] = Field(default_factory=list, description="Môn học tiêu biểu")


class PreferencesItem(BaseModel):
    employment_types: List[str] = Field(
        default_factory=list, description="Loại công việc mong muốn: Internship, Full-time, etc."
    )
    remote: Optional[Any] = Field(None, description="Chính sách làm việc từ xa: true, false, 'hybrid'")
    minimum_salary: Optional[float] = Field(None, description="Mức lương tối thiểu mong muốn")
    currency: Optional[str] = Field(None, description="Đơn vị tiền tệ: USD, VND")


# ==============================================================================
# Candidate Profile Schemas
# ==============================================================================

class CandidateBase(BaseModel):
    full_name: str = Field(..., description="Họ và tên ứng viên")
    headline: Optional[str] = Field(None, description="Chức danh tóm tắt (vd: System Intern)")
    email: Optional[str] = Field(None, description="Email liên hệ")
    phone: Optional[str] = Field(None, description="Số điện thoại")
    location: Optional[str] = Field(None, description="Địa điểm sinh sống")
    github_url: Optional[str] = Field(None, description="GitHub Profile URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn Profile URL")
    portfolio_url: Optional[str] = Field(None, description="Personal Website URL")
    summary: Optional[str] = Field(None, description="Mục tiêu hoặc tóm tắt kinh nghiệm")
    education: List[dict[str, Any]] = Field(
        default_factory=list, description="Danh sách thông tin học vấn"
    )
    target_roles: List[str] = Field(
        default_factory=list, description="Các vị trí ứng tuyển mục tiêu"
    )
    target_locations: List[str] = Field(
        default_factory=list, description="Địa điểm làm việc mục tiêu"
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="Sở thích & yêu cầu làm việc"
    )


class CandidateCreate(CandidateBase):
    raw_master_resume_md: Optional[str] = None
    raw_master_resume_tex: Optional[str] = None


class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    education: Optional[List[dict[str, Any]]] = None
    target_roles: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    preferences: Optional[dict[str, Any]] = None
    raw_master_resume_md: Optional[str] = None
    raw_master_resume_tex: Optional[str] = None


class CandidateDetailResponse(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_master_resume_md: Optional[str] = None
    raw_master_resume_tex: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    skills: List[SkillResponse] = Field(default_factory=list)
    experiences: List[ExperienceResponse] = Field(default_factory=list)
    projects: List[ProjectResponse] = Field(default_factory=list)
    certifications: List[CertificationResponse] = Field(default_factory=list)


# ==============================================================================
# Ingestion / Sync Schemas
# ==============================================================================

class CandidateSyncResponse(BaseModel):
    success: bool
    candidate_id: uuid.UUID
    full_name: str
    skills_count: int
    projects_count: int
    experiences_count: int
    certifications_count: int
    message: str
