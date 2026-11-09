"""Saramin Vietnam public IT jobs API (formerly TopDev)."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData
from app.services.extraction.detail_fetcher import clean_html_to_text, parse_posted_datetime

logger = logging.getLogger(__name__)


class SaraminJobCollector(BaseJobCollector):
    API_URL = "https://api.saramin.vn/td/v2/jobs"
    MAX_PAGES = 200

    @property
    def source_name(self) -> str:
        return "saramin"

    async def fetch_jobs(self, limit: int = 50) -> list[RawJobData]:
        results = []
        seen = set()
        params = {
            # ponytail: API page_size=100 repeats IDs after page 1; use verified 20-row pages.
            "job_categories_ids": 1, "page_size": 20,
            "fields[job]": "id,title,company,addresses,skills_arr,salary,detail_url,status_display,published,refreshed,description",
            "fields[company]": "display_name",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            for page in range(1, self.MAX_PAGES + 1):
                response = await client.get(self.API_URL, params={**params, "page": page})
                response.raise_for_status()
                body = response.json()
                items = body.get("data") if isinstance(body, dict) else None
                if not isinstance(items, list):
                    raise ValueError("Saramin API returned invalid data")
                if not items:
                    break
                new_ids = 0
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    job_id = item.get("id")
                    title = item.get("title")
                    url = item.get("detail_url")
                    company = item.get("company")
                    if (not isinstance(job_id, int) or isinstance(job_id, bool) or job_id <= 0
                            or not isinstance(title, str) or not title.strip()
                            or not isinstance(company, dict) or not isinstance(company.get("display_name"), str)
                            or not company["display_name"].strip() or not isinstance(url, str)):
                        continue
                    try:
                        parsed = urlsplit(url)
                        valid_url = (parsed.scheme == "https" and parsed.hostname in {"saramin.vn", "www.saramin.vn"}
                                     and parsed.port in (None, 443) and not parsed.username and not parsed.password
                                     and parsed.path.startswith(("/detail-jobs/", "/viec-lam/")))
                    except ValueError:
                        valid_url = False
                    if not valid_url or job_id in seen:
                        continue
                    seen.add(job_id)
                    new_ids += 1
                    addresses = item.get("addresses") or {}
                    skills = item.get("skills_arr") or []
                    expiry = parse_posted_datetime(item.get("expired_at"))
                    # Unknown states are not expiry evidence; do not treat every non-Open state as expired.
                    status = str(item.get("status_display") or "").strip().casefold()
                    payload = {
                        **item, "company": company["display_name"],
                        "location": addresses.get("address_region_list") if isinstance(addresses, dict) else None,
                        "skills": [s for s in skills if isinstance(s, str) and s.strip()] if isinstance(skills, list) else [],
                        "is_expired": status in {"expired", "closed", "hết hạn", "đã đóng", "đã hết hạn"}
                            or bool(expiry and expiry <= datetime.now(timezone.utc)),
                    }
                    results.append(RawJobData(
                        source=self.source_name, source_url=url, source_job_id=str(job_id), raw_payload=payload,
                        content_hash=self.compute_content_hash(json.dumps(item, sort_keys=True, ensure_ascii=False)),
                    ))
                    if limit > 0 and len(results) >= limit:
                        return results
                if not new_ids:
                    break
                meta = body.get("meta") or {}
                try:
                    last_page = int(meta["last_page"])
                except (KeyError, TypeError, ValueError):
                    raise ValueError("Saramin API returned invalid pagination") from None
                if page >= last_page:
                    break
                await asyncio.sleep(0.35)
        return results

    @staticmethod
    def _published_at(payload):
        if payload.get("posted_iso"):
            return parse_posted_datetime(payload["posted_iso"])
        published = payload.get("published")
        if not isinstance(published, dict):
            return None
        for key, fmt in (("datetime", "%H:%M:%S %d-%m-%Y"), ("date", "%d-%m-%Y")):
            try:
                # API dates are Vietnam local time; do not mistake DD-MM for MM-DD.
                from datetime import timedelta
                return datetime.strptime(published[key], fmt).replace(tzinfo=timezone(timedelta(hours=7)))
            except (KeyError, TypeError, ValueError):
                pass
        return None

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}
        # Masked/negotiable salaries are unknown, never substitute estimates or zero.
        salary = payload.get("salary") or {}
        def amount(key):
            value = salary.get(key) if isinstance(salary, dict) else None
            if isinstance(value, bool):
                return None
            try:
                number = float(value)
                return number if 0 < number < float("inf") else None
            except (ValueError, TypeError):
                return None
        return JobExtractedData(
            title=payload["title"].strip(), company_name=payload["company"].strip(),
            location=payload.get("location") or None,
            description=clean_html_to_text(str(payload.get("description") or "")) or payload["title"],
            skills_required=payload.get("skills", []), apply_url=raw.source_url,
            min_salary=amount("min"), max_salary=amount("max"),
            salary_currency=salary.get("currency") if isinstance(salary, dict) else None,
            is_salary_negotiable=str(salary.get("is_negotiable", "0")) == "1" if isinstance(salary, dict) else False,
            posted_at=self._published_at(payload),
            expires_at=parse_posted_datetime(payload.get("expires_iso") or payload.get("expired_at")),
        )
