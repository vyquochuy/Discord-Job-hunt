"""
Job Detail Fetcher — Detail Page Enrichment Service (Phase 2.7)

Làm giàu (enrich) tin tuyển dụng mức Listing (thẻ card trang danh sách) bằng
nội dung JD đầy đủ lấy từ trang chi tiết:

    JSON-LD JobPosting (schema.org)  ->  Site-specific DOM selectors
    ->  Generic main-container extraction  ->  Quality Validation

Nguyên tắc thiết kế (tuân thủ Invariants của AGENTS.md):
- Chỉ GET READ-ONLY: KHÔNG BAO GIỜ né/vượt CAPTCHA, WAF, login, rate limit
  (Invariant 19). Trang challenge/login được PHÁT HIỆN và đánh dấu BLOCKED;
  pipeline giữ nguyên dữ liệu listing và đề xuất fallback nhập tay.
- Detail enrichment là tùy chọn: nếu trích xuất thất bại, pipeline tiếp tục
  với dữ liệu listing (graceful degradation, không bao giờ gián đoạn ingest).
- Retry giới hạn (mặc định 2 lần, backoff tuyến tính 1.5s/3s). Các HTTP
  terminal 401/403/429 KHÔNG được retry lại để tránh vi phạm chính sách
  của nền tảng tuyển dụng (tương thích Invariant 22 về idempotent safety).
- Dữ liệu JD "giàu hơn" thắng "nghèo hơn" khi merge (richer-record merge):
  description dài hơn, skills là hợp (union) không lossy, ngày đăng thì
  chọn nguồn tin cậy cao hơn (JSON-LD datePosted > relative text).
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from app.services.extraction.url_fetcher import FetchedDocument, url_fetcher

logger = logging.getLogger("detail_fetcher")


# ==============================================================================
# Constants & Detection Rules
# ==============================================================================

# Nguồn được thiết kế trang chi tiết server-rendered / có JSON-LD, sẽ được
# làm giàu tự động. Các nguồn API đầy đủ sẵn (remotive) cần không enrich để
# tiết kiệm băng thông và chi phí runtime.
SUPPORTED_SOURCES = frozenset({"itviec", "topcv", "saramin", "vietnamworks", "careerlink"})

# Nếu listing description đã đủ dài (ví dụ VietnamWorks Search API trả về JD
# đầy đủ), bỏ qua bước detail fetch để tiết kiệm chi phí.
SKIP_IF_DESC_AT_LEAST = 800

# Độ dài tối thiểu coi là JD chi tiết hợp lệ.
MIN_DETAIL_LENGTH = 200

# Backoff tuyến tính giữa các lần retry (giây): 1.5s -> 3.0s -> ...
RETRY_BASE_DELAY_SECONDS = 1.5

# HTTP status KHÔNG được retry lại (terminal): vi phạm chính sách/truy cập.
TERMINAL_HTTP_STATUSES = frozenset({401, 403, 407, 429})

CHALLENGE_TITLE_MARKERS = (
    "just a moment",
    "attention required",
    "access denied",
    "security check",
    "bot verification",
)

CHALLENGE_SELECTORS = (
    "#challenge-form",
    "#cf-challenge-running",
    ".cf-browser-verification",
    "#challenge-error-text",
    "script[src*='challenges.cloudflare.com']",
)

CHALLENGE_TEXT_MARKERS = (
    "checking your browser before accessing",
    "verify you are human",
    "cf-browser-verification",
    "performance & security by cloudflare",
    "needs to review the security of your connection",
    "enable javascript and cookies to continue",
)

LOGIN_TITLE_MARKERS = (
    "sign in",
    "log in",
    "đăng nhập",
)

LOGIN_TEXT_MARKERS = (
    "sign in to view",
    "sign in to apply",
    "log in to view",
    "login to continue",
    "đăng nhập để xem",
    "đăng nhập để ứng tuyển",
    "you need to sign in",
)

# Boilerplate chung của platform (không phải nội dung JD).
PLATFORM_BOILERPLATE_MARKERS = (
    "Tiếp lợi thế",
    "Hệ sinh thái HR Tech",
    "TopCV hiểu rõ",
    "Định vị bản thân",
    "Tìm việc làm mới",
    "More jobs for you",
    "Other jobs at this company",
)

EXPIRED_TEXT_MARKERS = (
    "tin tuyển dụng đã hết hạn",
    "tin tuyển dụng này đã hết hạn",
    "tin đã hết hạn",
    "hết hạn nộp",
    "vị trí này đã đóng",
    "đã dừng nhận hồ sơ",
    "ngừng nhận hồ sơ",
    "job is expired",
    "job expired",
    "this job is no longer available",
    "this position has been closed",
    "posting has closed",
    "no longer accepting applications",
)


# ==============================================================================
# Result Dataclass
# ==============================================================================

@dataclass
class JobDetailResult:
    """Kết quả của một lần trích xuất trang chi tiết tin tuyển dụng."""

    source: str
    url: str
    # OK | BLOCKED | INCOMPLETE | FAILED
    status: str
    description: str = ""
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_expired: bool = False
    employment_type: Optional[str] = None
    experience_months: Optional[int] = None
    skills: List[str] = field(default_factory=list)
    json_ld: Optional[Dict[str, Any]] = None
    method: Optional[str] = None  # jsonld | site_dom | generic | page_text
    error: Optional[str] = None
    attempts: int = 0


# ==============================================================================
# Quality Validators (Challenge / Login detection)
# ==============================================================================

def is_challenge_page(soup: BeautifulSoup) -> Optional[str]:
    """Phát hiện trang chặn роли bảo mật (Cloudflare/challenge) - chỉ detect,
    KHÔNG tự vượt (Invariants 19). Trả về lý do nếu phát hiện."""
    title = (soup.title.get_text(" ", strip=True) if soup.title else "").lower()
    if any(m in title for m in CHALLENGE_TITLE_MARKERS):
        return "CHALLENGE_TITLE"

    try:
        if any(soup.select_one(sel) for sel in CHALLENGE_SELECTORS):
            return "CHALLENGE_DOM"
    except Exception:
        pass

    text = soup.get_text(" ", strip=True)[:1500].lower()
    if any(m in text for m in CHALLENGE_TEXT_MARKERS):
        return "CHALLENGE_TEXT"
    return None


def is_login_gate(soup: BeautifulSoup) -> Optional[str]:
    """Phát hiện trang cần đăng nhập mới xem được JD.
    Chỉ coi là login-gate khi tiêu đề chứa marker HOẶC nội dung quá ngắn
    (tránh false-positive với JD thường có nhắc từ 'sign in')."""
    title = (soup.title.get_text(" ", strip=True) if soup.title else "").lower()
    if title and any(m in title for m in LOGIN_TITLE_MARKERS):
        return "LOGIN_TITLE"

    text = soup.get_text(" ", strip=True)
    if len(text) < 500 and any(m in text.lower() for m in LOGIN_TEXT_MARKERS):
        return "LOGIN_TEXT"
    return None


def check_is_job_expired(soup: BeautifulSoup) -> bool:
    """
    Phát hiện xem trang chi tiết có hiển thị thông báo tin đã hết hạn/ngừng tuyển không.
    """
    # 1. Kiểm tra các thẻ thông báo nổi bật (banner, badge, alert)
    alert_elems = soup.select(
        ".job-expired, .job-closed, .alert-warning, .badge-expired, "
        "[class*='expired'], [class*='closed'], .status-expired"
    )
    for el in alert_elems:
        txt = el.get_text(" ", strip=True).lower()
        if any(m in txt for m in EXPIRED_TEXT_MARKERS):
            return True

    # 2. Quét 1000 ký tự đầu và các đoạn tiêu đề
    text_snippet = soup.get_text(" ", strip=True)[:1500].lower()
    return any(m in text_snippet for m in EXPIRED_TEXT_MARKERS)


def extract_deadline_from_dom(soup: BeautifulSoup) -> Optional[datetime]:
    """
    Bóc tách hạn nộp hồ sơ từ các thẻ hiển thị deadline thông dụng của sàn VN:
    - TopCV: .job-detail__info--deadline, "Hạn nộp hồ sơ: 30/11/2026"
    - ITViec: "Hạn nộp:", "Deadline:"
    - Generic regex tìm "Hạn nộp (hồ sơ)?: dd/mm/yyyy"
    """
    # 1. Thẻ chuyên dụng
    deadline_selectors = [
        ".job-detail__info--deadline",
        ".deadline",
        ".job-deadline",
        "[class*='deadline']",
        "span.text-deadline",
        "div.job-detail__info div:has(> i.fa-calendar)",
    ]
    for sel in deadline_selectors:
        try:
            elem = soup.select_one(sel)
            if elem:
                txt = elem.get_text(" ", strip=True)
                dt = parse_posted_datetime(txt)
                if dt:
                    return dt
        except Exception:
            continue

    # 2. Regex quét toàn bộ văn bản tìm mẫu "Hạn nộp (hồ sơ)?: dd/mm/yyyy"
    full_text = soup.get_text(" ", strip=True)
    m = re.search(
        r"(?:hạn\s*nộp(?:\s*hồ\s*sơ)?|deadline|hết\s*hạn\s*vào)\s*[:：\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        full_text,
        re.IGNORECASE,
    )
    if m:
        return parse_posted_datetime(m.group(1))

    return None


# ==============================================================================
# Merge Helper (Richer-record merge)
# ==============================================================================

def merge_detail_into_payload(
    payload: Optional[Dict[str, Any]],
    result: JobDetailResult,
) -> Dict[str, Any]:
    """
    Merge kết quả detail fetch vào listing payload theo nguyên tắc richer-record:
    - Description: chi tiết đầy đủ hơn sẽ thay thế listing desc nếu dài hơn.
    - Skills: union (không trùng, case-insensitive), không drop skill listing.
    - Posted date: JSON-LD datePosted (undan tin cậy cao hơn relative text).
    Không bao giờ xóa field listing đã có để giữ provenance.
    """
    merged = dict(payload or {})

    listing_desc = str(merged.get("description") or "").strip()
    detail_desc = (result.description or "").strip()
    if detail_desc and len(detail_desc) > len(listing_desc):
        merged["description"] = detail_desc

    if result.posted_at and not merged.get("posted_iso"):
        merged["posted_iso"] = result.posted_at.isoformat()

    if result.expires_at:
        merged["expires_iso"] = result.expires_at.isoformat()
    if result.is_expired:
        merged["is_expired"] = True

    listing_skills = [str(s) for s in (merged.get("skills") or [])]
    seen = {s.strip().lower() for s in listing_skills if s}
    for skill in result.skills:
        if not skill:
            continue
        key = str(skill).strip()
        if key.lower() not in seen:
            listing_skills.append(key)
            seen.add(key.lower())
    if listing_skills:
        merged["skills"] = listing_skills

    meta: Dict[str, Any] = {
        "status": result.status,
        "method": result.method,
        "description_length": len(detail_desc),
        "posted_at": result.posted_at.isoformat() if result.posted_at else None,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None,
        "is_expired": result.is_expired,
        "employment_type": result.employment_type,
        "experience_months": result.experience_months,
        "attempts": result.attempts,
        "error": result.error,
    }
    if detail_desc:
        meta["description_hash"] = hashlib.sha256(detail_desc.encode("utf-8")).hexdigest()
    merged["detail_meta"] = meta
    return merged


def note_detail_failure(
    payload: Optional[Dict[str, Any]],
    result: JobDetailResult,
) -> Dict[str, Any]:
    """Ghi nhận trạng thái failure của detail fetch vào payload cho việc
    bookkeeping/retry ở chu kỳ cào sau (không phá dữ liệu listing)."""
    merged = dict(payload or {})
    prev = merged.get("detail_meta") or {}
    merged["detail_meta"] = {
        **prev,
        "status": result.status,
        "method": None,
        "error": result.error,
        "attempts": result.attempts or prev.get("attempts", 0) + 1,
        "description_length": prev.get("description_length") or 0,
    }
    return merged


# ==============================================================================
# Posting Date Parser (relative VN/EN + ISO + epoch)
# ==============================================================================

def parse_posted_datetime(raw: Any) -> Optional[datetime]:
    """Phân tích chuỗi ngày đăng ở nhiều định dạng về datetime timezone-aware:
    - ISO 8601: '2026-10-30T09:00:00+07:00' / '...Z' (JSON-LD datePosted)
    - Epoch (giây hoặc mili-giây, int/str)
    - Relative text VN/EN: 'hôm qua', '3 ngày trước', '2 weeks ago',
      'Posted 5 days ago', '12 tháng trước'...
    Trả về None nếu không phân tích được."""
    if raw is None:
        return None

    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)

    text = str(raw).strip()
    if not text:
        return None

    # 1. Epoch seconds/millis
    if isinstance(raw, (int, float)) or (text.isdigit() and len(text) >= 10):
        try:
            value = float(raw)
            if value > 10_000_000_000:  # millis
                value /= 1000.0
            if 1_000_000_000 <= value < 2_000_000_000:  # năm 2001..2033, tránh nhầm jobId với timestamp
                return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None

    # 2. ISO 8601 (datePosted chuẩn JSON-LD)
    iso_candidate = text.replace("Z", "+00:00").replace("z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_candidate)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # 3. Relative text (BD tách "Posted " prefix như ITViec card)
    lower = text.lower().strip()
    lower = re.sub(r"^posted\s*", "", lower).strip()

    unit_map = {
        "day": "days", "days": "days", "ngày": "days", "ngay": "days",
        "week": "weeks", "weeks": "weeks", "tuần": "weeks", "tuan": "weeks",
        "month": "months", "months": "months", "tháng": "months", "thang": "months",
        "hour": "hours", "hours": "hours", "giờ": "hours", "gio": "hours",
        "giờ trước": "hours", "minute": "minutes", "minutes": "minutes",
        "phút": "minutes",
    }

    now = datetime.now(timezone.utc)

    def _from_match(number: int, unit_key: str) -> Optional[datetime]:
        unit = unit_map.get(unit_key)
        if not unit:
            return None
        if unit == "hours":
            return now - timedelta(hours=number)
        if unit == "minutes":
            return now - timedelta(minutes=number)
        if unit == "days":
            return now - timedelta(days=number)
        if unit == "weeks":
            return now - timedelta(weeks=number)
        if unit == "months":
            return now - timedelta(days=number * 30)  # xấp xỉ quản lý được
        return None

    if lower in ("hôm qua", "yesterday"):
        return now - timedelta(days=1)
    if lower in ("hôm nay", "today"):
        return now

    m = re.search(
        r"(\d+)\s*(giờ|gio|hours?|minutes?|phút|days?|ngày|ngay|weeks?|tuần|tuan|months?|tháng|thang)",
        lower,
    )
    if m:
        number = int(m.group(1))
        dt = _from_match(number, m.group(2))
        if dt:
            return dt

    # 4. Date-only strings: '30/10/2026' hoặc '2026-10-30'
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d/%m"):
        try:
            parsed = datetime.strptime(text, pattern)
            if pattern == "%d/%m":
                parsed = parsed.replace(year=now.year)
            return parsed.replace(tzinfo=timezone.utc) if not parsed.tzinfo else parsed
        except ValueError:
            continue

    return None


# ==============================================================================
# Description Cleaning
# ==============================================================================

def clean_html_to_text(html: str) -> str:
    """HTML -> text sạch giữ newline cấu trúc (dùng cho description payload)."""
    if not html or not html.strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return normalize_description(text)


def normalize_description(text: str) -> str:
    """Chuẩn hóa nhẹ: \r\n -> \n, gộp nhiều dòng trống, trim."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


