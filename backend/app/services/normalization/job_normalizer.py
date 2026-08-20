import hashlib
import re
from typing import Optional, Tuple
from app.models.job import JobLevelEnum, WorkModeEnum


class JobNormalizer:
    """
    Service chuẩn hóa các trường thông tin tin tuyển dụng:
    Title, Company, Location, Work Mode, Job Level, Salary và Dedup Signature.
    """

    # Các từ khóa và tiền tố thường gặp trong tiêu đề
    TITLE_CLEANUP_REGEX = re.compile(
        r"(\[.*?\]|\(.*?\)|(\b(tuyển gấp|urgent|hot|hấp dẫn|lương hấp dẫn|lương thỏa thuận|lương cao|up to\s*[$0-9,kM]+|tháng\s*[0-9]+)\b))",
        re.IGNORECASE,
    )

    # Các hậu tố pháp nhân công ty cần loại bỏ để chuẩn hóa tên
    COMPANY_CLEANUP_REGEX = re.compile(
        r"\b(công ty cổ phần|công ty tnhh|công ty|tnhh|cp|co\.,\s*ltd\.?|co\.,\s*ltd|inc\.?|llc|corp\.?|corporation|jsc|vietnam|việt nam|vn)\b",
        re.IGNORECASE,
    )

    @classmethod
    def normalize_title(cls, title: str) -> str:
        """Làm sạch tiêu đề công việc."""
        if not title:
            return ""

        # Xóa các tag vuông/tròn và cụm từ quảng cáo
        cleaned = cls.TITLE_CLEANUP_REGEX.sub(" ", title)
        # Chuẩn hóa khoảng trắng
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Xóa các ký tự phân cách thừa ở đầu/cuối như '-', '|', ':'
        cleaned = re.sub(r"^[\s\-\|:\–]+|[\s\-\|:\–]+$", "", cleaned).strip()

        return cleaned if cleaned else title.strip()

    @classmethod
    def normalize_company(cls, company_name: str) -> str:
        """Chuẩn hóa tên công ty về dạng cốt lõi."""
        if not company_name:
            return ""

        cleaned = cls.COMPANY_CLEANUP_REGEX.sub(" ", company_name)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"^[\s\-\|:\–]+|[\s\-\|:\–]+$", "", cleaned).strip()

        # Nếu viết tắt chữ hoa <= 4 ký tự (như VNG, FPT, CMC, VNPT), giữ nguyên
        if cleaned.isupper() and len(cleaned) <= 4:
            return cleaned

        # Format Title Case nếu toàn bộ viết thường
        if cleaned.islower():
            cleaned = cleaned.title()

        return cleaned if cleaned else company_name.strip()

    @classmethod
    def normalize_location(cls, location_str: Optional[str]) -> Tuple[Optional[str], WorkModeEnum]:
        """
        Chuẩn hóa địa điểm và suy luận hình thức làm việc (Work Mode).
        """
        if not location_str or not location_str.strip():
            return None, WorkModeEnum.ONSITE

        raw = location_str.strip()
        lower = raw.lower()

        # Phát hiện work mode
        work_mode = WorkModeEnum.ONSITE
        if "remote" in lower or "từ xa" in lower or "làm việc tại nhà" in lower or "wfh" in lower:
            if "hybrid" in lower or "linh hoạt" in lower:
                work_mode = WorkModeEnum.HYBRID
            else:
                work_mode = WorkModeEnum.REMOTE
        elif "hybrid" in lower:
            work_mode = WorkModeEnum.HYBRID

        # Chuẩn hóa thành phố chính
        if any(kw in lower for kw in ["hcm", "hồ chí minh", "ho chi minh", "tp.hcm", "sài gòn", "saigon", "q1", "q2", "q7", "thủ đức"]):
            return "Ho Chi Minh City", work_mode
        elif any(kw in lower for kw in ["hà nội", "ha noi", "hn", "cầu giấy", "ba đình", "nam từ liêm"]):
            return "Hanoi", work_mode
        elif any(kw in lower for kw in ["đà nẵng", "da nang", "dn"]):
            return "Da Nang", work_mode
        elif "vietnam" in lower or "việt nam" in lower:
            return "Vietnam", work_mode

        return raw, work_mode

    @classmethod
    def normalize_level(cls, title: str, description: str = "") -> JobLevelEnum:
        """Suy luận cấp bậc công việc từ tiêu đề hoặc mô tả."""
        text = f"{title} {description}".lower()

        if re.search(r"\b(intern|internship|thực tập|thực tập sinh)\b", text):
            return JobLevelEnum.INTERN
        if re.search(r"\b(fresher|mới tốt nghiệp)\b", text):
            return JobLevelEnum.FRESHER
        if re.search(r"\b(lead|tech lead|team lead|trưởng nhóm)\b", text):
            return JobLevelEnum.LEAD
        if re.search(r"\b(manager|quản lý|director|giám đốc|head of)\b", text):
            return JobLevelEnum.MANAGER
        if re.search(r"\b(senior|sr\.?|chuyên viên cao cấp)\b", text):
            return JobLevelEnum.SENIOR
        if re.search(r"\b(junior|jr\.?)\b", text):
            return JobLevelEnum.JUNIOR
        if re.search(r"\b(mid|middle|intermediate|chuyên viên)\b", text):
            return JobLevelEnum.MID

        return JobLevelEnum.UNKNOWN

    @classmethod
    def normalize_salary(
        cls,
        min_salary: Optional[float] = None,
        max_salary: Optional[float] = None,
        currency: Optional[str] = None,
        raw_text: str = "",
    ) -> Tuple[Optional[float], Optional[float], Optional[str], bool]:
        """
        Chuẩn hóa mức lương về chuẩn (Min, Max, Currency, is_negotiable).
        """
        is_negotiable = False
        text = (raw_text or "").lower()

        if not min_salary and not max_salary:
            if any(kw in text for kw in ["thỏa thuận", "negotiable", "competitive", "cạnh tranh", "trao đổi"]):
                return None, None, None, True

            # Regex trích xuất lương dạng "$1,000 - $2,500" hoặc "20 - 40 triệu"
            usd_match = re.search(r"\$\s*([0-9,]+)\s*-\s*\$?\s*([0-9,]+)", raw_text)
            if usd_match:
                min_sal = float(usd_match.group(1).replace(",", ""))
                max_sal = float(usd_match.group(2).replace(",", ""))
                return min_sal, max_sal, "USD", False

            vnd_match = re.search(r"([0-9]+)\s*-\s*([0-9]+)\s*(triệu|tr|m|vnd)", text)
            if vnd_match:
                min_sal = float(vnd_match.group(1)) * 1_000_000
                max_sal = float(vnd_match.group(2)) * 1_000_000
                return min_sal, max_sal, "VND", False

        curr = currency.upper() if currency else ("USD" if min_salary and min_salary < 50000 else "VND" if min_salary else None)
        return min_salary, max_salary, curr, is_negotiable

    @classmethod
    def compute_dedup_signature(
        cls,
        normalized_company: str,
        normalized_title: str,
        normalized_location: Optional[str],
    ) -> str:
        """
        Tạo chữ ký Exact Deduplication (MD5) từ: normalized_company:normalized_title:location.
        """
        company_key = (normalized_company or "").strip().lower()
        title_key = (normalized_title or "").strip().lower()
        loc_key = (normalized_location or "").strip().lower()

        payload = f"{company_key}:{title_key}:{loc_key}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Singleton Instance
job_normalizer = JobNormalizer()
