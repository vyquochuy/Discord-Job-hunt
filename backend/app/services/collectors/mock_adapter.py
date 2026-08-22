from datetime import datetime, timezone
from typing import List
from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData


class MockJobCollector(BaseJobCollector):
    """
    Adapter giả lập phong phú phục vụ kiểm thử, demo và phát triển offline.
    Mô phỏng 20+ tin tuyển dụng thực tế từ TopCV, ITViec, CareerLink, VietnamWorks và Remotive.
    """

    @property
    def source_name(self) -> str:
        return "mock"

    async def fetch_jobs(self, limit: int = 20) -> List[RawJobData]:
        mock_items = [
            {
                "id": "mock-001",
                "source": "itviec",
                "url": "https://itviec.com/it-jobs/senior-python-backend-engineer-fpt-software-1021",
                "title": "Senior Python Backend Engineer [HCM] (Urgent)",
                "company": "FPT Software",
                "location": "Ho Chi Minh City, Vietnam",
                "description": "We are looking for a Senior Python Developer with deep experience in FastAPI, PostgreSQL, Docker, AWS and Redis to lead our cloud-native team.",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
                "nice_to_have": ["Kubernetes", "Redis"],
                "min_salary": 2000.0,
                "max_salary": 3500.0,
                "currency": "USD",
                "work_mode": "HYBRID",
            },
            {
                "id": "mock-002",
                "source": "topcv",
                "url": "https://www.topcv.vn/viec-lam/junior-frontend-developer-react-typescript-vng-corporation/89214.html",
                "title": "Junior Frontend Developer (React / TypeScript)",
                "company": "VNG Corporation",
                "location": "Ho Chi Minh City",
                "description": "Junior Frontend Engineer with React, TypeScript, Next.js, Redux, Git. Build scalable web applications for millions of users.",
                "skills": ["React", "TypeScript", "Next.js", "Git"],
                "nice_to_have": ["TailwindCSS", "Redux"],
                "min_salary": 800.0,
                "max_salary": 1500.0,
                "currency": "USD",
                "work_mode": "ONSITE",
            },
            {
                "id": "mock-003",
                "source": "remotive",
                "url": "https://remotive.com/remote-jobs/devops/devops-sre-engineer-remote-98124",
                "title": "DevOps / SRE Engineer - Remote",
                "company": "Global Cloud Services",
                "location": "Worldwide (100% Remote)",
                "description": "Remote DevOps specialist experienced in CI/CD, Kubernetes, Terraform, Linux and AWS. Manage infrastructure across multi-region clusters.",
                "skills": ["Kubernetes", "Docker", "AWS", "CI/CD", "Linux"],
                "nice_to_have": ["Terraform", "Python"],
                "min_salary": 3000.0,
                "max_salary": 5000.0,
                "currency": "USD",
                "work_mode": "REMOTE",
            },
            {
                "id": "mock-004",
                "source": "topcv",
                "url": "https://www.topcv.vn/viec-lam/thuc-tap-sinh-devops-system-intern-momo-service/65412.html",
                "title": "Thực Tập Sinh DevOps / System Intern (Có Lương & Đào Tạo)",
                "company": "MoMo",
                "location": "Ho Chi Minh City",
                "description": "Tuyển dụng System / DevOps Intern tham gia quản trị hệ thống Linux, Docker, viết automation script bằng Python/Bash và xây dựng pipeline CI/CD cơ bản.",
                "skills": ["Linux", "Docker", "Python", "Git"],
                "nice_to_have": ["Kubernetes", "CI/CD", "PostgreSQL"],
                "min_salary": 6000000.0,
                "max_salary": 10000000.0,
                "currency": "VND",
                "work_mode": "HYBRID",
            },
            {
                "id": "mock-005",
                "source": "itviec",
                "url": "https://itviec.com/it-jobs/python-backend-developer-fastapi-tiki-vn-4512",
                "title": "Backend Developer (Python / FastAPI / PostgreSQL)",
                "company": "Tiki",
                "location": "Thu Duc, Ho Chi Minh City",
                "description": "Phát triển hệ thống microservices backend với Python FastAPI, tối ưu hóa truy vấn PostgreSQL, caching Redis và đóng gói Docker containers.",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
                "nice_to_have": ["RabbitMQ", "Kafka", "AWS"],
                "min_salary": 15000000.0,
                "max_salary": 30000000.0,
                "currency": "VND",
                "work_mode": "HYBRID",
            },
            {
                "id": "mock-006",
                "source": "careerlink",
                "url": "https://www.careerlink.vn/tim-viec-lam/golang-backend-engineer-vietcombank-digital/33129",
                "title": "Golang Backend Engineer (High Concurrency)",
                "company": "Vietcombank Digital",
                "location": "Hanoi, Vietnam",
                "description": "Xây dựng các dịch vụ thanh toán trực tuyến hiệu năng cao xử lý hàng triệu transactions mỗi ngày với Golang, gRPC, PostgreSQL và Kafka.",
                "skills": ["Go", "gRPC", "PostgreSQL", "Kafka", "Docker"],
                "nice_to_have": ["Kubernetes", "Redis"],
                "min_salary": 25000000.0,
                "max_salary": 45000000.0,
                "currency": "VND",
                "work_mode": "ONSITE",
            },
            {
                "id": "mock-007",
                "source": "remotive",
                "url": "https://remotive.com/remote-jobs/software-dev/fullstack-python-react-engineer-11029",
                "title": "Fullstack Software Engineer (Python & React) - 100% Remote",
                "company": "Automattic Partners",
                "location": "Remote - APAC / Vietnam",
                "description": "Looking for a versatile Fullstack Engineer to build modern web products with Python (FastAPI/Django), TypeScript, React and PostgreSQL.",
                "skills": ["Python", "React", "TypeScript", "FastAPI", "PostgreSQL"],
                "nice_to_have": ["Docker", "TailwindCSS", "Next.js"],
                "min_salary": 2500.0,
                "max_salary": 4200.0,
                "currency": "USD",
                "work_mode": "REMOTE",
            },
            {
                "id": "mock-008",
                "source": "itviec",
                "url": "https://itviec.com/it-jobs/cloud-infrastructure-engineer-aws-zalo-pay-7761",
                "title": "Cloud Infrastructure Engineer (AWS / Terraform)",
                "company": "ZaloPay",
                "location": "District 7, Ho Chi Minh City",
                "description": "Quản lý hạ tầng điện toán đám mây AWS, triển khai Infrastructure as Code với Terraform, giám sát hệ thống với Prometheus/Grafana.",
                "skills": ["AWS", "Terraform", "Docker", "Linux", "CI/CD"],
                "nice_to_have": ["Kubernetes", "Python", "Ansible"],
                "min_salary": 22000000.0,
                "max_salary": 40000000.0,
                "currency": "VND",
                "work_mode": "HYBRID",
            },
            {
                "id": "mock-009",
                "source": "topcv",
                "url": "https://www.topcv.vn/viec-lam/lap-trinh-vien-python-ai-nlp-engineer-viettel-ai/55120.html",
                "title": "Kỹ Sư AI / NLP Engineer (Python, LLM, PyTorch)",
                "company": "Viettel AI",
                "location": "Hanoi",
                "description": "Nghiên cứu và tích hợp mô hình ngôn ngữ lớn (LLM), xây dựng RAG pipelines, fine-tune models và tối ưu hóa inference API.",
                "skills": ["Python", "PyTorch", "NLP", "FastAPI", "Docker"],
                "nice_to_have": ["LangChain", "Vector DB", "PostgreSQL"],
                "min_salary": 30000000.0,
                "max_salary": 55000000.0,
                "currency": "VND",
                "work_mode": "ONSITE",
            },
            {
                "id": "mock-010",
                "source": "itviec",
                "url": "https://itviec.com/it-jobs/fresher-backend-developer-python-shopee-vietnam-8819",
                "title": "Fresher Backend Developer (Python / Java / Node.js)",
                "company": "Shopee Vietnam",
                "location": "Ho Chi Minh City",
                "description": "Chương trình tuyển dụng Fresh Graduate tài năng tham gia phát triển hệ thống sàn thương mại điện tử quy mô lớn tại Đông Nam Á.",
                "skills": ["Python", "PostgreSQL", "Git", "OOP", "Data Structures"],
                "nice_to_have": ["Docker", "Linux", "Redis"],
                "min_salary": 12000000.0,
                "max_salary": 20000000.0,
                "currency": "VND",
                "work_mode": "ONSITE",
            },
            {
                "id": "mock-011",
                "source": "topcv",
                "url": "https://www.topcv.vn/viec-lam/senior-devops-lead-sre-vinid-vsmart/99120.html",
                "title": "Lead DevOps / Platform Architect",
                "company": "VinGroup Technology",
                "location": "Hanoi & Ho Chi Minh City",
                "description": "Dẫn dắt đội ngũ kỹ sư Platform và SRE, thiết kế kiến trúc Kubernetes đa cụm, tối ưu chi phí hạ tầng Cloud.",
                "skills": ["Kubernetes", "AWS", "Terraform", "CI/CD", "Linux"],
                "nice_to_have": ["Go", "Python", "Security"],
                "min_salary": 50000000.0,
                "max_salary": 80000000.0,
                "currency": "VND",
                "work_mode": "HYBRID",
            },
            {
                "id": "mock-012",
                "source": "remotive",
                "url": "https://remotive.com/remote-jobs/qa/senior-qa-automation-engineer-remote-4412",
                "title": "QA Automation Engineer (Python / Playwright) - Remote",
                "company": "Global Test Solutions",
                "location": "Remote",
                "description": "Develop and maintain automated end-to-end testing frameworks using Python, Playwright, Pytest and GitHub Actions CI/CD pipelines.",
                "skills": ["Python", "Playwright", "CI/CD", "Git", "Linux"],
                "nice_to_have": ["Docker", "FastAPI"],
                "min_salary": 2000.0,
                "max_salary": 3200.0,
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
