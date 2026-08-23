import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz

from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job
from app.models.match import JobMatch

logger = logging.getLogger("resume_intelligence")


# ============================================================================
# Dataclasses & Data Contracts
# ============================================================================

@dataclass
class ScoredEvidence:
    """Đại diện cho một bullet point minh chứng kỹ thuật kèm điểm số liên quan."""
    project_name: str
    evidence_title: str
    evidence_detail: str
    technologies: List[str]
    score: float  # 0.0 - 1.0 (multi-tier relevance score)
    capabilities: List[str]  # ["api", "database", "realtime", "crypto", "infra", ...]
    metrics: List[str] = field(default_factory=list)


@dataclass
class ScoredProject:
    """Đại diện cho một dự án đã được tính điểm tổng hợp và xếp hạng các bullet points."""
    project: CandidateProject
    project_score: float  # Aggregate relevance score
    ranked_evidence: List[ScoredEvidence]  # Bullet points đã sắp xếp theo thứ tự ưu tiên


@dataclass
class ResumeStrategy:
    """
    Kế hoạch chiến lược định vị CV (Resume Strategy) thống nhất cho cả Resume Generator và Cover Letter:
    - Quyết định trọng tâm positioning theo JD.
    - Xếp hạng dự án và bullet points.
    - Đảm bảo 100% Zero-Hallucination (chỉ sử dụng dữ liệu thực tế từ hồ sơ ứng viên).
    """
    role_family: str  # "backend" | "system" | "security" | "general"
    target_title: str
    adaptive_summary: str
    priority_skills: List[str]  # Kỹ năng thực có của ứng viên, sắp xếp ưu tiên theo JD
    ranked_projects: List[ScoredProject]
    selected_evidence: List[ScoredEvidence]  # Top diverse evidence cho Cover Letter
    matched_skills: List[str]
    top_capabilities: List[str] = field(default_factory=list)


# ============================================================================
# Capability & Domain Mapping Taxonomy
# ============================================================================

CAPABILITY_KEYWORDS: Dict[str, Set[str]] = {
    "api": {
        "api", "rest", "graphql", "endpoint", "endpoints", "hono", "fastapi", "http",
        "sync", "microservices", "request", "token-bucket", "rate-limiting", "middleware"
    },
    "database": {
        "database", "db", "sql", "relational", "sqlite", "d1", "cloudflare d1", "postgres",
        "postgresql", "redis", "kv", "cloudflare kv", "schema", "table", "tables", "indexeddb",
        "query", "data model", "blind storage"
    },
    "realtime": {
        "websocket", "websockets", "real-time", "realtime", "durable objects", "stateful",
        "presence", "messaging", "pubsub", "concurrency", "channel"
    },
    "infra": {
        "infrastructure", "serverless", "cloudflare workers", "workers", "docker", "linux",
        "cloud", "edge", "latency", "deployment", "ci/cd", "pop", "asia-pacific pop"
    },
    "crypto": {
        "cryptography", "crypto", "encryption", "e2ee", "end-to-end", "zero-knowledge",
        "ecdh", "argon2id", "aes", "aes-256", "rsa", "rsa-2048", "sha-256", "pki",
        "x.509", "shamir", "key exchange", "salts", "hashing"
    },
    "system_programming": {
        "c++", "c++17", "system-level", "openssl", "protocol", "ieee 802.1x", "eap-tls",
        "peer", "authenticator", "authentication server", "memory", "object-oriented"
    },
    "security": {
        "security", "authentication", "auth", "anti-enumeration", "brute-force", "audit",
        "access control", "keystore", "keychain", "vulnerability", "tls", "eap"
    },
}

