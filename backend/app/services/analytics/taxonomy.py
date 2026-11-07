"""
Deterministic market taxonomy.

Everything in this module is derived from stored job fields — no LLM, no
external taxonomy service. Derived values are explicitly labelled as derived
in the API responses so the UI never presents them as employer-declared facts.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple


# ---------------------------------------------------------------------------
# Job category (derived from normalized_title)
# ---------------------------------------------------------------------------
# Order matters: the first matching rule wins. Specific families are checked
# before generic "software engineer" so that e.g. "Embedded Software Engineer"
# is not swallowed by the generic bucket.
CATEGORY_RULES: List[Tuple[str, List[Pattern[str]]]] = [
    (
        "ai_ml",
        [
            re.compile(r"\bai\b"),
            re.compile(r"\bml\b"),
            re.compile(r"machine learning"),
            re.compile(r"deep learning"),
            re.compile(r"data scien"),
            re.compile(r"\bnlp\b"),
            re.compile(r"computer vision"),
            re.compile(r"\bllm\b"),
            re.compile(r"generative ai"),
            re.compile(r"artificial intelligence"),
            re.compile(r"trí tuệ nhân tạo"),
        ],
    ),
    (
        "data",
        [
            re.compile(r"data engineer"),
            re.compile(r"data analyst"),
            re.compile(r"data architect"),
            re.compile(r"big data"),
            re.compile(r"business intelligence"),
            re.compile(r"\bbi\b"),
            re.compile(r"\betl\b"),
            re.compile(r"database administrator"),
            re.compile(r"\bdba\b"),
            re.compile(r"analytics engineer"),
            re.compile(r"data platform"),
        ],
    ),
    (
        "security",
        [
            re.compile(r"security"),
            re.compile(r"cyber"),
            re.compile(r"penetration"),
            re.compile(r"\bsoc\b"),
            re.compile(r"infosec"),
            re.compile(r"bảo mật"),
            re.compile(r"devsecops"),
        ],
    ),
    (
        "devops",
        [
            re.compile(r"devops"),
            re.compile(r"site reliability"),
            re.compile(r"\bsre\b"),
            re.compile(r"platform engineer"),
            re.compile(r"cloud engineer"),
            re.compile(r"infrastructure"),
            re.compile(r"system administrator"),
            re.compile(r"sysadmin"),
            re.compile(r"kubernetes"),
        ],
    ),
    (
        "qa",
        [
            re.compile(r"\bqa\b"),
            re.compile(r"\bqc\b"),
            re.compile(r"quality assurance"),
            re.compile(r"test engineer"),
            re.compile(r"tester"),
            re.compile(r"automation test"),
            re.compile(r"kiểm thử"),
            re.compile(r"software test"),
        ],
    ),
    (
        "mobile",
        [
            re.compile(r"\bios\b"),
            re.compile(r"android"),
            re.compile(r"mobile"),
            re.compile(r"flutter"),
            re.compile(r"react native"),
            re.compile(r"swift"),
            re.compile(r"kotlin"),
        ],
    ),
    (
        "fullstack",
        [
            re.compile(r"fullstack"),
            re.compile(r"full-stack"),
            re.compile(r"full stack"),
        ],
    ),
    (
        "frontend",
        [
            re.compile(r"frontend"),
            re.compile(r"front-end"),
            re.compile(r"front end"),
            re.compile(r"react developer"),
            re.compile(r"\bvue"),
            re.compile(r"angular"),
            re.compile(r"ui engineer"),
            re.compile(r"web developer"),
            re.compile(r"javascript developer"),
            re.compile(r"typescript developer"),
        ],
    ),
    (
        "backend",
        [
            re.compile(r"backend"),
            re.compile(r"back-end"),
            re.compile(r"back end"),
            re.compile(r"\bjava\b"),
            re.compile(r"\bpython\b"),
            re.compile(r"\bnode"),
            re.compile(r"\bphp\b"),
            re.compile(r"\bgolang\b"),
            re.compile(r"\bgo developer"),
            re.compile(r"\bc#"),
            re.compile(r"\.net"),
            re.compile(r"\bruby"),
            re.compile(r"\bscala\b"),
            re.compile(r"\brust\b"),
            re.compile(r"\bapi\b"),
        ],
    ),
    (
        "embedded",
        [
            re.compile(r"embedded"),
            re.compile(r"firmware"),
            re.compile(r"\biot\b"),
            re.compile(r"\bfpga\b"),
            re.compile(r"hardware"),
            re.compile(r"nhúng"),
            re.compile(r"automotive"),
        ],
    ),
    (
        "business_analysis",
        [
            re.compile(r"business analyst"),
            re.compile(r"\bba\b"),
            re.compile(r"business analysis"),
            re.compile(r"phân tích nghiệp vụ"),
            re.compile(r"product analyst"),
            re.compile(r"system analyst"),
        ],
    ),
    (
        "product",
        [
            re.compile(r"product owner"),
            re.compile(r"product manager"),
            re.compile(r"product designer"),
            re.compile(r"\bpo\b"),
            re.compile(r"quản lý sản phẩm"),
        ],
    ),
    (
        "project_management",
        [
            re.compile(r"project manager"),
            re.compile(r"program manager"),
            re.compile(r"scrum master"),
            re.compile(r"delivery manager"),
            re.compile(r"quản lý dự án"),
            re.compile(r"\bpm\b"),
        ],
    ),
    (
        "design",
        [
            re.compile(r"\bui\b"),
            re.compile(r"\bux\b"),
            re.compile(r"designer"),
            re.compile(r"graphic"),
            re.compile(r"thiết kế"),
        ],
    ),
    (
        "it_support",
        [
            re.compile(r"it support"),
            re.compile(r"helpdesk"),
            re.compile(r"help desk"),
            re.compile(r"technical support"),
            re.compile(r"hỗ trợ kỹ thuật"),
            re.compile(r"nhân viên it"),
        ],
    ),
    (
        "bridge_engineering",
        [
            re.compile(r"\bbrse\b"),
            re.compile(r"\bcomtor\b"),
            re.compile(r"bridge engineer"),
            re.compile(r"kỹ sư cầu nối"),
        ],
    ),
    (
        "management",
        [
            re.compile(r"director"),
            re.compile(r"\bcto\b"),
            re.compile(r"\bcio\b"),
            re.compile(r"head of"),
            re.compile(r"engineering manager"),
            re.compile(r"giám đốc"),
        ],
    ),
    (
        "software_engineering",
        [
            re.compile(r"software engineer"),
            re.compile(r"software developer"),
            re.compile(r"programmer"),
            re.compile(r"lập trình viên"),
            re.compile(r"architect"),
            re.compile(r"developer"),
            re.compile(r"engineer"),
        ],
    ),
]

CATEGORY_LABELS: Dict[str, str] = {
    "ai_ml": "AI / Machine Learning",
    "data": "Dữ liệu & Phân tích",
    "security": "An ninh mạng",
    "devops": "DevOps & Hạ tầng",
    "qa": "QA / Kiểm thử",
    "mobile": "Mobile",
    "fullstack": "Fullstack",
    "frontend": "Frontend",
    "backend": "Backend",
    "embedded": "Embedded / IoT",
    "business_analysis": "Business Analysis",
    "product": "Product",
    "project_management": "Quản lý dự án",
    "design": "Thiết kế UI/UX",
    "it_support": "IT Support",
    "bridge_engineering": "BrSE / Cầu nối",
    "management": "Quản lý / Lãnh đạo",
    "software_engineering": "Kỹ thuật phần mềm",
    "other": "Khác",
}

CATEGORY_ORDER: List[str] = list(CATEGORY_LABELS.keys())


def derive_category(title: Optional[str]) -> str:
    """Map a normalized job title to a deterministic category key."""
    text = (title or "").strip().lower()
    if not text:
        return "other"
    # Explicit role names beat incidental technology keywords (e.g. BrSE Java,
    # embedded Rust, project manager Python).
    specific = {"embedded", "business_analysis", "product", "project_management",
                "it_support", "bridge_engineering", "management"}
    for category, patterns in sorted(CATEGORY_RULES, key=lambda rule: rule[0] not in specific):
        for pattern in patterns:
            if pattern.search(text):
                return category
    return "other"


def category_label(category: Optional[str]) -> str:
    if not category:
        return CATEGORY_LABELS["other"]
    return CATEGORY_LABELS.get(category, category)


# ---------------------------------------------------------------------------
# Seniority labels
# ---------------------------------------------------------------------------
LEVEL_LABELS: Dict[str, str] = {
    "INTERN": "Thực tập",
    "FRESHER": "Fresher",
    "JUNIOR": "Junior",
    "MID": "Middle",
    "SENIOR": "Senior",
    "LEAD": "Lead",
    "MANAGER": "Manager",
    "UNKNOWN": "Chưa xác định",
}

LEVEL_ORDER: List[str] = [
    "INTERN",
    "FRESHER",
    "JUNIOR",
    "MID",
    "SENIOR",
    "LEAD",
    "MANAGER",
    "UNKNOWN",
]


def level_label(level: Optional[str]) -> str:
    if not level:
        return LEVEL_LABELS["UNKNOWN"]
    return LEVEL_LABELS.get(level.upper(), level)


# ---------------------------------------------------------------------------
# Work mode labels
# ---------------------------------------------------------------------------
WORK_MODE_LABELS: Dict[str, str] = {
    "ONSITE": "Tại văn phòng",
    "HYBRID": "Hybrid",
    "REMOTE": "Remote",
}


def work_mode_label(mode: Optional[str]) -> str:
    if not mode:
        return "Không xác định"
    return WORK_MODE_LABELS.get(mode.upper(), mode)


# ---------------------------------------------------------------------------
# Region (derived from normalized_location)
# ---------------------------------------------------------------------------
REGION_LABELS: Dict[str, str] = {
    "hcm": "TP. Hồ Chí Minh",
    "hanoi": "Hà Nội",
    "danang": "Đà Nẵng",
    "vietnam": "Toàn quốc",
    "other_vn": "Tỉnh / thành khác",
    "international": "Quốc tế",
    "remote": "Remote",
    "unknown": "Không xác định",
}

REGION_ORDER: List[str] = [
    "hcm",
    "hanoi",
    "danang",
    "vietnam",
    "other_vn",
    "international",
    "remote",
    "unknown",
]

_HCM_TOKENS = ("ho chi minh", "hồ chí minh", "hcm", "sai gon", "sài gòn", "tp.hcm")
_HANOI_TOKENS = ("hanoi", "hà nội", "ha noi")
_DANANG_TOKENS = ("da nang", "đà nẵng", "danang")
_REMOTE_TOKENS = ("remote", "worldwide", "từ xa", "làm việc tại nhà", "wfh")
_INTERNATIONAL_TOKENS = (
    "quốc tế",
    "international",
    "japan",
    "nhật",
    "singapore",
    "korea",
    "hàn quốc",
    "united states",
    "usa",
    "europe",
    "australia",
    "canada",
    "germany",
    "taiwan",
    "đài loan",
)


def derive_region(location: Optional[str]) -> str:
    """Map a normalized location string to a coarse region key."""
    text = (location or "").strip().lower()
    if not text:
        return "unknown"
    if any(token in text for token in _REMOTE_TOKENS):
        return "remote"
    if any(token in text for token in _HCM_TOKENS):
        return "hcm"
    if any(token in text for token in _HANOI_TOKENS):
        return "hanoi"
    if any(token in text for token in _DANANG_TOKENS):
        return "danang"
    if "vietnam" in text or "việt nam" in text:
        return "vietnam"
    if any(token in text for token in _INTERNATIONAL_TOKENS):
        return "international"
    return "other_vn"


def region_label(region: Optional[str]) -> str:
    if not region:
        return REGION_LABELS["unknown"]
    return REGION_LABELS.get(region, region)


# ---------------------------------------------------------------------------
# Role family (title with seniority noise removed)
# ---------------------------------------------------------------------------
_ROLE_NOISE = re.compile(
    r"\b(senior|sr\.?|junior|jr\.?|mid|middle|intermediate|lead|principal|staff|"
    r"intern|internship|fresher|thực tập sinh|trưởng nhóm|chuyên viên cao cấp|"
    r"urgent|hot|remote|hybrid|onsite)\b",
    re.IGNORECASE,
)
_ROLE_BRACKETS = re.compile(r"[\(\[\{].*?[\)\]\}]")


def derive_role_family(title: Optional[str]) -> str:
    """Collapse seniority/noise tokens so "Senior Backend Developer" and
    "Backend Developer" share one family. Purely lexical, fully deterministic."""
    text = _ROLE_BRACKETS.sub(" ", (title or "").lower())
    text = _ROLE_NOISE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:–—")
    return text or (title or "").strip() or "Không xác định"


def normalize_company_key(company: Optional[str]) -> str:
    """Company names are already normalized by the ingestion pipeline; this is
    only a defensive trim so grouping keys stay stable across sources."""
    return (company or "").strip()
