import logging
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData

logger = logging.getLogger("remotive_adapter")


class RemotiveJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng Remote quốc tế từ Remotive Public API.
    URL API: https://remotive.com/api/remote-jobs
    """

    API_URL = "https://remotive.com/api/remote-jobs"

    @property
    def source_name(self) -> str:
        return "remotive"

    async def fetch_jobs(self, limit: int = 50) -> List[RawJobData]:
        results: List[RawJobData] = []
        categories = ["software-dev", "devops-sysadmin"]
        headers = {
            "User-Agent": "JobHunterBot/1.0 (https://github.com/vyquochuy/Discord-Job-hunt; job-matching-bot)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                seen_ids = set()
                for cat in categories:
                    if len(results) >= limit:
                        break

                    params = {"category": cat, "limit": limit}
                    response = await client.get(self.API_URL, params=params, headers=headers)
                    if response.status_code != 200:
                        logger.warning(f"Remotive API ({cat}) returned status {response.status_code}")
                        continue

                    data = response.json()
                    raw_jobs_list = data.get("jobs", [])

                    for item in raw_jobs_list:
                        if len(results) >= limit:
                            break

                        job_id = str(item.get("id"))
                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)

                        url = item.get("url") or f"https://remotive.com/job/{job_id}"
                        content_hash = self.compute_content_hash(item)

                        results.append(
                            RawJobData(
                                source=self.source_name,
                                source_url=url,
                                source_job_id=job_id,
                                raw_payload=item,
                                raw_html=None,
                                content_hash=content_hash,
                            )
                        )

                logger.info(f"Successfully fetched {len(results)} IT/DevOps jobs from Remotive API")
        except Exception as e:
            logger.error(f"Error fetching jobs from Remotive: {e}")

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}

        # Làm sạch HTML description
        raw_html_desc = payload.get("description", "")
        clean_desc = BeautifulSoup(raw_html_desc, "html.parser").get_text(separator=" ").strip()
        clean_desc = " ".join(clean_desc.split())

        # Parse posted_at
        posted_at = None
        pub_date_str = payload.get("publication_date")
        if pub_date_str:
            try:
                posted_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            except Exception:
                posted_at = datetime.now(timezone.utc)

        tags = payload.get("tags", [])
        salary_text = payload.get("salary", "")

        return JobExtractedData(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company_name", "").strip(),
            location=payload.get("candidate_required_location") or "Worldwide",
            work_mode=WorkModeEnum.REMOTE,
            level=JobLevelEnum.UNKNOWN,
            description=clean_desc if clean_desc else raw_html_desc,
            skills_required=tags,
            skills_nice_to_have=[],
            posted_at=posted_at,
        )