# ==============================================================================
# Site-specific Description Extraction
# ==============================================================================

def _pick_largest_block(soup: BeautifulSoup, min_length: int = 400) -> str:
    """Chọn block nội dung lớn nhất không chứa boilerplate platform
    (chiến thuật an toàn khi các trang thay đổi class CSS)."""
    best = ""
    for el in soup.select("div, section"):
        try:
            txt = el.get_text("\n", strip=True)
        except Exception:
            continue
        if len(txt) <= len(best) or len(txt) < min_length:
            continue
        if any(b in txt for b in PLATFORM_BOILERPLATE_MARKERS):
            continue
        best = txt
    return best


def _json_ld_description(json_ld: Optional[Dict[str, Any]]) -> str:
    if not isinstance(json_ld, dict):
        return ""
    desc = json_ld.get("description") or ""
    if not desc:
        return ""
    return BeautifulSoup(str(desc), "html.parser").get_text("\n", strip=True)


def _site_selectors(source: str) -> List[str]:
    """Selectors ưu tiên cho từng nguồn, theo thứ tự giảm độ tin cậy."""
    if source == "itviec":
        return [
            "[class*='job-detail']",
            "[class*='job-description']",
            ".job-description__content",
            "article",
            "main",
        ]
    if source == "saramin":
        # Card JD dedicated của TopDev/Saramin (avoid side panels toàn trang).
        return ["div.rounded-xl.border.p-4", "[class*='job-description']", "article", "main"]
    if source == "topcv":
        return [
            "[class*='job-description']",
            "[class*='job-detail'] .job-detail__body--content",
            ".job-detail",
            "section",
        ]
    if source == "vietnamworks":
        return ["[class*='job-description']", "article", "main", "section"]
    # careerlink + generic fallback
    return ["[class*='job-description']", "article", "main", "section"]


