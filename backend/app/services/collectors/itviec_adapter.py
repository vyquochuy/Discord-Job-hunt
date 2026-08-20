import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData

logger = logging.getLogger("itviec_adapter")


class ITViecJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng ngành CNTT Việt Nam từ ITViec.
    """

    BASE_URL = "https://itviec.com"
    SEARCH_URL = "https://itviec.com/it-jobs"

    @property
    def source_name(self) -> str:
        return "itviec"

    async def fetch_jobs(self, limit: int = 20) -> List[RawJobData]:
        results: List[RawJobData] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(self.SEARCH_URL, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"ITViec request returned status {response.status_code}")
                    return results

                soup = BeautifulSoup(response.text, "html.parser")
                
                # Tìm các job card theo selector của ITViec
                job_cards = soup.select(".job-card, .job_content, div[data-search--job-selection-target='jobCard']")
                
                if not job_cards:
                    # Fallback tìm các link job nếu ITViec thay đổi class
                    job_cards = soup.find_all("div", class_=re.compile(r"job.*card|job-item", re.I))

                for card in job_cards[:limit]:
                    title_elem = card.select_one("h3 a, .job-card__title a, a[href*='/it-jobs/']")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    rel_url = title_elem.get("href", "")
                    url = rel_url if rel_url.startswith("http") else f"{self.BASE_URL}{rel_url}"

                    company_elem = card.select_one(
                        "span.text-hover-underline, a.text-rich-grey, .job-card__company-name, .employer-name, a[href*='/companies/']"
                    )
                    company = company_elem.get_text(strip=True) if company_elem else "IT Company"

                    location_elem = card.select_one(
                        "div.text-rich-grey.text-truncate, .job-card__location, .city, .address"
                    )
                    location = location_elem.get_text(strip=True) if location_elem else "Vietnam"

                    # Lấy các skill badges (thẻ a có class itag)
                    skill_badges = card.select("a.itag, .job-card__skills a, .tag-list a")
                    skills = [s.get_text(strip=True) for s in skill_badges if s.get_text(strip=True)]

                    # Lấy thông tin lương nếu hiển thị
                    salary_elem = card.select_one(".job-card__salary, .salary")
                    salary_text = salary_elem.get_text(strip=True) if salary_elem else ""

                    card_payload = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url,
                        "skills": skills,
                        "salary_text": salary_text,
                    }

                    content_hash = self.compute_content_hash(f"{title}|{company}|{location}|{url}")

                    results.append(
                        RawJobData(
                            source=self.source_name,
                            source_url=url,
                            source_job_id=url.split("/")[-1].split("?")[0] if url else None,
                            raw_payload=card_payload,
                            raw_html=str(card),
                            content_hash=content_hash,
                        )
                    )

                logger.info(f"Successfully scraped {len(results)} jobs from ITViec")
        except Exception as e:
            logger.error(f"Error scraping ITViec: {e}")

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}
        
        # Nếu có HTML chi tiết, trích xuất text
        desc = ""
        if raw.raw_html:
            desc = BeautifulSoup(raw.raw_html, "html.parser").get_text(separator=" ").strip()
        else:
            desc = f"{payload.get('title', '')} at {payload.get('company', '')}"

        return JobExtractedData(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company", "").strip(),
            location=payload.get("location", "Ho Chi Minh City"),
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.UNKNOWN,
            description=desc,
            skills_required=payload.get("skills", []),
            skills_nice_to_have=[],
            posted_at=datetime.now(timezone.utc),
        )
