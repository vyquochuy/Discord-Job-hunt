import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List
import httpx
from bs4 import BeautifulSoup

from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData

logger = logging.getLogger("vietnamworks_adapter")


class VietnamWorksJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng CNTT từ VietnamWorks.com (Navigos Group).
    Hỗ trợ bóc tách danh mục IT - Phần mềm, trích xuất dải lương, công ty và kỹ năng.
    """

    BASE_URL = "https://www.vietnamworks.com"
    SEARCH_URL = "https://www.vietnamworks.com/it-phan-mem-kv"

    API_SEARCH_URL = "https://ms.vietnamworks.com/job-search/v1.0/search"

    @property
    def source_name(self) -> str:
        return "vietnamworks"

    async def fetch_jobs(self, limit: int = 50) -> List[RawJobData]:
        results: List[RawJobData] = []
        api_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }

        # 1. Primary: Query VietnamWorks public Search API
        try:
            timeout_cfg = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True) as client:
                page = 0
                hits_per_page = min(limit, 25)
                while len(results) < limit:
                    payload = {
                        "userId": 0,
                        "query": "IT Software",
                        "filter": [],
                        "ranges": [],
                        "order": [],
                        "hitsPerPage": hits_per_page,
                        "page": page,
                    }
                    response = await client.post(self.API_SEARCH_URL, headers=api_headers, json=payload)
                    if response.status_code != 200:
                        logger.warning(f"VietnamWorks API returned status {response.status_code}")
                        break

                    data = response.json()
                    job_items = data.get("data", [])
                    if not job_items:
                        break

                    for item in job_items:
                        if len(results) >= limit:
                            break

                        title = item.get("jobTitle") or ""
                        if not title:
                            continue

                        url = item.get("jobUrl") or ""
                        if not url.startswith("http"):
                            url = f"{self.BASE_URL}{url}"

                        company = item.get("companyName") or "VietnamWorks Employer"

                        # Extract locations
                        locs = item.get("workingLocations") or []
                        loc_names = [l.get("cityNameVI") or l.get("cityName") for l in locs if isinstance(l, dict)]
                        location = ", ".join(loc_names) if loc_names else "Vietnam"

                        # Extract salary
                        sal_min = item.get("salaryMin")
                        sal_max = item.get("salaryMax")
                        if sal_min and sal_max:
                            salary_text = f"{sal_min:,} - {sal_max:,} {item.get('salaryCurrency', 'VND')}"
                        else:
                            salary_text = item.get("prettySalary") or ""

                        # Extract skills
                        raw_skills = item.get("skills") or []
                        skills = [s.get("skillName") for s in raw_skills if isinstance(s, dict) and s.get("skillName")]

                        source_job_id = str(item.get("jobId") or "")
                        card_payload = {
                            "title": title,
                            "company": company,
                            "location": location,
                            "url": url,
                            "salary_text": salary_text,
                            "skills": skills,
                            "description": item.get("jobDescription") or "",
                        }

                        content_hash = self.compute_content_hash(f"{title}|{company}|{location}|{url}")
                        results.append(
                            RawJobData(
                                source=self.source_name,
                                source_url=url,
                                source_job_id=source_job_id or None,
                                raw_payload=card_payload,
                                raw_html=item.get("jobDescription") or "",
                                content_hash=content_hash,
                            )
                        )

                    page += 1
                    if len(results) >= limit or len(job_items) < hits_per_page:
                        break
                    await asyncio.sleep(0.3)

            if results:
                logger.info(f"Successfully fetched {len(results)} IT jobs via VietnamWorks Search API")
                return results

        except Exception as e:
            logger.warning(f"VietnamWorks API query failed, trying HTML fallback: {e}")

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}

        desc = ""
        if raw.raw_html:
            desc = BeautifulSoup(raw.raw_html, "html.parser").get_text(separator=" ").strip()
            desc = " ".join(desc.split())
        else:
            desc = f"{payload.get('title', '')} tại {payload.get('company', '')}"

        title_lower = (payload.get("title") or "").lower()
        work_mode = WorkModeEnum.ONSITE
        if "remote" in title_lower:
            work_mode = WorkModeEnum.REMOTE
        elif "hybrid" in title_lower:
            work_mode = WorkModeEnum.HYBRID

        return JobExtractedData(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company", "").strip(),
            location=payload.get("location", "Vietnam"),
            work_mode=work_mode,
            level=JobLevelEnum.UNKNOWN,
            description=desc,
            skills_required=payload.get("skills", []),
            skills_nice_to_have=[],
            posted_at=datetime.now(timezone.utc),
        )
