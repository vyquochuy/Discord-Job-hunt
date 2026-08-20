from datetime import datetime, timezone
from typing import List
from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData


class MockJobCollector(BaseJobCollector):
    """
    Adapter giả lập phục vụ cho Unit Testing, CI/CD và Offline Verification.
    Không gọi bất kỳ request mạng nào ra ngoài.
    """

    @property
    def source_name(self) -> str:
        return "mock"

    async def fetch_jobs(self, limit: int = 20) -> List[RawJobData]:
        mock_items = [
            {
                "id": "mock-001",
                "url": "https://example.com/jobs/senior-python-engineer",
                "title": "Senior Python Backend Engineer [HCM] (Urgent)",
                "company": "FPT Software Co., Ltd",
                "location": "Ho Chi Minh City, Vietnam",
                "description": "We are looking for a Senior Python Developer with deep experience in FastAPI, PostgreSQL, Docker, AWS and Redis.",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
                "nice_to_have": ["Kubernetes", "Redis"],
                "min_salary": 2000.0,
                "max_salary": 3500.0,
                "currency": "USD",
                "work_mode": "HYBRID",
            },
            {
                "id": "mock-002",
                "url": "https://example.com/jobs/junior-react-developer",
                "title": "Junior Frontend Developer (React / TypeScript)",
                "company": "VNG Corporation JSC",
                "location": "Ho Chi Minh City",
                "description": "Junior Frontend Engineer with React, TypeScript, Next.js, Redux, Git. Good communication skills.",
                "skills": ["React", "TypeScript", "Next.js", "Git"],
                "nice_to_have": ["TailwindCSS"],
                "min_salary": 800.0,
                "max_salary": 1500.0,
                "currency": "USD",
                "work_mode": "ONSITE",
            },
            {
                "id": "mock-003",
                "url": "https://example.com/jobs/remote-devops-engineer",
                "title": "DevOps / SRE Engineer - Remote",
                "company": "Global Cloud Services",
                "location": "Remote",
                "description": "Remote DevOps specialist experienced in CI/CD, Kubernetes, Terraform, Linux and AWS.",
                "skills": ["Kubernetes", "Docker", "AWS", "CI/CD", "Linux"],
                "nice_to_have": ["Terraform", "Python"],
                "min_salary": 3000.0,
                "max_salary": 5000.0,
                "currency": "USD",
                "work_mode": "REMOTE",
            },
        ]

        results: List[RawJobData] = []
        for item in mock_items[:limit]:
            content_str = f"{item['title']}|{item['company']}|{item['description']}"
            results.append(
                RawJobData(
                    source=self.source_name,
                    source_url=item["url"],
                    source_job_id=item["id"],
                    raw_payload=item,
                    raw_html=None,
                    content_hash=self.compute_content_hash(content_str),
                )
            )
        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}
        work_mode_str = payload.get("work_mode", "ONSITE")
        work_mode = (
            WorkModeEnum.REMOTE if work_mode_str == "REMOTE"
            else WorkModeEnum.HYBRID if work_mode_str == "HYBRID"
            else WorkModeEnum.ONSITE
        )

        return JobExtractedData(
            title=payload.get("title", ""),
            company_name=payload.get("company", ""),
            location=payload.get("location", ""),
            work_mode=work_mode,
            level=JobLevelEnum.UNKNOWN,
            min_salary=payload.get("min_salary"),
            max_salary=payload.get("max_salary"),
            salary_currency=payload.get("currency"),
            description=payload.get("description", ""),
            skills_required=payload.get("skills", []),
            skills_nice_to_have=payload.get("nice_to_have", []),
            posted_at=datetime.now(timezone.utc),
        )
