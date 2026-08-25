import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData

logger = logging.getLogger("careerlink_adapter")


class CareerLinkJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng ngành CNTT từ CareerLink.vn.
    Hỗ trợ danh mục IT - Phần mềm (Category 19) với duyệt phân trang đa trang.
    """

    BASE_URL = "https://www.careerlink.vn"
    SEARCH_URL = "https://www.careerlink.vn/vieclam/list?category=19"

    @property
    def source_name(self) -> str:
        return "careerlink"

    async def fetch_jobs(self, limit: int = 50) -> List[RawJobData]:
        results: List[RawJobData] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.careerlink.vn/",
        }

        page = 1
        max_pages = min(25, max(1, (limit + 19) // 20))

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                while page <= max_pages and len(results) < limit:
                    target_url = f"{self.SEARCH_URL}&page={page}" if page > 1 else self.SEARCH_URL
                    logger.info(f"CareerLink: Fetching page {page}/{max_pages} from {target_url}...")

                    response = await client.get(target_url, headers=headers)
                    if response.status_code != 200:
                        logger.warning(f"CareerLink page {page} returned status {response.status_code}")
                        break

                    soup = BeautifulSoup(response.text, "html.parser")
                    job_cards = soup.select(".job-item, .list-group-item.job-item, div.media")

                    if not job_cards:
                        logger.info(f"CareerLink: No more job cards found on page {page}.")
                        break

                    for card in job_cards:
                        if len(results) >= limit:
                            break

                        # 1. Title & URL
                        title_elem = card.select_one("a.job-link, a.clickable-outside, h2 a, h3 a")
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        rel_url = title_elem.get("href", "")
                        url = rel_url if rel_url.startswith("http") else f"{self.BASE_URL}{rel_url}"

                        # 2. Company Name
                        company_elem = card.select_one("a.job-company, .job-company, a[href*='/nha-tuyen-dung/']")
                        company = company_elem.get_text(strip=True) if company_elem else "IT Company"

                        # 3. Location
                        location_elem = card.select_one(".job-location, div.list-with-comma, .mobile-disabled-link")
                        location = location_elem.get_text(strip=True) if location_elem else "Vietnam"

                        # 4. Salary
                        salary_elem = card.select_one(".job-salary, span.text-primary")
                        salary_text = salary_elem.get_text(strip=True) if salary_elem else ""

                        # 5. Position/Skills badge
                        position_elem = card.select_one(".job-position")
                        position_tag = position_elem.get_text(strip=True) if position_elem else ""
                        skills = [position_tag] if position_tag else []

                        card_payload = {
                            "title": title,
                            "company": company,
                            "location": location,
                            "url": url,
                            "salary_text": salary_text,
                            "skills": skills,
                        }

                        content_hash = self.compute_content_hash(f"{title}|{company}|{location}|{url}")
                        job_id_match = re.search(r"/(\d+)(?:\?|$)", url)
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

                    page += 1
                    if page <= max_pages and len(results) < limit:
                        await asyncio.sleep(0.35)

                logger.info(f"Successfully scraped {len(results)} IT jobs across {page-1} pages from CareerLink.vn")
        except Exception as e:
            logger.error(f"Error scraping CareerLink: {e}", exc_info=True)

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}
        
        # Bóc tách text description từ HTML card nếu có
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