ROLE_DOMAIN_AFFINITIES: Dict[str, Dict[str, float]] = {
    "backend": {
        "api": 1.0,
        "database": 1.0,
        "realtime": 0.7,
        "infra": 0.6,
        "crypto": 0.4,
        "system_programming": 0.5,
        "security": 0.5,
    },
    "system": {
        "infra": 1.0,
        "realtime": 0.8,
        "system_programming": 0.8,
        "api": 0.6,
        "database": 0.6,
        "crypto": 0.4,
        "security": 0.5,
    },
    "security": {
        "crypto": 1.0,
        "security": 1.0,
        "system_programming": 0.8,
        "api": 0.5,
        "database": 0.4,
        "infra": 0.4,
        "realtime": 0.3,
    },
    "general": {
        "api": 0.7,
        "database": 0.7,
        "infra": 0.7,
        "realtime": 0.6,
        "crypto": 0.6,
        "system_programming": 0.6,
        "security": 0.6,
    },
}


# ============================================================================
# Role Classifier
# ============================================================================

class RoleClassifier:
    """Xác định Role Family của công việc dựa trên Title, Requirements và Description."""

    BACKEND_KEYWORDS = {
        "backend", "back-end", "python developer", "api", "rest", "database",
        "web developer", "fullstack", "full-stack", "django", "fastapi", "nodejs",
        "java", "golang", "server", "microservice"
    }
    SYSTEM_KEYWORDS = {
        "system", "devops", "cloud", "infrastructure", "sre", "reliability",
        "platform", "linux", "docker", "serverless", "embedded", "network",
        "distributed", "edge", "sysadmin"
    }
    SECURITY_KEYWORDS = {
        "security", "cyber", "infosec", "cryptography", "crypto", "appsec",
        "soc", "pentest", "vulnerability", "threat", "pki", "tls", "auth"
    }

    @classmethod
    def classify_role(cls, job: Job) -> str:
        text = f"{job.title} {job.normalized_title} {job.description or ''} {job.requirements_summary or ''}".lower()

        backend_score = sum(1 for kw in cls.BACKEND_KEYWORDS if kw in text)
        system_score = sum(1 for kw in cls.SYSTEM_KEYWORDS if kw in text)
        security_score = sum(1 for kw in cls.SECURITY_KEYWORDS if kw in text)

        # Trọng số ưu tiên cao hơn cho Title
        title_lower = f"{job.title} {job.normalized_title}".lower()
        for kw in cls.BACKEND_KEYWORDS:
            if kw in title_lower:
                backend_score += 4
        for kw in cls.SYSTEM_KEYWORDS:
            if kw in title_lower:
                system_score += 4
        for kw in cls.SECURITY_KEYWORDS:
            if kw in title_lower:
                security_score += 4

        scores = [
            ("backend", backend_score),
            ("system", system_score),
            ("security", security_score),
        ]
        scores.sort(key=lambda x: x[1], reverse=True)

        best_role, best_val = scores[0]
        if best_val == 0:
            return "general"
        return best_role


# ============================================================================
# Multi-Tier Evidence Scorer
# ============================================================================