_TOPDEV_JD_MARKERS = (
    "Your role",
    "Your skills",
    "responsibilities",
    "Benefits",
    "Mô tả",
    "Yêu cầu",
    "Quyền lợi",
)


def extract_site_description(source: str, soup: BeautifulSoup) -> Tuple[str, str]:
    """Bóc tách description DOM theo từng nguồn.
    Trả về (description, method)."""
    for sel in _site_selectors(source):
        try:
            elements = soup.select(sel)
        except Exception:
            continue
        for el in elements:
            try:
                txt = el.get_text("\n", strip=True)
            except Exception:
                continue
            if len(txt) < MIN_DETAIL_LENGTH:
                continue
            if source == "saramin" and not any(m in txt for m in _TOPDEV_JD_MARKERS):
                continue
            if any(b in txt[:200] for b in PLATFORM_BOILERPLATE_MARKERS):
                continue
            return txt, f"site_dom:{sel}"
    return "", ""


def _extract_jsonld_meta(json_ld: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if not isinstance(json_ld, dict):
        return meta

    posted_dt = parse_posted_datetime(json_ld.get("datePosted"))
    if posted_dt:
        meta["posted_at"] = posted_dt

    # Schema.org JobPosting: validThrough quy định thời hạn hết hạn của tin tuyển dụng
    expires_dt = parse_posted_datetime(json_ld.get("validThrough") or json_ld.get("expires"))
    if expires_dt:
        meta["expires_at"] = expires_dt

    employment = json_ld.get("employmentType")
    if isinstance(employment, str) and employment.strip():
        meta["employment_type"] = employment.strip()

    exp = json_ld.get("experienceRequirements")
    if isinstance(exp, dict) and exp.get("monthsOfExperience"):
        try:
            meta["experience_months"] = int(exp["monthsOfExperience"])
        except (TypeError, ValueError):
            pass

    raw_skills = json_ld.get("skills")
    skills: List[str] = []
    if isinstance(raw_skills, list):
        for s in raw_skills:
            if isinstance(s, dict) and s.get("name"):
                skills.append(str(s["name"]).strip())
            elif isinstance(s, str) and s.strip():
                skills.append(s.strip())
    elif isinstance(raw_skills, str) and raw_skills.strip():
        skills = [x.strip() for x in raw_skills.split(",") if x.strip()]
    if skills:
        meta["skills"] = skills[:30]

    return meta


# ==============================================================================
# Main Fetcher Service
# ==============================================================================

class JobDetailFetcher:
    """
    Service fetch trang chi tiết tin tuyển dụng qua URLFetcher(SSRF-safe):
    JSON-LD trước, DOM theo nguồn sau, generic main container cuối.
    """

    def is_supported(self, source: str) -> bool:
        return source in SUPPORTED_SOURCES

    async def fetch_detail(
        self,
        source: str,
        url: str,
        max_attempts: int = 2,
        timeout: float = 10.0,
    ) -> JobDetailResult:
        """Fetch và trích xuất trang chi tiết. Không bao giờ raise - tất cả
        lỗi được map về một trong các trạng thái BLOCKED/INCOMPLETE/FAILED."""
        max_attempts = max(1, max_attempts)
        result = JobDetailResult(source=source, url=url, status="FAILED")

        for attempt in range(1, max_attempts + 1):
            result.attempts = attempt
            try:
                doc: FetchedDocument = await url_fetcher.fetch(url, timeout=timeout)
            except Exception as exc:  # defensive: URLFetcher đã self-manage lỗi
                logger.warning(f"[{source}] detail fetch('{url}') raised: {exc}")
                result.error = f"FETCH_EXC:{type(exc).__name__}"
                await self._backoff(attempt)
                continue

            if doc.fetch_method == "failed":
                result.error = doc.error or "UNKNOWN_FETCH_ERROR"
                if self._is_terminal(doc.status_code):
                    result.status = "BLOCKED"
                    logger.warning(
                        f"[{source}] detail fetch terminal blocked "
                        f"({doc.status_code}) for {url}: not retrying."
                    )
                    return result
                if doc.error == "JS_REQUIRED":
                    # SPA render client-side: HTTP-only không thấy nội dung.
                    result.status = "INCOMPLETE"
                    return result
                await self._backoff(attempt)
                continue

            soup = BeautifulSoup(doc.html or "", "html.parser")

            challenge = is_challenge_page(soup)
            if challenge:
                result.status = "BLOCKED"
                result.error = f"WAF_CHALLENGE:{challenge}"
                logger.warning(f"[{source}] WAF/login challenge detected: {url} ({challenge}).")
                return result

            login_gate = is_login_gate(soup)
            if login_gate:
                result.status = "BLOCKED"
                result.error = f"LOGIN_GATE:{login_gate}"
                logger.warning(f"[{source}] Login gate detected: {url} ({login_gate}).")
                return result

            description, method = self._extract_description(source, soup, doc)
            if len(description) < MIN_DETAIL_LENGTH:
                result.error = "INSUFFICIENT_CONTENT"
                result.status = "INCOMPLETE"
                await self._backoff(attempt)
                continue

            meta = _extract_jsonld_meta(doc.json_ld)
            expires_at = meta.get("expires_at") or extract_deadline_from_dom(soup)
            is_expired = check_is_job_expired(soup)
            if not is_expired and expires_at:
                now_utc = datetime.now(timezone.utc)
                if expires_at < now_utc:
                    is_expired = True

            result.status = "OK"
            result.description = normalize_description(description)
            result.method = method
            result.json_ld = doc.json_ld if isinstance(doc.json_ld, dict) else None
            result.posted_at = meta.get("posted_at")
            result.expires_at = expires_at
            result.is_expired = is_expired
            result.employment_type = meta.get("employment_type")
            result.experience_months = meta.get("experience_months")
            result.skills = meta.get("skills", [])
            result.error = None
            return result

        if result.status not in ("BLOCKED", "INCOMPLETE"):
            result.status = "FAILED"
        return result

    def _is_terminal(self, status_code: int) -> bool:
        return status_code in TERMINAL_HTTP_STATUSES

    def _extract_description(
        self, source: str, soup: BeautifulSoup, doc: FetchedDocument
    ) -> Tuple[str, str]:
        # Ưu tiên 1: JSON-LD JobPosting (ít vỡ bởi layout, chuẩn schema.org)
        jsonld_desc = _json_ld_description(doc.json_ld)
        if len(jsonld_desc) >= MIN_DETAIL_LENGTH:
            return jsonld_desc, "jsonld"

        # Ưu tiên 2: DOM selectors theo từng nguồn
        site_desc, site_method = extract_site_description(source, soup)
        if site_desc:
            return site_desc, site_method

        # Ưu tiên 3: Fallback toàn trang lớn nhất (largest-block heuristic)
        largest = _pick_largest_block(soup, min_length=MIN_DETAIL_LENGTH)
        if largest:
            return largest, "largest_block"

        # Ưu tiên 4: clean text URLFetcher (main/article đã lọc script/nav)
        if doc.clean_text and len(doc.clean_text) >= MIN_DETAIL_LENGTH:
            return doc.clean_text, "page_text"

        return "", ""

    async def _backoff(self, attempt: int) -> None:
        delay = RETRY_BASE_DELAY_SECONDS * attempt
        if delay > 0 and attempt < 3:  # cap ~3s để tránh pipeline kéo dài bất thường
            await asyncio.sleep(delay)


# Singleton Instance
job_detail_fetcher = JobDetailFetcher()

# Alias ngắn gọn
detail_fetcher = job_detail_fetcher
