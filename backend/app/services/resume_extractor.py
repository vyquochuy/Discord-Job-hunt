import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("resume_extractor")


# ==============================================================================
# Pydantic Schemas for Structured CV Extraction
# ==============================================================================

class ExtractedCandidateContact(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    summary: Optional[str] = None


class ExtractedEducationItem(BaseModel):
    institution: str = Field(..., description="Tên trường / đại học")
    degree: Optional[str] = Field(None, description="Hệ / Bằng cấp: Cử nhân, Kỹ sư, Thạc sĩ...")
    field: Optional[str] = Field(None, description="Chuyên ngành")
    graduation_year: Optional[int] = Field(None, description="Năm tốt nghiệp")
    gpa: Optional[str] = Field(None, description="Điểm GPA")
    coursework: List[str] = Field(default_factory=list, description="Môn học tiêu biểu")


class ExtractedProjectItem(BaseModel):
    name: str = Field(..., description="Tên dự án")
    role: Optional[str] = Field(None, description="Vai trò trong dự án")
    period: Optional[str] = Field(None, description="Thời gian thực hiện")
    technologies: List[str] = Field(default_factory=list, description="Công nghệ sử dụng")
    highlights: List[str] = Field(default_factory=list, description="Các điểm nổi bật / kết quả / metric")


class ExtractedExperienceItem(BaseModel):
    company: str = Field(..., description="Tên công ty / tổ chức")
    role: str = Field(..., description="Chức danh / Vị trí")
    period: Optional[str] = Field(None, description="Khoảng thời gian làm việc")
    description: Optional[str] = Field(None, description="Mô tả công việc và đóng góp")
    technologies: List[str] = Field(default_factory=list, description="Công nghệ sử dụng")


class ExtractedCertificationItem(BaseModel):
    name: str = Field(..., description="Tên chứng chỉ")
    issuer: Optional[str] = Field(None, description="Đơn vị cấp")
    issue_year: Optional[int] = Field(None, description="Năm cấp")
    credential_url: Optional[str] = Field(None, description="Link chứng chỉ nếu có")


class ExtractedCandidateData(BaseModel):
    candidate: ExtractedCandidateContact = Field(default_factory=ExtractedCandidateContact)
    education: List[ExtractedEducationItem] = Field(default_factory=list)
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    projects: List[ExtractedProjectItem] = Field(default_factory=list)
    experience: List[ExtractedExperienceItem] = Field(default_factory=list)
    certifications: List[ExtractedCertificationItem] = Field(default_factory=list)


# ==============================================================================
# AI & Deterministic Resume Extractor
# ==============================================================================

SYSTEM_CV_EXTRACTOR_PROMPT = """Bạn là một chuyên gia ATS Resume Parser hàng đầu thế giới.
Nhiệm vụ của bạn là đọc nội dung văn bản CV thô (được trích xuất từ file PDF/Word/LaTeX của ứng viên) và bóc tách thành cấu trúc JSON chuẩn xác 100%.

YÊU CẦU QUAN TRỌNG:
1. Không bịa đặt thêm thông tin (Zero Hallucination). Chỉ lấy đúng những gì có trong văn bản CV.
2. Trích xuất chính xác họ tên, số điện thoại, email, link Github, Linkedin, Portfolio.
3. Học vấn (education): Tìm tên trường đại học, bằng cấp, chuyên ngành, GPA, năm tốt nghiệp.
4. Kỹ năng (skills): Phân loại vào các nhóm:
   - "programming": các ngôn ngữ lập trình (Python, JavaScript, Go, C++, etc.)
   - "frameworks": các framework (FastAPI, React, Spring Boot, etc.)
   - "tools_databases": cơ sở dữ liệu và công cụ (PostgreSQL, Docker, Git, Redis, etc.)
   - "soft_skills": kỹ năng mềm
5. Dự án (projects): Tên dự án, vai trò, thời gian, công nghệ, và các gạch đầu dòng mô tả thành tích/kết quả (highlights).
6. Kinh nghiệm làm việc (experience): Công ty, vị trí, thời gian, mô tả công việc.
7. Chứng chỉ (certifications): Tên chứng chỉ, đơn vị cấp, năm cấp.

TRẢ VỀ KẾT QUẢ DƯỚI DẠNG JSON SCHEMA:
{
  "candidate": {
    "name": "string",
    "headline": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "github": "string",
    "linkedin": "string",
    "portfolio": "string",
    "summary": "string"
  },
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field": "string",
      "graduation_year": 2026,
      "gpa": "string",
      "coursework": ["string"]
    }
  ],
  "skills": {
    "programming": ["string"],
    "frameworks": ["string"],
    "tools_databases": ["string"],
    "soft_skills": ["string"]
  },
  "projects": [
    {
      "name": "string",
      "role": "string",
      "period": "string",
      "technologies": ["string"],
      "highlights": ["string"]
    }
  ],
  "experience": [
    {
      "company": "string",
      "role": "string",
      "period": "string",
      "description": "string",
      "technologies": ["string"]
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string",
      "issue_year": 2025,
      "credential_url": "string"
    }
  ]
}
"""


class AIResumeExtractor:
    """
    Bộ trích xuất hồ sơ ứng viên thông minh:
    - Sử dụng Gemini REST API (với fallback cascade các model chính thức)
    - Hỗ trợ Groq API / OpenAI API nếu cấu hình
    - Bộ phân tích heuristic regex tất định dự phòng 100% offline
    """

    @classmethod
    async def extract_profile_from_text(cls, raw_text: str) -> Dict[str, Any]:
        """
        Trích xuất toàn diện hồ sơ ứng viên từ chuỗi văn bản thô.
        """
        if not raw_text or not raw_text.strip():
            return {}

        # 1. Thử dùng AI nếu có API Key
        ai_result = await cls._try_ai_extraction(raw_text)
        if ai_result and (ai_result.get("candidate", {}).get("name") or ai_result.get("skills")):
            logger.info("[AIResumeExtractor] Successfully extracted structured profile via LLM.")
            return cls._format_extracted_data(ai_result, raw_text)

        # 2. Dự phòng: Enhanced Heuristic Regex Extractor
        logger.info("[AIResumeExtractor] LLM not available or returned empty. Using Enhanced Deterministic Extractor.")
        return cls.enhanced_deterministic_extract(raw_text)

    @classmethod
    async def _try_ai_extraction(cls, raw_text: str) -> Optional[Dict[str, Any]]:
        """Gọi Gemini API hoặc Groq API với Structured JSON output."""
        api_key = (
            getattr(settings, "GEMINI_API_KEY", None)
            or getattr(settings, "GOOGLE_API_KEY", None)
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

        if not api_key:
            # Thử Groq API nếu có
            groq_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY")
            if groq_key:
                return await cls._call_groq_json(groq_key, raw_text)
            return None

        # Cắt bớt văn bản nếu quá dài (tối đa 25,000 ký tự cho CV)
        truncated_text = raw_text[:25000]

        # Danh sách model chính thức có hỗ trợ JSON Mode
        models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
        base_url = getattr(settings, "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"Nội dung CV cần bóc tách:\n\n{truncated_text}"}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": SYSTEM_CV_EXTRACTOR_PROMPT}]
            },
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            for model_name in models_to_try:
                url = f"{base_url}/models/{model_name}:generateContent?key={api_key}"
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for p in parts:
                                if "text" in p and p["text"]:
                                    parsed = json.loads(p["text"].strip())
                                    if isinstance(parsed, dict):
                                        return parsed
                    elif resp.status_code == 429:
                        logger.warning(f"Gemini model '{model_name}' hit rate limit (429). Trying next model...")
                        continue
                    else:
                        logger.warning(f"Gemini model '{model_name}' returned status {resp.status_code}.")
                except Exception as e:
                    logger.warning(f"Error calling Gemini model '{model_name}': {e}")
                    continue

        return None

    @classmethod
    async def _call_groq_json(cls, groq_key: str, raw_text: str) -> Optional[Dict[str, Any]]:
        """Fallback sang Groq API với LLaMA 3.3 70B cực nhanh."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_CV_EXTRACTOR_PROMPT},
                {"role": "user", "content": f"Nội dung CV cần bóc tách:\n\n{raw_text[:20000]}"},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
        except Exception as e:
            logger.warning(f"Groq CV extraction failed: {e}")
        return None

    @classmethod
    def _format_extracted_data(cls, data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """Chuẩn hóa dữ liệu JSON thành cấu trúc tương thích 100% với CandidateRepository."""
        candidate = data.get("candidate", {}) or {}
        skills = data.get("skills", {}) or {}
        education = data.get("education", []) or []
        projects = data.get("projects", []) or []
        experience = data.get("experience", []) or []
        certifications = data.get("certifications", []) or []

        # Chuẩn hóa projects để tương thích cấu trúc core + supporting_evidence
        formatted_projects = []
        for p in projects:
            if not isinstance(p, dict):
                continue
            name = p.get("name", "Project")
            role = p.get("role")
            period = p.get("period")
            techs = p.get("technologies", [])
            highlights = p.get("highlights", [])

            core_desc = highlights[0] if highlights else f"Developed {name} using {', '.join(techs[:3])}"
            sup_evidence = []
            for h in highlights[1:]:
                sup_evidence.append({
                    "title": "Achievement",
                    "description": h,
                    "technology_refs": techs,
                })

            formatted_projects.append({
                "name": name,
                "role": role,
                "period": period,
                "technologies": techs,
                "core": {
                    "title": "Core Architecture",
                    "description": core_desc,
                    "technology_refs": techs,
                },
                "supporting_evidence": sup_evidence,
            })

        return {
            "candidate": candidate,
            "skills": skills,
            "education": education,
            "projects": formatted_projects,
            "experience": experience,
            "certifications": certifications,
            "raw_master_resume_md": raw_text,
        }

    @classmethod
    def enhanced_deterministic_extract(cls, raw_text: str) -> Dict[str, Any]:
        """
        Thuật toán bóc tách regex quy tắc nâng cao (không cần AI):
        - Nhận diện các khối phần (Sections): Objective, Education, Skills, Projects, Experience, Certifications.
        - Trích xuất tên, email, sđt, link mạng xã hội.
        - Bóc tách kỹ năng từ Taxonomy và kinh nghiệm theo bullet points.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        result: Dict[str, Any] = {
            "candidate": {},
            "education": [],
            "skills": {},
            "projects": [],
            "experience": [],
            "certifications": [],
            "raw_master_resume_md": raw_text,
        }

        if not lines:
            return result

        # 1. Họ và tên: Quét các dòng đầu tiên không chứa từ khóa định hướng
        for line in lines[:5]:
            words = line.split()
            if 2 <= len(words) <= 5 and not re.search(r"cv|resume|curriculum|page|trang|email|phone|tel|https?://", line, re.I):
                result["candidate"]["name"] = line
                break

        if not result["candidate"].get("name") and lines:
            result["candidate"]["name"] = lines[0]

        # 2. Email, Phone, Social links
        email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", raw_text)
        if email_match:
            result["candidate"]["email"] = email_match.group(1).strip()

        phone_match = re.search(r"(?:\+84|0|\(\+84\))[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}", raw_text)
        if phone_match:
            result["candidate"]["phone"] = phone_match.group(0).strip()

        github_match = re.search(r"(?:https?://)?github\.com/([a-zA-Z0-9_-]+)", raw_text, re.I)
        if github_match:
            result["candidate"]["github"] = f"https://github.com/{github_match.group(1).strip()}"

        linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)", raw_text, re.I)
        if linkedin_match:
            result["candidate"]["linkedin"] = f"https://www.linkedin.com/in/{linkedin_match.group(1).strip()}/"

        # 3. Phân loại kỹ năng chuẩn
        known_prog = ["Python", "JavaScript", "TypeScript", "C++", "C#", "Java", "Go", "Golang", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "Dart", "SQL", "HTML", "CSS"]
        known_fw = ["FastAPI", "React", "NextJS", "Next.js", "Vue", "Angular", "Express", "NestJS", "Django", "Flask", "Spring Boot", "Flutter", "Node.js", "Tailwind CSS"]
        known_tools = ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "Git", "Linux", "AWS", "GCP", "Cloudflare", "CI/CD", "Nginx", "Alembic", "SQLAlchemy"]
        known_soft = ["Teamwork", "Problem Solving", "Communication", "Time Management", "Leadership", "Giao tiếp", "Làm việc nhóm", "Tư duy phản biện"]

        f_prog = [k for k in known_prog if re.search(r"\b" + re.escape(k) + r"\b", raw_text, re.I)]
        f_fw = [k for k in known_fw if re.search(r"\b" + re.escape(k) + r"\b", raw_text, re.I)]
        f_tools = [k for k in known_tools if re.search(r"\b" + re.escape(k) + r"\b", raw_text, re.I)]
        f_soft = [k for k in known_soft if re.search(r"\b" + re.escape(k) + r"\b", raw_text, re.I)]

        if f_prog:
            result["skills"]["programming"] = f_prog
        if f_fw:
            result["skills"]["frameworks"] = f_fw
        if f_tools:
            result["skills"]["tools_databases"] = f_tools
        if f_soft:
            result["skills"]["soft_skills"] = f_soft

        # 4. Trích xuất Học vấn (Education)
        edu_match = re.search(r"(?:Education|Học vấn|Đào tạo)[\s\S]*?(?=(?:Skills|Experience|Projects|Kinh nghiệm|Dự án|Chứng chỉ|\Z))", raw_text, re.I)
        if edu_match:
            edu_block = edu_match.group(0)
            uni_match = re.search(r"((?:Đại học|Trường Đại học|University|College|Academy|Học viện)[^\n,]+)", edu_block, re.I)
            inst = uni_match.group(1).strip() if uni_match else "Đại học"
            major_match = re.search(r"(?:Major|Chuyên ngành|Ngành):\s*([^\n,]+)", edu_block, re.I)
            major = major_match.group(1).strip() if major_match else "Công nghệ thông tin"
            gpa_match = re.search(r"GPA:\s*([0-9\./]+)", edu_block, re.I)
            gpa = gpa_match.group(1).strip() if gpa_match else None

            result["education"].append({
                "institution": inst,
                "degree": "Bachelor",
                "field": major,
                "graduation_year": 2026,
                "gpa": gpa,
                "coursework": [],
            })

        # 5. Trích xuất Dự án (Projects)
        proj_match = re.search(r"(?:Projects|Dự án|Personal Projects)[\s\S]*?(?=(?:Experience|Education|Skills|Certifications|Kinh nghiệm|Học vấn|\Z))", raw_text, re.I)
        if proj_match:
            proj_block = proj_match.group(0)
            # Tìm các mục con theo gạch đầu dòng hoặc tiêu đề dự án
            proj_lines = [l for l in proj_block.splitlines() if l.strip() and not re.match(r"^(Projects|Dự án|Personal Projects):?$", l.strip(), re.I)]
            current_proj = None
            for pl in proj_lines:
                if re.match(r"^[-*•]\s*", pl):
                    if current_proj:
                        bullet = re.sub(r"^[-*•]\s*", "", pl).strip()
                        current_proj["supporting_evidence"].append({
                            "title": "Detail",
                            "description": bullet,
                            "technology_refs": [],
                        })
                elif len(pl.split()) <= 8 and not pl.endswith("."):
                    # Tên dự án mới
                    if current_proj:
                        result["projects"].append(current_proj)
                    current_proj = {
                        "name": pl.strip(),
                        "role": "Developer",
                        "period": "2024 -- 2026",
                        "technologies": [],
                        "core": {
                            "title": "Core Architecture",
                            "description": f"Developed {pl.strip()}",
                            "technology_refs": [],
                        },
                        "supporting_evidence": [],
                    }
            if current_proj:
                result["projects"].append(current_proj)

        return result