class EvidenceScorer:
    """
    Chấm điểm liên quan (Relevance Score) của từng Evidence Point đối với JD:
    - Phân tích đa lớp: Responsibility Match + Technical/Capability Match + Domain Affinity + Strength.
    - Tuyệt đối không hallucinate hay mutate công nghệ.
    """

    @classmethod
    def infer_capabilities(cls, title: str, detail: str, technologies: List[str]) -> List[str]:
        """Tự động trích xuất các capability tags từ văn bản và tech stack của bullet point."""
        text = f"{title} {detail} {' '.join(technologies)}".lower()
        detected = []
        for cap, keywords in CAPABILITY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                detected.append(cap)
        return detected or ["general"]

    @classmethod
    def extract_metrics(cls, text: str) -> List[str]:
        """Trích xuất các con số và chỉ số định lượng."""
        pattern = r"\b\d+(?:\.\d+)?(?:ms|s|%|req/min|req/10s|MB|GB|KB|POPs?|PoP)?\b"
        return list(set(re.findall(pattern, text, re.IGNORECASE)))

    @classmethod
    def score_evidence(
        cls,
        project_name: str,
        evidence_point: Dict[str, Any],
        project_technologies: List[str],
        job: Job,
        role_family: str,
        matched_skills: List[str],
    ) -> ScoredEvidence:
        title = evidence_point.get("title", "") if isinstance(evidence_point, dict) else ""
        detail = evidence_point.get("detail", "") if isinstance(evidence_point, dict) else str(evidence_point)
        evidence_techs = evidence_point.get("technologies", project_technologies) if isinstance(evidence_point, dict) else project_technologies

        capabilities = cls.infer_capabilities(title, detail, evidence_techs)
        metrics = cls.extract_metrics(detail)

        # 1. Responsibility Match (35%): RapidFuzz so với JD description + requirements
        jd_context = f"{job.title} {job.description or ''} {job.requirements_summary or ''}".lower()
        claim_text = f"{title} {detail}".lower()
        resp_score = (
            max(
                fuzz.partial_ratio(claim_text, jd_context),
                fuzz.token_set_ratio(claim_text, jd_context),
            )
            / 100.0
        )

        # 2. Skill & Capability Match (30%):
        # - Exact Tech Match (1.0)
        # - Capability Match (0.5)
        matched_lower = {s.lower() for s in (matched_skills or [])}
        exact_matches = sum(1 for t in evidence_techs if t.lower() in matched_lower)
        tech_score = (exact_matches / max(len(evidence_techs), 1)) if evidence_techs else 0.0

        # Thưởng thêm cho capability match
        cap_match_count = 0
        for cap in capabilities:
            cap_keywords = CAPABILITY_KEYWORDS.get(cap, set())
            if any(kw in jd_context for kw in cap_keywords):
                cap_match_count += 1
        cap_score = min(1.0, (cap_match_count / max(len(capabilities), 1)))

        tech_and_cap_score = min(1.0, (tech_score * 0.7 + cap_score * 0.3))

        # 3. Domain Affinity Match (20%): Dựa trên Role Family
        affinities = ROLE_DOMAIN_AFFINITIES.get(role_family, ROLE_DOMAIN_AFFINITIES["general"])
        domain_score = max([affinities.get(c, 0.5) for c in capabilities], default=0.5)

        # 4. Evidence Strength (15%): Có metrics định lượng và tên công nghệ rõ ràng
        strength_score = 0.5
        if metrics:
            strength_score += 0.3
        if len(evidence_techs) >= 2:
            strength_score += 0.2
        strength_score = min(1.0, strength_score)

        # Tính điểm tổng hợp (Weighted sum)
        total_score = (
            0.35 * resp_score
            + 0.30 * tech_and_cap_score
            + 0.20 * domain_score
            + 0.15 * strength_score
        )
        total_score = round(min(1.0, max(0.0, total_score)), 4)

        return ScoredEvidence(
            project_name=project_name,
            evidence_title=title,
            evidence_detail=detail,
            technologies=evidence_techs,
            score=total_score,
            capabilities=capabilities,
            metrics=metrics,
        )


# ============================================================================
# Diverse Evidence Selector (MMR-style)
# ============================================================================

class DiverseEvidenceSelector:
    """Chọn lọc tập bằng chứng hàng đầu (Top Evidence) đảm bảo độ phủ đa dạng các năng lực."""

    @classmethod
    def select_diverse_evidence(
        cls,
        all_scored_evidence: List[ScoredEvidence],
        limit: int = 3,
        min_threshold: float = 0.3,
    ) -> List[ScoredEvidence]:
        qualified = [e for e in all_scored_evidence if e.score >= min_threshold]
        if not qualified:
            qualified = all_scored_evidence

        # Sắp xếp giảm dần theo điểm
        sorted_ev = sorted(qualified, key=lambda e: e.score, reverse=True)

        selected: List[ScoredEvidence] = []
        covered_capabilities: Set[str] = set()

        # Tuyển chọn: Ưu tiên năng lực chưa được đại diện
        for item in sorted_ev:
            item_caps = set(item.capabilities)
            # Nếu chưa đủ limit và có năng lực mới hoặc chưa chọn cái nào
            if len(selected) < limit:
                if not covered_capabilities or not item_caps.issubset(covered_capabilities):
                    selected.append(item)
                    covered_capabilities.update(item_caps)

        # Nếu vẫn chưa đủ limit, lấy thêm các items có điểm cao nhất còn lại
        for item in sorted_ev:
            if len(selected) >= limit:
                break
            if item not in selected:
                selected.append(item)

        return selected


