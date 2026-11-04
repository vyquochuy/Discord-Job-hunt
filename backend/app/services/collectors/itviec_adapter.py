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
from app.services.extraction.detail_fetcher import parse_posted_datetime

logger = logging.getLogger("itviec_adapter")


class ITViecJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng ngành CNTT Việt Nam từ ITViec.
    Hỗ trợ duyệt phân trang đa trang (Pagination Loop).
    """

    BASE_URL = "https://itviec.com"
    SEARCH_URL = "https://itviec.com/it-jobs"

    @property
    def source_name(self) -> str:
        return "itviec"

    async def fetch_jobs(self, limit: int = 50) -> List[RawJobData]:
        results: List[RawJobData] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }

        page = 1
        # limit <= 0 có nghĩa là quét toàn bộ job chưa hết hạn
        unlimited = limit <= 0
        max_pages = 80 if unlimited else max(1, (limit + 19) // 20)
        consecutive_expired = 0
        MAX_CONSECUTIVE_EXPIRED = 15

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                while page <= max_pages and (unlimited or len(results) < limit):
                    target_url = f"{self.SEARCH_URL}?page={page}" if page > 1 else self.SEARCH_URL
                    logger.info(f"ITViec: Fetching page {page}/{max_pages} from {target_url}...")

                    response = await client.get(target_url, headers=headers)
                    if response.status_code != 200:
                        logger.warning(f"ITViec page {page} request returned status {response.status_code}")
                        break

                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Tìm các job card theo selector của ITViec
                    job_cards = soup.select(".job-card, .job_content, div[data-search--job-selection-target='jobCard']")
                    
                    if not job_cards:
                        # Fallback tìm các link job nếu ITViec thay đổi class
                        job_cards = soup.find_all("div", class_=re.compile(r"job.*card|job-item", re.I))

                    if not job_cards:
                        logger.info(f"ITViec: No more job cards found on page {page}.")
                        break

                    page_jobs_count = 0
                    for card in job_cards:
                        if not unlimited and len(results) >= limit:
                            break

                        title_elem = card.select_one("h3 a, .job-card__title a, a[href*='/it-jobs/']")
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        rel_url = title_elem.get("href", "")
                        url = rel_url if rel_url.startswith("http") else f"{self.BASE_URL}{rel_url}"

                        # Kiểm tra cờ hết hạn hiển thị trên card (nếu có)
                        card_text_lower = card.get_text(" ", strip=True).lower()
                        is_card_expired = any(
                            m in card_text_lower for m in ("hết hạn", "đã đóng", "closed", "expired")
                        )
                        if is_card_expired:
                            consecutive_expired += 1
                        else:
                            consecutive_expired = 0

                        # Dừng sớm nếu gặp liên tiếp nhiều job hết hạn theo thứ tự thời gian
                        if consecutive_expired >= MAX_CONSECUTIVE_EXPIRED:
                            logger.info(f"ITViec: Encountered {consecutive_expired} consecutive expired jobs. Stopping early at page {page}.")
                            break

                        company_elem = card.select_one(
                            "div.imy-3, a[href*='/companies/'], span.text-hover-underline, .job-card__company-name, .employer-name"
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

                        # Best-effort: ngày đăng tương đối trên card ("3 days ago" / "5 ngày trước")
                        posted_elem = card.select_one("time, .footer time, span.small-text, .posted-date")
                        posted_text = None
                        if posted_elem:
                            posted_text = (
                                posted_elem.get("datetime")
                                or posted_elem.get("title")
                                or " ".join(posted_elem.get_text(" ", strip=True).split())
                            )

                        card_payload = {
                            "title": title,
                            "company": company,
                            "location": location,
                            "url": url,
                            "skills": skills,
                            "salary_text": salary_text,
                            "posted_at_text": posted_text,
                            "is_expired": is_card_expired,
                        }

                        content_hash = self.compute_content_hash(f"{title}|{company}|{location}|{url}" + (f"|{posted_text}" if posted_text else ""))

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
                        page_jobs_count += 1

                    if consecutive_expired >= MAX_CONSECUTIVE_EXPIRED:
                        break

                    page += 1
                    if page <= max_pages and (unlimited or len(results) < limit):
                        await asyncio.sleep(0.35)

                logger.info(f"Successfully scraped {len(results)} IT jobs across {page-1} pages from ITViec")
        except Exception as e:
            logger.error(f"Error scraping ITViec: {e}")

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}

        # Bóc tách description: ưu tiên JD đầy đủ từ Detail Enrichment
        # (payload["description"]), fallback về HTML card listing nếu chưa có.
        desc = str(payload.get("description") or "").strip()
        if not desc and raw.raw_html:
            desc = BeautifulSoup(raw.raw_html, "html.parser").get_text(separator="\n", strip=True)
        if not desc:
            desc = f"{payload.get('title', '')} at {payload.get('company', '')}"

        # Posted date: ưu tiên JSON-LD/Detail ISO, fallback relative text của card
        posted_at = (
            parse_posted_datetime(payload.get("posted_iso"))
            or parse_posted_datetime(payload.get("posted_at_text"))
            or datetime.now(timezone.utc)
        )

        # Expiry date từ detail enrichment hoặc card
        expires_at = parse_posted_datetime(payload.get("expires_iso"))

        return JobExtractedData(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company", "").strip(),
            location=payload.get("location", "Ho Chi Minh City"),
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.UNKNOWN,
            description=desc,
            skills_required=payload.get("skills", []),
            skills_nice_to_have=[],
            posted_at=posted_at,
            expires_at=expires_at,
        )
