import json
import logging
import re
from typing import List, Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData

logger = logging.getLogger("llm_extractor")


class LLMExtractor:
    """
    Service trích xuất thông tin có cấu trúc (Structured Outputs) từ JD bằng LLM,
    kèm cơ chế Rule-based Fallback khi không có API Key hoặc offline.
    """

    def __init__(self):
        self.api_key = getattr(settings, "OPENAI_API_KEY", None)
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def extract_job_details(
        self, description_text: str, current_data: Optional[JobExtractedData] = None
    ) -> JobExtractedData:
        """
        Trích xuất chuyên sâu các trường: skills, requirements summary, benefits, level, work_mode.
        """
        # Nếu có OpenAI API Key -> gọi LLM Structured JSON
        if self.client and description_text and len(description_text.strip()) > 30:
            try:
                extracted = await self._call_llm_extract(description_text, current_data)
                if extracted:
                    return extracted
            except Exception as e:
                logger.warning(f"LLM Extraction failed, falling back to rule-based: {e}")

        # Fallback Rule-based Extraction
        return self._rule_based_extract(description_text, current_data)

    async def _call_llm_extract(
        self, text: str, current_data: Optional[JobExtractedData]
    ) -> Optional[JobExtractedData]:
        system_prompt = """You are an expert HR Data Parser. Extract structured technical requirements from the Job Description text.
Output MUST be a valid JSON object matching this schema:
{
  "skills_required": ["Python", "PostgreSQL", "FastAPI"],
  "skills_nice_to_have": ["Docker", "Kubernetes"],
  "level": "INTERN | FRESHER | JUNIOR | MID | SENIOR | LEAD | MANAGER | UNKNOWN",
  "work_mode": "ONSITE | HYBRID | REMOTE",
  "requirements_summary": "Brief 2-3 sentence summary of core requirements",
  "benefits_summary": "Brief 2-3 sentence summary of benefits"
}"""

        response = await self.client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:4000]},  # Limit context token
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=600,
        )

        content = response.choices[0].message.content
        if not content:
            return None

        parsed = json.loads(content)

        skills_req = parsed.get("skills_required", [])
        skills_nice = parsed.get("skills_nice_to_have", [])
        req_summary = parsed.get("requirements_summary")
        ben_summary = parsed.get("benefits_summary")

        # Map Enums
        level_str = parsed.get("level", "UNKNOWN").upper()
        level = getattr(JobLevelEnum, level_str, JobLevelEnum.UNKNOWN)

        mode_str = parsed.get("work_mode", "ONSITE").upper()
        work_mode = getattr(WorkModeEnum, mode_str, WorkModeEnum.ONSITE)

        base = current_data or JobExtractedData(
            title="",
            company_name="",
            description=text,
        )

        return JobExtractedData(
            title=base.title,
            company_name=base.company_name,
            location=base.location,
            work_mode=work_mode,
            level=level,
            min_salary=base.min_salary,
            max_salary=base.max_salary,
            salary_currency=base.salary_currency,
            is_salary_negotiable=base.is_salary_negotiable,
            description=base.description,
            requirements_summary=req_summary,
            benefits_summary=ben_summary,
            skills_required=list(set(base.skills_required + skills_req)),
            skills_nice_to_have=list(set(base.skills_nice_to_have + skills_nice)),
            posted_at=base.posted_at,
        )

    def _rule_based_extract(
        self, text: str, current_data: Optional[JobExtractedData]
    ) -> JobExtractedData:
        """Cơ chế trích xuất fallback dựa trên Rule/Regex."""
        base = current_data or JobExtractedData(
            title="",
            company_name="",
            description=text,
        )

        # Trích xuất các từ khóa công nghệ phổ biến từ text nếu chưa có
        tech_keywords = [
            "Python", "FastAPI", "Django", "Flask", "JavaScript", "TypeScript",
            "Node.js", "React", "Vue", "Next.js", "PostgreSQL", "MySQL", "MongoDB",
            "Redis", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Git", "CI/CD",
            "Linux", "Go", "Java", "C++", "C#", "Rust"
        ]

        found_skills = set(base.skills_required)
        text_lower = text.lower()

        for tech in tech_keywords:
            # Word boundary search
            pattern = rf"\b{re.escape(tech.lower())}\b"
            if re.search(pattern, text_lower):
                found_skills.add(tech)

        return JobExtractedData(
            title=base.title,
            company_name=base.company_name,
            location=base.location,
            work_mode=base.work_mode,
            level=base.level,
            min_salary=base.min_salary,
            max_salary=base.max_salary,
            salary_currency=base.salary_currency,
            is_salary_negotiable=base.is_salary_negotiable,
            description=base.description,
            requirements_summary=base.requirements_summary,
            benefits_summary=base.benefits_summary,
            skills_required=list(found_skills),
            skills_nice_to_have=base.skills_nice_to_have,
            posted_at=base.posted_at,
        )


# Singleton Instance
llm_extractor = LLMExtractor()
