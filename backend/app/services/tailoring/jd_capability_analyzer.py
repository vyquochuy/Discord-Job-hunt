import logging
import re
from typing import Dict, List, Set, Tuple
from rapidfuzz import fuzz

from app.models.job import Job
from app.schemas.tailoring_ir import JDCapabilityProfile, SkillRequirementType

logger = logging.getLogger("jd_capability_analyzer")

# Extended multi-dimensional capability domain dictionary
# Uses word-boundary matching to prevent single letters (like 'c') from matching substrings
DOMAIN_KEYWORD_TAXONOMY: Dict[str, Set[str]] = {
    "backend": {
        "backend", "back-end", "server", "microservice", "microservices", "api", "rest",
        "graphql", "fastapi", "django", "flask", "nodejs", "express", "hono", "golang",
        "java", "spring", "spring boot", "database", "sql", "postgresql", "mysql", "redis"
    },
    "systems": {
        "system", "systems", "c++", "c++17", "c++20", "embedded", "linux", "kernel",
        "driver", "memory management", "multithreading", "concurrency", "socket", "network protocol",
        "openssl", "wireshark", "ipc", "low-level", "performance optimization", "c language"
    },
    "security": {
        "security", "cyber", "cybersecurity", "infosec", "appsec", "cryptography", "crypto", "encryption",
        "e2ee", "pki", "x.509", "tls", "eap-tls", "auth", "authentication", "authorization",
        "vulnerability", "pentest", "soc", "anti-enumeration", "zero-knowledge", "keystore", "keychain"
    },
    "frontend": {
        "frontend", "front-end", "ui", "ux", "react", "reactjs", "nextjs", "vue", "angular",
        "html", "css", "tailwind", "tailwind css", "javascript", "typescript", "dom", "redux", "web"
    },
    "mobile": {
        "mobile", "ios", "android", "flutter", "dart", "react native", "swift", "kotlin",
        "mobile app", "keystore", "keychain"
    },
    "cloud": {
        "cloud", "devops", "aws", "gcp", "azure", "cloudflare", "cloudflare workers", "serverless",
        "docker", "kubernetes", "k8s", "ci/cd", "terraform", "edge", "sre", "infrastructure"
    },
    "database": {
        "database", "db", "sql", "relational", "sqlite", "d1", "postgres", "postgresql",
        "mysql", "redis", "kv", "schema", "orm", "sqlalchemy", "alembic", "data modeling"
    },
    "realtime": {
        "websocket", "websockets", "real-time", "realtime", "socket.io", "durable objects",
        "pubsub", "streaming", "messaging", "presence", "channel"
    },
    "data_ai": {
        "data", "data engineer", "ai", "ml", "machine learning", "deep learning", "pytorch", "tensorflow",
        "llm", "nlp", "rag", "pandas", "numpy", "pgvector", "vector db"
    },
    "automation": {
        "automation", "scraping", "bot", "discord.js", "playwright", "selenium", "pipeline", "etl"
    }
}

# Skill aliases and implicit foundations
IMPLICIT_FOUNDATIONS: Dict[str, Set[str]] = {
    "backend": {"git", "linux", "sql", "rest", "docker"},
    "systems": {"git", "linux", "c++", "debugging"},
    "security": {"git", "linux", "networking", "cryptography"},
    "frontend": {"git", "html", "css", "javascript", "typescript"},
    "mobile": {"git", "dart", "mobile"},
    "cloud": {"git", "linux", "docker", "ci/cd"},
}


def count_domain_hits(keywords: Set[str], text: str, word_set: Set[str]) -> int:
    """Đếm số từ khóa xuất hiện chính xác theo word-boundary (tránh match substring ngắn)."""
    hits = 0
    for kw in keywords:
        kw_low = kw.lower()
        if " " in kw_low or "-" in kw_low or "/" in kw_low or "." in kw_low:
            if re.search(r"\b" + re.escape(kw_low) + r"\b", text):
                hits += 1
        else:
            if kw_low in word_set:
                hits += 1
    return hits