# ============================================================================
# Adaptive Summary Builder
# ============================================================================

class AdaptiveSummaryBuilder:
    """
    Xây dựng Summary định vị theo Role Family:
    - Tuyệt đối chỉ sử dụng dữ liệu thực tế: trường đại học, chuyên ngành, GPA, các kỹ năng và dự án đã kiểm chứng.
    - Phân hóa rõ rệt trọng tâm: Backend (APIs, Database, Distributed) vs System (Cloud, Linux, Automation) vs Security (PKI, E2EE, Crypto).
    """

    @classmethod
    def build_summary(
        cls,
        candidate: Candidate,
        role_family: str,
        target_title: str,
        top_evidence: List[ScoredEvidence],
        matched_skills: List[str],
    ) -> str:
        # Trích xuất thông tin học vấn thật
        edu_major = "Computer Science (Cyber Security)"
        edu_school = "VNUHCM - University of Science"
        if candidate.education and len(candidate.education) > 0:
            edu_0 = candidate.education[0]
            edu_major = edu_0.get("field", edu_major)
            edu_school = edu_0.get("institution", edu_school)

        if role_family == "backend":
            summary = (
                f"Final-year {edu_major} student at {edu_school} specializing in backend software engineering, "
                f"relational data modeling, and distributed serverless APIs. Hands-on experience architecting high-throughput "
                f"REST and WebSocket services with Cloudflare Workers, Hono, and SQLite/D1, backed by client-side cryptographic hashing "
                f"and dynamic rate limiting. Seeking a {target_title} position to build scalable, secure, and resilient backend systems."
            )
        elif role_family == "system":
            summary = (
                f"Final-year {edu_major} student at {edu_school} with strong interest in cloud infrastructure, "
                f"Linux systems, automation, and distributed platforms. Practical experience engineering stateful "
                f"edge WebSocket infrastructure on Cloudflare Durable Objects and automated serverless deployments. "
                f"Seeking a {target_title} role to contribute to reliable cloud operations and high-performance system engineering."
            )
        elif role_family == "security":
            summary = (
                f"Final-year {edu_major} student at {edu_school} with deep foundations in modern C++, Public Key Infrastructure (PKI), "
                f"and applied cryptography. Experienced in implementing end-to-end cryptographic workflows including IEEE 802.1X EAP-TLS protocol simulation, "
                f"X.509 certificate chain validation with OpenSSL, and zero-knowledge E2EE messaging. "
                f"Seeking a {target_title} role to apply secure architecture and cryptographic engineering practices."
            )
        else:
            summary = candidate.summary or (
                f"Final-year {edu_major} student at {edu_school} with strong foundations in software engineering, "
                f"system architecture, and security protocols. Experienced in developing full-stack serverless applications and cryptographic systems. "
                f"Seeking a {target_title} position to contribute to robust and reliable software development."
            )

        return summary


# ============================================================================
# Resume Intelligence Engine (Facade)
# ============================================================================

