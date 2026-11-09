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

logger = logging.getLogger("itnavi_adapter")


class ITNaviJobCollector(BaseJobCollector):
    """
    Adapter thu thập tin tuyển dụng CNTT từ ITnavi.com.vn.
    Hỗ trợ bóc tách danh sách việc làm IT, công nghệ yêu cầu, mức lương và kinh nghiệm.
    """

    BASE_URL = "https://itnavi.com.vn"
    SEARCH_URL = "https://itnavi.com.vn/job"

    @property
    def source_name(self) -> str:
        return "itnavi"

    async def fetch_jobs(self, limit: int = 50) -> List[RawJobData]:
        results: List[RawJobData] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://itnavi.com.vn/",
        }

        page = 1
        unlimited = limit <= 0
        # Mỗi trang ITNavi có 10 tin; limit=50 cần 5 trang. Khi full scan, cap tối đa 50 trang (~490 tin).
        max_pages = 50 if unlimited else min(25, max(1, (limit + 9) // 10))
        seen = set()
        seen_ids = set()

        try:
            timeout_cfg = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True) as client:
                while page <= max_pages and (unlimited or len(results) < limit):
                    target_url = f"{self.SEARCH_URL}?page={page}" if page > 1 else self.SEARCH_URL
                    logger.info(f"ITNavi: Fetching page {page}/{max_pages} from {target_url}...")

                    try:
                        response = await client.get(target_url, headers=headers)
                    except httpx.TimeoutException:
                        logger.warning(f"ITNavi page {page} timed out, retrying once...")
                        try:
                            response = await client.get(target_url, headers=headers)
                        except httpx.TimeoutException:
                            logger.warning(f"ITNavi page {page} timed out twice, stopping pagination.")
                            break
                    if response.status_code != 200:
                        logger.warning(f"ITNavi page {page} returned status {response.status_code}")
                        break

                    soup = BeautifulSoup(response.text, "html.parser")
                    job_cards = soup.select(
                        ".jsl-item, .jsl_item, .job-item, .item-job, .card-job, div[class*='job-item'], div[class*='job_item'], .job-card"
                    )

                    if not job_cards:
                        job_cards = soup.find_all("div", class_=re.compile(r"jsl.*item|job.*item|job.*card", re.I))

                    if not job_cards:
                        logger.info(f"ITNavi: No job cards found on page {page}.")
                        break

                    async def _parse_card(card):
                        title_elem = card.select_one(
                            ".jsl-item__name, h2, h3, a[class*='title'], a[href*='/viec-lam-'], a[href*='/job/']"
                        )
                        if not title_elem:
                            return None

                        title = title_elem.get_text(strip=True)
                        if not title:
                            return None

                        job_id = card.get("data-id") or card.get("id") or ""
                        if job_id:
                            if job_id in seen_ids:
                                return None
                            seen_ids.add(job_id)

                        company_elem = card.select_one(
                            ".jsl-item__cpn, .company-name, a[class*='company'], .company, p[class*='company'], .employer-name"
                        )
                        company = company_elem.get_text(strip=True) if company_elem else "ITNavi Employer"

                        location_elem = card.select_one(
                            ".jsl-item__location, .location, .address, span[class*='location'], span[class*='city'], .city"
                        )
                        location = location_elem.get_text(strip=True) if location_elem else "Vietnam"

                        salary_elem = card.select_one(
                            ".jsl-item__sm, .salary, span[class*='salary'], .text-salary, .salary-text, .price"
                        )
                        salary_text = salary_elem.get_text(" ", strip=True) if salary_elem else ""

                        skill_elems = card.select(
                            ".tag, .skill-tag, .skill-item, span[class*='tag'], span[class*='skill'], a.tag, .jsl-item__tag"
                        )
                        skills = [s.get_text(strip=True) for s in skill_elems if s.get_text(strip=True)]

                        url = None
                        description = ""
                        min_salary = None
                        max_salary = None

                        if job_id:
                            try:
                                ajax_url = f"{self.BASE_URL}/ajax/get-job-by-id/{job_id}"
                                ajax_resp = await client.get(ajax_url, headers=headers, timeout=5.0)
                                if ajax_resp.status_code == 200:
                                    ajax_data = ajax_resp.json().get("data", {})
                                    canonical_slug = ajax_data.get("job_slug")
                                    if canonical_slug:
                                        url = canonical_slug if canonical_slug.startswith("http") else f"{self.BASE_URL}{canonical_slug}"
                                    if ajax_data.get("job_content"):
                                        description = BeautifulSoup(ajax_data["job_content"], "html.parser").get_text(separator="\n").strip()
                                    min_salary = ajax_data.get("job_salary_min")
                                    max_salary = ajax_data.get("job_salary_max")
                                    for sk in ajax_data.get("skill", []):
                                        sk_name = sk.get("name") if isinstance(sk, dict) else str(sk)
                                        if sk_name and sk_name not in skills:
                                            skills.append(sk_name)
                            except Exception as e:
                                logger.debug(f"ITNavi AJAX detail fetch error for job_id={job_id}: {e}")

                        if not url:
                            copy_elem = card.select_one("[data-copy]")
                            if copy_elem and copy_elem.get("data-copy"):
                                url = copy_elem.get("data-copy")
                            else:
                                link_elem = card.select_one("a[href*='/job-detail/'], a[href*='/viec-lam-']")
                                if link_elem and link_elem.get("href"):
                                    rel_url = link_elem.get("href")
                                    url = rel_url if rel_url.startswith("http") else f"{self.BASE_URL}{rel_url}"
                                elif job_id:
                                    url = f"{self.BASE_URL}/job-detail/{job_id}"
                                else:
                                    url = self.SEARCH_URL

                        card_payload = {
                            "title": title,
                            "company": company,
                            "location": location,
                            "url": url,
                            "salary_text": salary_text,
                            "min_salary": min_salary,
                            "max_salary": max_salary,
                            "description": description,
                            "skills": skills,
                        }

                        content_hash = self.compute_content_hash(f"{title}|{company}|{location}|{url}")
                        return RawJobData(
                            source=self.source_name,
                            source_url=url,
                            source_job_id=job_id or None,
                            raw_payload=card_payload,
                            raw_html=str(card),
                            content_hash=content_hash,
                        )

                    before = len(results)
                    card_tasks = [_parse_card(card) for card in job_cards]
                    parsed_cards = await asyncio.gather(*card_tasks)

                    for raw_item in parsed_cards:
                        if not raw_item:
                            continue
                        if not unlimited and len(results) >= limit:
                            break
                        if raw_item.source_url in seen:
                            continue
                        seen.add(raw_item.source_url)
                        results.append(raw_item)

                    if len(results) == before:
                        break
                    page += 1
                    if page <= max_pages and (unlimited or len(results) < limit):
                        await asyncio.sleep(0.35)

                logger.info(f"Successfully scraped {len(results)} IT jobs across {page-1} pages from ITnavi.com.vn")
        except Exception as e:
            logger.error(f"Error scraping ITnavi: {e}", exc_info=True)

        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}

        desc = payload.get("description") or ""
        if not desc and raw.raw_html:
            desc = BeautifulSoup(raw.raw_html, "html.parser").get_text(separator=" ").strip()
            desc = " ".join(desc.split())
        if not desc:
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
            min_salary=payload.get("min_salary"),
            max_salary=payload.get("max_salary"),
            description=desc,
            skills_required=payload.get("skills", []),
            skills_nice_to_have=[],
            posted_at=datetime.now(timezone.utc),
        )
