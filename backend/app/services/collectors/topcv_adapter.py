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
from app.services.extraction.detail_fetcher import (
    clean_html_to_text,
    parse_posted_datetime,
)

logger = logging.getLogger("topcv_adapter")


class TopCVJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng từ TopCV.vn.
    Hỗ trợ bóc tách danh sách tin IT đa trang và xử lý bot detection / WAF fallback.
    """

    BASE_URL = "https://www.topcv.vn"
    SEARCH_URL = "https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026"

    @property
    def source_name(self) -> str:
        return "topcv"

    async def fetch_jobs(self, limit: int = 50) -> List[RawJobData]:
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

        page = 1
        unlimited = limit <= 0
        max_pages = 80 if unlimited else max(1, (limit + 19) // 20)
        consecutive_expired = 0
        MAX_CONSECUTIVE_EXPIRED = 15

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                while page <= max_pages and (unlimited or len(results) < limit):
                    target_url = f"{self.SEARCH_URL}?sort=new&page={page}" if page > 1 else f"{self.SEARCH_URL}?sort=new"
                    logger.info(f"TopCV: Fetching page {page}/{max_pages} from {target_url}...")
                    
                    response = await client.get(target_url, headers=headers)
                    if response.status_code == 403:
                        logger.warning(
                            "TopCV.vn trả về HTTP 403 (Cloudflare Bot Management / WAF). "
                            "Tự động bỏ qua cào tự động cho nguồn này. Khuyến nghị người dùng sử dụng tính năng "
                            "'Nhập JD thủ công' (POST /api/v1/jobs/ingest-manual) để nhập tin TopCV."
                        )
                        break
                    elif response.status_code != 200:
                        logger.warning(
                            f"TopCV.vn page {page} returned status {response.status_code}"
                        )
                        break

                    soup = BeautifulSoup(response.text, "html.parser")
                    job_cards = soup.select(
                        ".job-item-search-result, .job-item-2, .job-item, .job-ta, div[data-job-id]"
                    )

                    if not job_cards:
                        logger.info(f"TopCV: No more job cards found on page {page}.")
                        break

                    page_jobs_count = 0
                    for card in job_cards:
                        if not unlimited and len(results) >= limit:
                            break

                        # 1. Tiêu đề và link
                        title_elem = card.select_one("h3 a, .title a, a[href*='/viec-lam/'], span.bold a, a.job-title")
                        if not title_elem:
                            continue

                        title = (
                            title_elem.get("title")
                            or title_elem.get("data-original-title")
                            or title_elem.get_text(strip=True)
                            or (title_elem.select_one("span") and title_elem.select_one("span").get_text(strip=True))
                            or ""
                        )
                        if not title:
                            span_title = card.select_one("span.bold, span.title-name, .title")
                            title = span_title.get_text(strip=True) if span_title else ""
                        if not title:
                            continue

                        rel_url = title_elem.get("href", "")
                        url = rel_url if rel_url.startswith("http") else f"{self.BASE_URL}{rel_url}"

                        # 2. Tên công ty
                        company_elem = card.select_one("a.company, .company-name, a[href*='/cong-ty/'], .name, span.company-name")
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

                        # 6. Hạn nộp / trạng thái hết hạn từ card
                        deadline_elem = card.select_one(".time, .deadline, .job-deadline, span.time")
                        deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ""
                        card_text_lower = card.get_text(" ", strip=True).lower()
                        is_card_expired = any(
                            m in card_text_lower for m in ("hết hạn", "đã đóng", "closed", "expired")
                        )
                        if is_card_expired:
                            consecutive_expired += 1
                        else:
                            consecutive_expired = 0

                        if consecutive_expired >= MAX_CONSECUTIVE_EXPIRED:
                            logger.info(f"TopCV: Encountered {consecutive_expired} consecutive expired jobs. Stopping early at page {page}.")
                            break

                        card_payload = {
                            "title": title,
                            "company": company,
                            "location": location,
                            "url": url,
                            "salary_text": salary_text,
                            "skills": skills,
                            "deadline_text": deadline_text,
                            "is_expired": is_card_expired,
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
                        page_jobs_count += 1

                    if consecutive_expired >= MAX_CONSECUTIVE_EXPIRED:
                        break

                    page += 1
                    if page <= max_pages and (unlimited or len(results) < limit):
                        await asyncio.sleep(0.35)

                logger.info(f"Successfully scraped {len(results)} IT jobs across {page-1} pages from TopCV.vn")
        except Exception as e:
            logger.error(f"Error scraping TopCV: {e}", exc_info=True)

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}

        # Ưu tiên JD đầy đủ từ Detail Enrichment (payload["description"]),
        # fallback về HTML card listing nếu chưa có.
        desc = clean_html_to_text(str(payload.get("description") or ""))
        if len(desc) < 80 and raw.raw_html:
            desc = " ".join(
                BeautifulSoup(raw.raw_html, "html.parser").get_text(separator="\n", strip=True).split()
            )
        if not desc:
            desc = f"{payload.get('title', '')} tại {payload.get('company', '')}"

        posted_at = (
            parse_posted_datetime(payload.get("posted_iso"))
            or parse_posted_datetime(payload.get("posted_at_text"))
            or datetime.now(timezone.utc)
        )

        expires_at = (
            parse_posted_datetime(payload.get("expires_iso"))
            or parse_posted_datetime(payload.get("deadline_text"))
        )

        return JobExtractedData(
            title=payload.get("title", "").strip(),
            company_name=payload.get("company", "").strip(),
            location=payload.get("location", "Vietnam"),
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.UNKNOWN,
            description=desc,
            skills_required=payload.get("skills", []),
            skills_nice_to_have=[],
            posted_at=posted_at,
            expires_at=expires_at,
        )