class JDCapabilityAnalyzer:
    """
    Phân tích Job Description (JD) thành JD Capability Profile đa chiều:
    1. Trích xuất vector năng lực liên tục [0.0, 1.0] cho từng domain kỹ thuật.
    2. Xác định các bài toán cốt lõi (Core Problem Statements).
    3. Phân loại kỹ năng yêu cầu (REQUIRED, PREFERRED, IMPLICIT, IRRELEVANT).
    4. Xác định Role Family chủ đạo và danh sách primary domains (hỗ trợ hybrid).
    """

    @classmethod
    def analyze_job(cls, job: Job) -> JDCapabilityProfile:
        title = (getattr(job, "title", None) or "").strip()
        norm_title = (getattr(job, "normalized_title", None) or "").strip()
        desc = (getattr(job, "description", None) or "").strip()
        reqs = (getattr(job, "requirements_summary", None) or "").strip()

        combined_text = f"{title} {norm_title} {desc} {reqs}".lower()
        title_text = f"{title} {norm_title}".lower()

        combined_words = set(re.findall(r"[a-zA-Z0-9_\+\#\.\-]+", combined_text))
        title_words = set(re.findall(r"[a-zA-Z0-9_\+\#\.\-]+", title_text))

        # 1. Tính toán Capability Vector với word boundary
        capability_vector: Dict[str, float] = {}
        for domain, keywords in DOMAIN_KEYWORD_TAXONOMY.items():
            body_hits = count_domain_hits(keywords, combined_text, combined_words)
            title_hits = count_domain_hits(keywords, title_text, title_words)
            
            raw_score = (title_hits * 3.0) + (body_hits * 0.6)
            normalized = min(1.0, raw_score / 4.0)
            if normalized > 0.05:
                capability_vector[domain] = round(normalized, 3)
            else:
                capability_vector[domain] = 0.05

        # 2. Xác định Primary Domains
        sorted_domains = sorted(
            capability_vector.items(), key=lambda x: x[1], reverse=True
        )
        primary_domains = [d for d, s in sorted_domains if s >= 0.25]
        if not primary_domains and sorted_domains:
            primary_domains = [sorted_domains[0][0]]

        # 3. Trích xuất Core Problem Statements
        problem_statements: List[str] = []
        sentences = re.split(r"[\n\.\;\•\-\–]", f"{reqs} {desc}")
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) >= 15 and len(s_clean) <= 200:
                s_words = set(re.findall(r"[a-zA-Z0-9_\+\#\.\-]+", s_clean.lower()))
                if any(count_domain_hits(DOMAIN_KEYWORD_TAXONOMY[d], s_clean.lower(), s_words) > 0 for d in primary_domains):
                    problem_statements.append(s_clean)
            if len(problem_statements) >= 5:
                break
        
        if not problem_statements:
            problem_statements = [f"Developing robust software solutions for {title}."]

        # 4. Phân loại Kỹ năng (Safe inspect without triggering SQLAlchemy greenlet IO)
        skill_classifications: Dict[str, SkillRequirementType] = {}
        job_skills = []
        try:
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(job)
            if insp and "skills" not in insp.unloaded:
                skills_rel = job.skills
                if skills_rel:
                    for s in skills_rel:
                        if hasattr(s, "name"):
                            job_skills.append(s.name)
                        elif hasattr(s, "skill") and s.skill and hasattr(s.skill, "canonical_name"):
                            job_skills.append(s.skill.canonical_name)
        except Exception:
            pass

        all_skills_pool = set(job_skills)
        for kw_set in DOMAIN_KEYWORD_TAXONOMY.values():
            all_skills_pool.update(kw_set)

        for skill in all_skills_pool:
            s_low = skill.lower()
            if s_low in title_words or (reqs and s_low in reqs.lower()):
                skill_classifications[skill] = SkillRequirementType.REQUIRED
            elif s_low in combined_words or s_low in desc.lower():
                skill_classifications[skill] = SkillRequirementType.PREFERRED
            else:
                is_implicit = False
                for dom in primary_domains:
                    if s_low in IMPLICIT_FOUNDATIONS.get(dom, set()):
                        is_implicit = True
                        break
                if is_implicit:
                    skill_classifications[skill] = SkillRequirementType.IMPLICIT
                else:
                    skill_classifications[skill] = SkillRequirementType.IRRELEVANT

        # 5. Seniority Level
        seniority = "INTERN"
        if any(w in title_words for w in ["intern", "internship", "thực tập"]):
            seniority = "INTERN"
        elif any(w in title_words for w in ["fresher", "entry"]):
            seniority = "FRESHER"
        elif any(w in title_words for w in ["junior", "associate"]):
            seniority = "JUNIOR"
        elif any(w in title_words for w in ["senior", "lead", "principal"]):
            seniority = "SENIOR"
        elif any(w in title_words for w in ["mid", "developer", "engineer"]):
            seniority = "MID"

        return JDCapabilityProfile(
            capability_vector=capability_vector,
            primary_domains=primary_domains,
            skill_classifications=skill_classifications,
            core_problem_statements=problem_statements,
            seniority_level=seniority,
            normalized_role_title=title or "Software Engineer",
            confidence=round(max([s for s in capability_vector.values()] or [0.5]), 2),
        )

    @classmethod
    def identify_candidate_gaps(
        cls,
        candidate_canonical_techs: Set[str],
        candidate_capabilities: Set[str],
        profile: JDCapabilityProfile,
        job: Job,
    ) -> List[str]:
        """
        Phát hiện các khoảng trống (Candidate Gaps / Unsupported Requirements):
        Các kỹ năng / công nghệ cụ thể mà JD yêu cầu nhưng ứng viên hoàn toàn chưa có trong Evidence.
        Danh sách này sẽ được cấm đoán nghiêm ngặt (Forbidden Boundaries) để LLM không bịa đặt.
        """
        from app.services.tailoring.alias_registry import alias_registry

        GENERIC_DOMAINS = {
            "backend", "frontend", "database", "systems", "system", "security", "cloud",
            "realtime", "automation", "data_ai", "general", "mobile", "foundation",
            "education", "other", "soft_skills", "rest", "api", "apis", "software engineer",
            "server", "client", "service", "services", "platform", "platforms", "application",
            "applications", "architecture", "infrastructure", "serverless", "framework",
            "library", "network", "networks", "protocol", "protocols", "development",
            "engineering", "technology", "technologies", "data", "web", "intern", "internship",
            "developer", "engineer", "software", "code", "design", "performance", "optimization",
            "scale", "scalable", "storage", "memory", "testing", "management"
        }

        def is_tech_covered(canon: str) -> bool:
            if not canon:
                return True
            clean_c = canon.lower().strip().replace("_", " ")
            if clean_c in GENERIC_DOMAINS or canon.lower() in GENERIC_DOMAINS:
                return True
            if canon in candidate_canonical_techs:
                return True
            # Kiểm tra quan hệ prefix / substring (ví dụ 'cloudflare' được cover bởi 'cloudflare_workers')
            for cand_t in candidate_canonical_techs:
                if canon in cand_t or cand_t in canon:
                    return True
            return False

        unsupported: List[str] = []
        for skill_name, req_type in profile.skill_classifications.items():
            if req_type in (SkillRequirementType.REQUIRED, SkillRequirementType.PREFERRED):
                s_clean = skill_name.lower().strip().replace("_", " ")
                if s_clean in GENERIC_DOMAINS or s_clean in candidate_capabilities:
                    continue
                canon_id = alias_registry.get_canonical_id(skill_name)
                if not is_tech_covered(canon_id):
                    unsupported.append(skill_name)

        # Kiểm tra thêm từ raw job requirements (chỉ xét các tech cụ thể như Kubernetes, Kafka, Cassandra, gRPC, Golang)
        req_text = f"{getattr(job, 'requirements_summary', '') or ''} {getattr(job, 'description', '') or ''}".lower()
        extracted_techs = alias_registry.extract_technologies_from_text(req_text)
        for surface_token, canon_id in extracted_techs:
            if not is_tech_covered(canon_id):
                if surface_token.title() not in unsupported and surface_token not in unsupported:
                    unsupported.append(surface_token)

        # Giữ danh sách gọn gàng (unique)
        unique_gaps = list(dict.fromkeys(unsupported))
        return unique_gaps[:10]


jd_capability_analyzer = JDCapabilityAnalyzer()

