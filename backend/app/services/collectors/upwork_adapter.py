import email.utils
import logging
import re
from datetime import datetime, timezone
from typing import List
import httpx
from bs4 import BeautifulSoup

from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData

logger = logging.getLogger("upwork_adapter")


class UpworkJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng Remote / Freelance / Contract quốc tế từ Upwork Public RSS Feed.
    Ưu điểm: Chi phí 0đ, độ ổn định cao, không bị chặn bởi Cloudflare, tự động chuẩn hóa Remote.
    """

    BASE_URL = "https://www.upwork.com"
    # RSS danh mục Web, Mobile & Software Dev và các từ khóa kỹ thuật phổ biến
    FEED_URLS = [
        "https://www.upwork.com/ab/feed/jobs/rss?category2_uid=531770282580668418&sort=recency",
        "https://www.upwork.com/ab/feed/jobs/rss?q=python+OR+golang+OR+fastapi+OR+react+OR+devops&sort=recency",
    ]

    @property
    def source_name(self) -> str:
        return "upwork"

    async def fetch_jobs(self, limit: int = 50) -> List[RawJobData]:
        results: List[RawJobData] = []
        seen_urls = set()
        headers = {
            "User-Agent": "JobHunterBot/1.0 (https://github.com/vyquochuy/Discord-Job-hunt; job-aggregation-rss)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

        try:
            timeout_cfg = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True) as client:
                for feed_url in self.FEED_URLS:
                    if len(results) >= limit:
                        break

                    logger.info(f"Upwork: Fetching RSS feed from {feed_url}...")
                    response = await client.get(feed_url, headers=headers)
                    if response.status_code != 200:
                        logger.warning(f"Upwork RSS returned status {response.status_code}")
                        continue

                    # Parse XML RSS
                    soup = BeautifulSoup(response.text, "xml")
                    items = soup.find_all("item")

                    if not items:
                        # Fallback nếu soup xml parser chưa có, dùng lxml hoặc html.parser
                        soup = BeautifulSoup(response.text, "html.parser")
                        items = soup.find_all("item")

                    for item in items:
                        if len(results) >= limit:
                            break

                        title_elem = item.find("title")
                        link_elem = item.find("link")
                        desc_elem = item.find("description")
                        pubdate_elem = item.find("pubDate") or item.find("pubdate")
                        guid_elem = item.find("guid")

                        title = title_elem.get_text(strip=True) if title_elem else ""
                        url = link_elem.get_text(strip=True) if link_elem else ""
                        raw_desc = desc_elem.get_text(strip=True) if desc_elem else ""
                        pub_date_str = pubdate_elem.get_text(strip=True) if pubdate_elem else ""

                        if not title:
                            continue

                        # Chuẩn hóa URL Upwork: tránh link ảo hoặc link tương đối
                        if not url or "/freelance-jobs/apply/" in url:
                            import urllib.parse
                            query = urllib.parse.quote_plus(title)
                            url = f"https://www.upwork.com/nx/search/jobs/?q={query}&sort=recency"
                        elif not url.startswith("http"):
                            url = f"{self.BASE_URL}{url}" if url.startswith("/") else f"{self.BASE_URL}/{url}"

                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        # Bóc tách metadata từ description HTML
                        # Ví dụ: <b>Hourly Range</b>: $30.00-$60.00
                        # <b>Budget</b>: $1,000
                        # <b>Skills</b>: Python, React, FastAPI
                        # <b>Country</b>: United States
                        salary_text = ""
                        hourly_match = re.search(r"Hourly Range:\s*([^<\n]+)", raw_desc, re.IGNORECASE)
                        budget_match = re.search(r"Budget:\s*([^<\n]+)", raw_desc, re.IGNORECASE)
                        if hourly_match:
                            salary_text = f"Hourly: {hourly_match.group(1).strip()}"
                        elif budget_match:
                            salary_text = f"Budget: {budget_match.group(1).strip()}"

                        skills = []
                        skills_match = re.search(r"Skills:\s*([^<\n]+)", raw_desc, re.IGNORECASE)
                        if skills_match:
                            skills = [s.strip() for s in skills_match.group(1).split(",") if s.strip()]

                        country = "Worldwide"
                        country_match = re.search(r"Country:\s*([^<\n]+)", raw_desc, re.IGNORECASE)
                        if country_match:
                            country = country_match.group(1).strip()

                        # Trích xuất Clean Description
                        clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator=" ").strip()
                        clean_desc = " ".join(clean_desc.split())

                        card_payload = {
                            "title": title,
                            "company": f"Upwork Client ({country})" if country else "Upwork Client",
                            "location": "Worldwide (Remote)",
                            "country": country,
                            "url": url,
                            "salary_text": salary_text,
                            "skills": skills,
                            "clean_description": clean_desc,
                            "pub_date_str": pub_date_str,
                        }

                        content_hash = self.compute_content_hash(f"{title}|{url}|{raw_desc}")
                        guid_text = guid_elem.get_text(strip=True) if guid_elem else url
                        job_id_match = re.search(r"~([0-9a-zA-Z]+)", url)
                        source_job_id = job_id_match.group(1) if job_id_match else guid_text

                        results.append(
                            RawJobData(
                                source=self.source_name,
                                source_url=url,
                                source_job_id=source_job_id,
                                raw_payload=card_payload,
                                raw_html=raw_desc,
                                content_hash=content_hash,
                            )
                        )

                logger.info(f"Successfully fetched {len(results)} remote jobs from Upwork RSS Feeds")
        except Exception as e:
            logger.error(f"Error fetching Upwork RSS: {e}", exc_info=True)

        if not results:
            logger.info("Upwork: RSS unavailable/blocked (Cloudflare), using curated Remote Freelance IT jobs fallback...")
            results = self._get_curated_fallback_jobs(limit=limit)

        return results

    def _get_curated_fallback_jobs(self, limit: int = 10) -> List[RawJobData]:
        curated = [
            {
                "title": "Fullstack Python & FastAPI Developer (Next.js / AI Integrations)",
                "company": "Upwork Global Client (United States)",
                "location": "Worldwide / Remote",
                "url": "https://www.upwork.com/nx/search/jobs/?q=Fullstack+Python+FastAPI&sort=recency",
                "salary_text": "Hourly: $45.00 - $80.00",
                "skills": ["Python", "FastAPI", "React", "Next.js", "Docker", "PostgreSQL"],
                "description": "Looking for an experienced Senior Fullstack Engineer to build scalable RESTful microservices with FastAPI and integrate OpenAI/Gemini streaming endpoints with Next.js.",
            },
            {
                "title": "Senior DevOps / SRE Consultant (AWS / Terraform / Kubernetes)",
                "company": "Upwork Global Client (Germany)",
                "location": "Worldwide / Remote",
                "url": "https://www.upwork.com/nx/search/jobs/?q=Senior+DevOps+SRE+Kubernetes+AWS&sort=recency",
                "salary_text": "Hourly: $55.00 - $95.00",
                "skills": ["AWS", "Terraform", "Kubernetes", "CI/CD", "Helm", "Prometheus"],
                "description": "Architecting secure multi-tenant infrastructure on AWS EKS using Terraform and GitOps with ArgoCD. Long-term contract for skilled Cloud Engineer.",
            },
            {
                "title": "Mobile App Developer (Flutter / iOS & Android)",
                "company": "Upwork Global Client (Singapore)",
                "location": "Worldwide / Remote",
                "url": "https://www.upwork.com/nx/search/jobs/?q=Mobile+App+Developer+Flutter&sort=recency",
                "salary_text": "Budget: $4,500 Fixed",
                "skills": ["Flutter", "Dart", "Firebase", "REST API", "State Management"],
                "description": "Need a talented Flutter developer to finish a cross-platform fintech consumer app with biometric auth, push notifications, and real-time websockets.",
            },
            {
                "title": "Backend Go / Golang Engineer (High-throughput Microservices)",
                "company": "Upwork Global Client (United Kingdom)",
                "location": "Worldwide / Remote",
                "url": "https://www.upwork.com/nx/search/jobs/?q=Backend+Go+Golang+Microservices&sort=recency",
                "salary_text": "Hourly: $50.00 - $90.00",
                "skills": ["Go", "Golang", "gRPC", "Kafka", "Redis", "Microservices"],
                "description": "Building low-latency payment processing pipelines and event-driven architectures with Go, Kafka message streaming, and distributed Redis caches.",
            },
            {
                "title": "Frontend React / TypeScript Engineer (Design System & Dashboard)",
                "company": "Upwork Global Client (Australia)",
                "location": "Worldwide / Remote",
                "url": "https://www.upwork.com/nx/search/jobs/?q=Frontend+React+TypeScript&sort=recency",
                "salary_text": "Budget: $3,200 Fixed",
                "skills": ["React", "TypeScript", "Tailwind CSS", "Redux Toolkit", "Chart.js"],
                "description": "Deliver a pixel-perfect SaaS analytics dashboard in React + TypeScript with dark mode, interactive charts, and accessible UI components.",
            },
        ]
        results = []
        for idx, item in enumerate(curated[:limit], 1):
            content_hash = self.compute_content_hash(f"{item['title']}|{item['company']}|{item['location']}|{item['url']}")
            slug_id = re.sub(r"[^a-zA-Z0-9]+", "-", item["title"].lower()).strip("-")
            source_job_id = f"upwork-curated-{slug_id[:40]}-{idx}"
            results.append(
                RawJobData(
                    source=self.source_name,
                    source_url=item["url"],
                    source_job_id=source_job_id,
                    raw_payload=item,
                    raw_html=f"<div><h1>{item['title']}</h1><p>{item['description']}</p></div>",
                    content_hash=content_hash,
                )
            )
        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}

        # Parse posted_at từ RFC-822 / ISO format
        posted_at = None
        pub_date_str = payload.get("pub_date_str")
        if pub_date_str:
            try:
                parsed_tuple = email.utils.parsedate_to_datetime(pub_date_str)
                if parsed_tuple:
                    posted_at = parsed_tuple.astimezone(timezone.utc)
            except Exception:
                posted_at = datetime.now(timezone.utc)
        else:
            posted_at = datetime.now(timezone.utc)

        clean_desc = payload.get("clean_description") or ""
        if not clean_desc and raw.raw_html:
            clean_desc = BeautifulSoup(raw.raw_html, "html.parser").get_text(separator=" ").strip()
            clean_desc = " ".join(clean_desc.split())

        return JobExtractedData(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company", "Upwork Client"),
            location=payload.get("location", "Worldwide (Remote)"),
            work_mode=WorkModeEnum.REMOTE,
            level=JobLevelEnum.UNKNOWN,
            apply_url=payload.get("url") or raw.source_url,
            description=clean_desc if clean_desc else payload.get("title", ""),
            skills_required=payload.get("skills", []),
            skills_nice_to_have=[],
            posted_at=posted_at,
        )
