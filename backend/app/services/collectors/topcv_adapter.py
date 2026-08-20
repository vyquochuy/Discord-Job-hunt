import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData

logger = logging.getLogger("topcv_adapter")


class TopCVJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng từ TopCV.vn.
    Hỗ trợ bóc tách danh sách tin IT và xử lý bot detection / WAF fallback.
    """

    BASE_URL = "https://www.topcv.vn"
    SEARCH_URL = "https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026"

    @property
    def source_name(self) -> str:
        return "topcv"

    async def fetch_jobs(self, limit: int = 20) -> List[RawJobData]:
        results: List[RawJobData] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(self.SEARCH_URL, headers=headers)
                if response.status_code != 200:
                    logger.warning(
                        f"TopCV.vn returned status {response.status_code} "
                        f"(Notice: TopCV may require browser automation/proxy if Cloudflare WAF is active)"
                    )
                    return results

                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.select(
                    ".job-item-search-result, .job-item-2, .job-item, .job-ta, div[data-job-id]"
                )

                for card in job_cards[:limit]:
                    # 1. Tiêu đề và link
                    title_elem = card.select_one("h3 a, .title a, a[href*='/viec-lam/']")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    rel_url = title_elem.get("href", "")
                    url = rel_url if rel_url.startswith("http") else f"{self.BASE_URL}{rel_url}"

                    # 2. Tên công ty
                    company_elem = card.select_one("a.company, .company-name, a[href*='/cong-ty/'], .name")
                    company = company_elem.get_text(strip=True) if company_elem else "IT Company"

                    # 3. Địa điểm
                    location_elem = card.select_one(".address, .city, .location")
                    location = location_elem.get_text(strip=True) if location_elem else "Vietnam"

                    # 4. Mức lương
                    salary_elem = card.select_one(".salary, .badge-salary")
                    salary_text = salary_elem.get_text(strip=True) if salary_elem else ""

                    # 5. Kỹ năng / Tags
                    skill_badges = card.select(".tag, .badge, .job-tag")
                    skills = [s.get_text(strip=True) for s in skill_badges if s.get_text(strip=True)]

                    card_payload = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url,
                        "salary_text": salary_text,
                        "skills": skills,
                    }

                    content_hash = self.compute_content_hash(f"{title}|{company}|{location}|{url}")
                    job_id_match = re.search(r"/(\d+)\.html", url)
                    source_job_id = job_id_match.group(1) if job_id_match else None

                    results.append(
                        RawJobData(
                            source=self.source_name,
                            source_url=url,
                            source_job_id=source_job_id,
                            raw_payload=card_payload,
                            raw_html=str(card),
                            content_hash=content_hash,
                        )
                    )

                logger.info(f"Successfully scraped {len(results)} jobs from TopCV.vn")
        except Exception as e:
            logger.error(f"Error scraping TopCV: {e}", exc_info=True)

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}
        
        desc = ""
        if raw.raw_html:
            desc = BeautifulSoup(raw.raw_html, "html.parser").get_text(separator=" ").strip()
            desc = " ".join(desc.split())
        else:
            desc = f"{payload.get('title', '')} tại {payload.get('company', '')}"

        return JobExtractedData(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company", "").strip(),
            location=payload.get("location", "Vietnam"),
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.UNKNOWN,
            description=desc,
            skills_required=payload.get("skills", []),
            skills_nice_to_have=[],
            posted_at=datetime.now(timezone.utc),
        )