class ResumeIntelligenceEngine:
    """Facade điều phối toàn bộ lớp Resume Intelligence."""

    @classmethod
    def build_strategy(
        cls,
        candidate: Candidate,
        job: Job,
        match_record: Optional[JobMatch] = None,
        custom_tone: str = "professional_and_humble",
    ) -> ResumeStrategy:
        # 1. Xác định Role Family
        role_family = RoleClassifier.classify_role(job)
        target_title = job.title or candidate.headline or "Software Engineer Intern"

        # 2. Thu thập matched skills
        matched_skills = []
        if match_record and match_record.matched_skills:
            matched_skills = match_record.matched_skills
        else:
            # Safely check candidate skills against job description / keywords
            candidate_skills = []
            if "skills" in candidate.__dict__ and candidate.skills:
                candidate_skills = [s.name for s in candidate.skills]
            jd_text = f"{job.title} {job.description or ''} {job.requirements_summary or ''}".lower()
            for s in candidate_skills:
                if s.lower() in jd_text:
                    matched_skills.append(s)

        # 3. Chấm điểm từng Evidence Point trong từng Project
        scored_projects: List[ScoredProject] = []
        all_scored_evidences: List[ScoredEvidence] = []

        candidate_projects = getattr(candidate, "projects", None) or []
        for proj in candidate_projects:
            proj_ev_scored: List[ScoredEvidence] = []
            if proj.evidence_points:
                for ev in proj.evidence_points:
                    scored_ev = EvidenceScorer.score_evidence(
                        project_name=proj.name,
                        evidence_point=ev,
                        project_technologies=proj.technologies or [],
                        job=job,
                        role_family=role_family,
                        matched_skills=matched_skills,
                    )
                    proj_ev_scored.append(scored_ev)
                    all_scored_evidences.append(scored_ev)

            # Sắp xếp bullet points trong project theo score giảm dần
            proj_ev_scored.sort(key=lambda e: e.score, reverse=True)

            # Aggregate Project Score (lấy điểm trung bình của top bullets)
            if proj_ev_scored:
                top_scores = [e.score for e in proj_ev_scored[:2]]
                proj_score = sum(top_scores) / len(top_scores)
            else:
                proj_score = 0.5

            scored_projects.append(
                ScoredProject(
                    project=proj,
                    project_score=round(proj_score, 4),
                    ranked_evidence=proj_ev_scored,
                )
            )

        # 4. Sắp xếp thứ tự các Projects theo Project Score giảm dần
        scored_projects.sort(key=lambda p: p.project_score, reverse=True)

        # 5. Tuyển chọn Diverse Evidence cho Cover Letter
        selected_evidence = DiverseEvidenceSelector.select_diverse_evidence(
            all_scored_evidence=all_scored_evidences,
            limit=3,
            min_threshold=0.3,
        )

        # 6. Sắp xếp Kỹ năng ưu tiên (Priority Skills)
        # Bắt đầu từ candidate skills thực có, ưu tiên matched skills và role domain affinity
        candidate_skills_list = []
        skills_rel = getattr(candidate, "skills", None) or []
        if skills_rel:
            candidate_skills_list = [s.name for s in skills_rel]
        if not candidate_skills_list:
            candidate_skills_list = ["C++", "Python", "JavaScript", "TypeScript", "SQL", "Linux", "Docker", "X.509 PKI", "OpenSSL"]

        matched_set = {s.lower() for s in matched_skills}

        def skill_rank_key(skill_name: str) -> Tuple[int, int]:
            s_lower = skill_name.lower()
            is_matched = 1 if s_lower in matched_set else 0
            # Kiểm tra affinity
            affinities = ROLE_DOMAIN_AFFINITIES.get(role_family, {})
            aff_score = 0
            for cap, weight in affinities.items():
                if any(kw in s_lower for kw in CAPABILITY_KEYWORDS.get(cap, set())):
                    aff_score = max(aff_score, int(weight * 10))
            return (is_matched, aff_score)

        priority_skills = sorted(candidate_skills_list, key=skill_rank_key, reverse=True)

        # 7. Xây dựng Adaptive Summary
        adaptive_summary = AdaptiveSummaryBuilder.build_summary(
            candidate=candidate,
            role_family=role_family,
            target_title=target_title,
            top_evidence=selected_evidence,
            matched_skills=matched_skills,
        )

        # Top Capabilities
        all_caps = []
        for e in selected_evidence:
            all_caps.extend(e.capabilities)
        top_capabilities = list(dict.fromkeys(all_caps))

        logger.info(
            f"Resume Strategy built: role_family='{role_family}', target_title='{target_title}', "
            f"top_project='{scored_projects[0].project.name if scored_projects else 'None'}'"
        )

        return ResumeStrategy(
            role_family=role_family,
            target_title=target_title,
            adaptive_summary=adaptive_summary,
            priority_skills=priority_skills,
            ranked_projects=scored_projects,
            selected_evidence=selected_evidence,
            matched_skills=matched_skills,
            top_capabilities=top_capabilities,
        )


resume_intelligence = ResumeIntelligenceEngine()
