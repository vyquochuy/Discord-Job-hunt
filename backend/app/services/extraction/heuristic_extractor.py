import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.job import JobLevelEnum, WorkModeEnum
from app.schemas.job import JobExtractedData
from app.services.normalization.job_normalizer import job_normalizer
from app.services.normalization.skill_normalizer import skill_normalizer

logger = logging.getLogger("heuristic_extractor")


class FieldConfidence(BaseModel):
    field: str
    detected: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    value: Any = None
    method: str = "heuristic"


class ExtractionResult(BaseModel):
    data: JobExtractedData
    method: str = "heuristic"  # "heuristic" | "llm" | "heuristic+llm"
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    fields: List[FieldConfidence] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    extraction_status: str = "PARSED"  # "PARSED" | "PARTIAL" | "FAILED"


class HeuristicJobExtractor:
    """
    Deterministic rule-based extractor từ clean text sang ExtractionResult
    với đánh giá độ tin cậy (Confidence Score) chi tiết trên từng trường dữ liệu.
    """

    CONFIDENCE_THRESHOLD = 0.65

    TITLE_PREFIX_PATTERNS = [
        re.compile(r"^(?:\[(?:Tuyển dụng|Tuyển|HOT|GẤP|Hiring|Job)\]|Vị trí\s*:?|Position\s*:?|Job Title\s*:?|Role\s*:?|Cần tuyển\s*:?|TUYỂN DỤNG\s*:?|🔥|⚡|📢)\s*(.*)", re.I),
        re.compile(r"(?:Tuyển dụng|Tuyển|Cần tìm)\s+(?:vị trí\s+)?([A-Za-z0-9\s\/\+\#\-\.\(\)]+(?:Developer|Engineer|Architect|Lead|Intern|Fresher|Tester|QA|DevOps|Specialist|Manager))", re.I),
    ]

    TECH_ROLE_KEYWORDS = [
        "Backend Developer", "Frontend Developer", "Fullstack Developer", "Software Engineer",
        "DevOps Engineer", "System Engineer", "Cloud Engineer", "Data Engineer", "Data Scientist",
        "AI Engineer", "ML Engineer", "Mobile Developer", "iOS Developer", "Android Developer",
        "Golang Developer", "Python Developer", "Java Developer", "NodeJS Developer", "React Developer",
        "QA Engineer", "QC Engineer", "Automation Tester", "Security Engineer", "Solutions Architect",
        "Tech Lead", "Engineering Manager", "Lập trình viên", "Kỹ sư phần mềm"
    ]

    COMPANY_PATTERNS = [
        re.compile(r"(?:Công ty|Company|Doanh nghiệp|Tập đoàn|Studio|Client)\s*[:：\-]\s*([^\n\r,;|]+)", re.I),
        re.compile(r"(?:làm việc tại|join with|tại)\s+([A-Z0-9][A-Za-z0-9\s\.\,\-&]+(?:JSC|Co\.,\s*Ltd|Corp|Inc|Technologies|Software|Global|Solutions|Vietnam|Việt Nam))", re.I),
        re.compile(r"@\s*([A-Za-z0-9\s\.\-]{2,30})", re.I),
    ]

    def extract(self, text: str, initial_title: Optional[str] = None) -> ExtractionResult:
        """
        Trích xuất thông tin việc làm từ văn bản thuần túy với độ tự tin per-field.
        """
        clean_text = text.strip()
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        warnings: List[str] = []
        fields_confidence: List[FieldConfidence] = []

        if len(clean_text) < 30:
            warnings.append("Text content is too short for reliable extraction.")
            empty_data = JobExtractedData(
                title=initial_title or "Unknown Title",
                company_name="Unknown Company",
                description=clean_text,
            )
            return ExtractionResult(
                data=empty_data,
                method="heuristic",
                overall_confidence=0.1,
                fields=[
                    FieldConfidence(field="title", detected=False, confidence=0.1, method="fallback"),
                    FieldConfidence(field="company", detected=False, confidence=0.0, method="fallback"),
                ],
                warnings=warnings,
                extraction_status="FAILED",
            )

        # 1. Trích xuất Tiêu đề (Title)
        title, title_conf, title_method = self._extract_title(lines, initial_title)
        fields_confidence.append(FieldConfidence(field="title", detected=bool(title), confidence=title_conf, value=title, method=title_method))
        if title_conf < 0.6:
            warnings.append("Job title was inferred with low confidence.")

        # 2. Trích xuất Tên công ty (Company)
        company, comp_conf, comp_method = self._extract_company(lines, title)
        fields_confidence.append(FieldConfidence(field="company", detected=bool(company), confidence=comp_conf, value=company, method=comp_method))
        if comp_conf < 0.5:
            warnings.append("Company name could not be reliably determined.")

        # 3. Trích xuất Mức lương (Salary)
        min_sal, max_sal, curr, is_neg, sal_conf = self._extract_salary(clean_text)
        fields_confidence.append(FieldConfidence(
            field="salary",
            detected=(min_sal is not None or is_neg),
            confidence=sal_conf,
            value={"min": min_sal, "max": max_sal, "currency": curr, "negotiable": is_neg},
            method="regex"
        ))

        # 4. Trích xuất Địa điểm & Work Mode (Location)
        location, work_mode, loc_conf = self._extract_location(clean_text)
        fields_confidence.append(FieldConfidence(
            field="location",
            detected=bool(location),
            confidence=loc_conf,
            value={"location": location, "work_mode": work_mode.value},
            method="keyword_matching"
        ))
        if loc_conf < 0.5:
            warnings.append("Location could not be determined; defaulted to Vietnam/Onsite.")

        # 5. Trích xuất Cấp bậc (Level)
        level, level_conf = self._extract_level(title, clean_text)
        fields_confidence.append(FieldConfidence(
            field="level",
            detected=(level != JobLevelEnum.UNKNOWN),
            confidence=level_conf,
            value=level.value,
            method="keyword_matching"
        ))

        # 6. Trích xuất Kỹ năng (Skills) qua Canonical Taxonomy
        req_skills, nice_skills, skill_conf = self._extract_skills(clean_text)
        fields_confidence.append(FieldConfidence(
            field="skills",
            detected=(len(req_skills) + len(nice_skills) > 0),
            confidence=skill_conf,
            value={"required": req_skills, "nice_to_have": nice_skills},
            method="canonical_taxonomy"
        ))
        if len(req_skills) == 0 and len(nice_skills) == 0:
            warnings.append("No canonical technical skills were detected in the description.")

        # 7. Trích xuất Thông tin liên hệ (Contact Email & Phone)
        email, phone, apply_url, contact_conf = self._extract_contact(clean_text)
        fields_confidence.append(FieldConfidence(
            field="contact",
            detected=(email is not None or phone is not None or apply_url is not None),
            confidence=contact_conf,
            value={"email": email, "phone": phone, "apply_url": apply_url},
            method="regex"
        ))

        # 8. Trích xuất Tóm tắt Yêu cầu & Quyền lợi
        req_summary, ben_summary = self._extract_summaries(clean_text)

        # Tính Overall Confidence có trọng số
        weights = {
            "title": 0.25,
            "company": 0.15,
            "skills": 0.25,
            "salary": 0.10,
            "location": 0.10,
            "level": 0.08,
            "contact": 0.07,
        }
        overall_conf = sum(
            fc.confidence * weights.get(fc.field, 0.05) for fc in fields_confidence
        )
        overall_conf = round(min(1.0, max(0.0, overall_conf)), 2)

        # Xác định Extraction Status: PARSED vs PARTIAL vs FAILED
        if overall_conf >= self.CONFIDENCE_THRESHOLD and title and (company or len(req_skills) > 0):
            status = "PARSED"
        elif overall_conf >= 0.35 and title:
            status = "PARTIAL"
        else:
            status = "FAILED"
            warnings.append("Overall extraction confidence below threshold.")

        extracted_data = JobExtractedData(
            title=title,
            company_name=company,
            location=location,
            work_mode=work_mode,
            level=level,
            min_salary=min_sal,
            max_salary=max_sal,
            salary_currency=curr,
            is_salary_negotiable=is_neg,
            contact_email=email,
            apply_url=apply_url,
            description=clean_text,
            requirements_summary=req_summary,
            benefits_summary=ben_summary,
            skills_required=req_skills,
            skills_nice_to_have=nice_skills,
            posted_at=datetime.now(timezone.utc),
        )

        return ExtractionResult(
            data=extracted_data,
            method="heuristic",
            overall_confidence=overall_conf,
            fields=fields_confidence,
            warnings=warnings,
            extraction_status=status,
        )

    def _extract_title(self, lines: List[str], initial_title: Optional[str]) -> Tuple[str, float, str]:
        """Trích xuất tiêu đề công việc."""
        if initial_title and len(initial_title.strip()) > 3:
            return job_normalizer.normalize_title(initial_title), 0.95, "initial_metadata"

        # Kiểm tra qua các dòng đầu tiên (tối đa 6 dòng đầu)
        for i, line in enumerate(lines[:6]):
            # Kiểm tra patterns prefix
            for pat in self.TITLE_PREFIX_PATTERNS:
                m = pat.search(line)
                if m:
                    extracted = m.group(1).strip()
                    # Làm sạch các ký tự ngăn cách
                    cleaned = re.sub(r"^[\s\-\|:\–]+|[\s\-\|:\–]+$", "", extracted).strip()
                    if len(cleaned) >= 4 and len(cleaned) <= 100:
                        return job_normalizer.normalize_title(cleaned), 0.92, "prefix_regex"

            # Kiểm tra từ khóa chức danh kỹ thuật
            for kw in self.TECH_ROLE_KEYWORDS:
                if re.search(rf"\b{re.escape(kw)}\b", line, re.I):
                    return job_normalizer.normalize_title(line), 0.88, "role_keyword"

        # Fallback lấy dòng đầu tiên nếu ngắn gọn
        first_line = lines[0] if lines else "Software Engineer"
        cleaned_first = job_normalizer.normalize_title(first_line)
        if len(cleaned_first) <= 80:
            return cleaned_first, 0.65, "position_heuristic"

        return "Software Engineer", 0.35, "default_fallback"

    def _extract_company(self, lines: List[str], current_title: str) -> Tuple[str, float, str]:
        """Trích xuất tên công ty."""
        # 1. Quét qua các pattern công ty
        for line in lines[:8]:
            for pat in self.COMPANY_PATTERNS:
                m = pat.search(line)
                if m:
                    comp = m.group(1).strip()
                    cleaned = job_normalizer.normalize_company(comp)
                    if len(cleaned) >= 2 and len(cleaned) <= 80:
                        return cleaned, 0.90, "company_regex"

        # 2. Tìm trong dòng tiêu đề nếu có cấu trúc: "Title at Company" hoặc "Title - Company"
        for line in lines[:3]:
            sep_match = re.search(r"[-–|@]\s*(.+)$", line)
            if sep_match:
                candidate = sep_match.group(1).strip()
                cleaned = job_normalizer.normalize_company(candidate)
                if len(cleaned) >= 2 and len(cleaned) <= 60 and cleaned.lower() != current_title.lower():
                    return cleaned, 0.75, "title_separator"

        # 3. Kiểm tra dòng 2 nếu dòng 1 là title
        if len(lines) > 1 and len(lines[1]) <= 60:
            candidate = lines[1]
            if not any(k in candidate.lower() for k in ["lương", "salary", "địa chỉ", "location", "yêu cầu", "requirement"]):
                cleaned = job_normalizer.normalize_company(candidate)
                if len(cleaned) >= 2:
                    return cleaned, 0.60, "line2_heuristic"

        return "IT Company", 0.30, "default_fallback"

    def _extract_salary(self, text: str) -> Tuple[Optional[float], Optional[float], Optional[str], bool, float]:
        """Trích xuất mức lương."""
        min_sal, max_sal, curr, is_neg = job_normalizer.normalize_salary(raw_text=text)
        if min_sal is not None or max_sal is not None:
            return min_sal, max_sal, curr, is_neg, 0.95
        if is_neg:
            return None, None, None, True, 0.90
        return None, None, None, False, 0.0

    def _extract_location(self, text: str) -> Tuple[Optional[str], WorkModeEnum, float]:
        """Trích xuất địa điểm và hình thức làm việc."""
        loc, work_mode = job_normalizer.normalize_location(text)
        confidence = 0.85 if loc else 0.40
        if work_mode != WorkModeEnum.ONSITE:
            confidence = max(confidence, 0.80)
        return loc or "Vietnam", work_mode, confidence

    def _extract_level(self, title: str, text: str) -> Tuple[JobLevelEnum, float]:
        """Suy luận cấp bậc công việc."""
        level = job_normalizer.normalize_level(title, text)
        confidence = 0.90 if level != JobLevelEnum.UNKNOWN else 0.30
        return level, confidence

    def _extract_skills(self, text: str) -> Tuple[List[str], List[str], float]:
        """Trích xuất kỹ năng bắt buộc và ưu tiên."""
        all_skills = skill_normalizer.extract_skills_from_text(text)
        if not all_skills:
            return [], [], 0.0

        # Phân tách required vs nice-to-have theo sections
        req_skills: List[str] = []
        nice_skills: List[str] = []

        lower_text = text.lower()
        nice_section_pos = -1
        for kw in ["điểm cộng", "nice to have", "plus", "ưu tiên", "lợi thế", "preferred"]:
            pos = lower_text.find(kw)
            if pos != -1:
                nice_section_pos = pos
                break

        if nice_section_pos != -1:
            nice_text = text[nice_section_pos:]
            nice_extracted = skill_normalizer.extract_skills_from_text(nice_text)
            nice_set = set(nice_extracted)
            for s in all_skills:
                if s in nice_set:
                    nice_skills.append(s)
                else:
                    req_skills.append(s)
        else:
            req_skills = all_skills

        confidence = 0.92 if len(all_skills) >= 2 else 0.70
        return req_skills, nice_skills, confidence

    def _extract_contact(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str], float]:
        """Trích xuất email, SĐT, và link apply."""
        email, apply_url = job_normalizer.extract_contact_info(text)
        phone: Optional[str] = None

        phone_match = re.search(r"(?:(?:\+84|0)(?:3|5|7|8|9)\d{8})", text)
        if phone_match:
            phone = phone_match.group(0).strip()

        conf = 0.95 if (email or phone or apply_url) else 0.0
        return email, phone, apply_url, conf

    def _extract_summaries(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Trích xuất tóm tắt requirements và benefits ngắn gọn."""
        req_summary = None
        ben_summary = None

        req_match = re.search(r"(?:yêu cầu|requirements?|mô tả công việc|trách nhiệm)\s*[:：\n]([\s\S]{30,400}?)(?:\n\n|\n[A-Z0-9\-\*\•]|$)", text, re.I)
        if req_match:
            req_summary = " ".join(req_match.group(1).split())[:300]

        ben_match = re.search(r"(?:quyền lợi|benefits?|chế độ|phúc lợi|đãi ngộ)\s*[:：\n]([\s\S]{30,400}?)(?:\n\n|\n[A-Z0-9\-\*\•]|$)", text, re.I)
        if ben_match:
            ben_summary = " ".join(ben_match.group(1).split())[:300]

        return req_summary, ben_summary


heuristic_extractor = HeuristicJobExtractor()
