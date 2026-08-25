import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz

from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job
from app.models.match import JobMatch
from app.schemas.tailoring_ir import (
    FactNode,
    JDCapabilityProfile,
    LayoutBudget,
    MetricFact,
    ResumeStrategy,
    ScoredEvidenceItem,
    ScoredProjectCandidate,
    SkillRequirementType,
)
from app.services.tailoring.fact_graph import CAPABILITY_TAXONOMY, fact_graph_builder
from app.services.tailoring.jd_capability_analyzer import (
    DOMAIN_KEYWORD_TAXONOMY,
    jd_capability_analyzer,
)

logger = logging.getLogger("resume_intelligence")

# Backward compatibility alias
ScoredEvidence = ScoredEvidenceItem
ScoredProject = ScoredProjectCandidate

CAP_TO_DOMAIN_MAP: Dict[str, str] = {
    "api": "backend",
    "database": "database",
    "backend": "backend",
    "realtime": "realtime",
    "infra": "cloud",
    "cloud": "cloud",
    "crypto": "security",
    "security": "security",
    "system_programming": "systems",
    "systems": "systems",
    "mobile": "mobile",
    "frontend": "frontend",
    "automation": "automation",
    "data_ai": "data_ai",
}


def normalize_target_title_to_english(raw_title: Optional[str], role_family: str = "general") -> str:
    """
    Chuẩn hóa chức danh ứng tuyển (target_role / target_title) sang tiếng Anh chuẩn,
    bảo đảm CV may đo và Cover Letter luôn viết hoàn toàn bằng tiếng Anh.
    Ví dụ:
    - 'Thực Tập Sinh Phát Triển Phần Mềm' -> 'Software Engineer Intern'
    - 'Thực tập sinh Backend' -> 'Backend Developer Intern'
    - 'Lập trình viên C++ Thực tập' -> 'C++ Software Engineer Intern'
    - 'Thực tập sinh An toàn thông tin' -> 'Cyber Security Intern'
    - 'Thực tập sinh DevOps' -> 'DevOps Engineer Intern'
    """
    if not raw_title:
        fallback_map = {
            "backend": "Backend Developer Intern",
            "system": "System & Infrastructure Intern",
            "systems": "System & Infrastructure Intern",
            "security": "Cyber Security & Systems Intern",
            "frontend": "Frontend Developer Intern",
            "mobile": "Mobile App Developer Intern",
            "cloud": "Cloud / DevOps Engineer Intern",
            "devops": "DevOps Engineer Intern",
        }
        return fallback_map.get(role_family.lower(), "Software Engineer Intern")

    title = raw_title.strip()
    title_lower = title.lower()

    # Kiểm tra xem có chứa tiếng Việt có dấu hoặc cụm từ tiếng Việt không
    has_vietnamese = bool(re.search(
        r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
        title_lower
    ) or any(w in title_lower for w in ["thực tập", "thuc tap", "sinh viên", "lập trình viên", "chuyên viên", "kỹ sư", "nhân viên"]))

    if not has_vietnamese:
        return title

    is_intern = any(w in title_lower for w in ["thực tập", "thuc tap", "intern", "trainee", "sinh viên", "fresher"])

    if any(w in title_lower for w in ["an toàn thông tin", "bảo mật", "cyber", "security", "an ninh mạng", "pentest", "soc"]):
        return "Cyber Security Intern" if is_intern else "Security Engineer"
    elif any(w in title_lower for w in ["backend", "back-end", "máy chủ", "server"]):
        return "Backend Developer Intern" if is_intern else "Backend Developer"
    elif any(w in title_lower for w in ["frontend", "front-end", "giao diện"]):
        return "Frontend Developer Intern" if is_intern else "Frontend Developer"
    elif any(w in title_lower for w in ["fullstack", "full-stack"]):
        return "Full-Stack Developer Intern" if is_intern else "Full-Stack Developer"
    elif any(w in title_lower for w in ["hệ thống", "system", "c++", "embedded", "nhúng", "ha tang", "hạ tầng"]):
        return "System & Infrastructure Intern" if is_intern else "System Engineer"
    elif any(w in title_lower for w in ["devops", "cloud", "sre", "điện toán đám mây"]):
        return "DevOps Engineer Intern" if is_intern else "DevOps Engineer"
    elif any(w in title_lower for w in ["mobile", "di động", "flutter", "android", "ios"]):
        return "Mobile App Developer Intern" if is_intern else "Mobile Developer"
    elif any(w in title_lower for w in ["ai", "trí tuệ nhân tạo", "machine learning", "học máy", "data"]):
        return "AI / Machine Learning Intern" if is_intern else "AI Engineer"
    elif any(w in title_lower for w in ["phát triển phần mềm", "phần mềm", "software", "lập trình viên"]):
        return "Software Engineer Intern" if is_intern else "Software Engineer"

    fallback_map = {
        "backend": "Backend Developer Intern" if is_intern else "Backend Developer",
        "system": "System Engineer Intern" if is_intern else "System Engineer",
        "systems": "System Engineer Intern" if is_intern else "System Engineer",
        "security": "Cyber Security Intern" if is_intern else "Security Engineer",
        "frontend": "Frontend Developer Intern" if is_intern else "Frontend Developer",
        "mobile": "Mobile Developer Intern" if is_intern else "Mobile Developer",
    }
    return fallback_map.get(role_family.lower(), "Software Engineer Intern" if is_intern else "Software Engineer")


# ============================================================================
# Role Classifier (Kept for compatibility & primary categorization)
# ============================================================================

class RoleClassifier:
    """Xác định Role Family chủ đạo của công việc dựa trên Title, Requirements và Description."""

    BACKEND_KEYWORDS = {
        "backend", "back-end", "python developer", "api", "rest", "database",
        "web developer", "fullstack", "full-stack", "django", "fastapi", "nodejs",
        "java", "golang", "server", "microservice"
    }
    SYSTEM_KEYWORDS = {
        "system", "systems", "devops", "cloud", "infrastructure", "sre", "reliability",
        "platform", "linux", "docker", "serverless", "embedded", "network",
        "distributed", "edge", "sysadmin"
    }
    SECURITY_KEYWORDS = {
        "security", "cyber", "infosec", "cryptography", "crypto", "appsec",
        "soc", "pentest", "vulnerability", "threat", "pki", "tls", "auth"
    }

    @classmethod
    def classify_role(cls, job: Job) -> str:
        text = f"{getattr(job, 'title', '')} {getattr(job, 'normalized_title', '')} {getattr(job, 'description', '') or ''} {getattr(job, 'requirements_summary', '') or ''}".lower()
        title_lower = f"{getattr(job, 'title', '')} {getattr(job, 'normalized_title', '')}".lower()

        backend_score = sum(1 for kw in cls.BACKEND_KEYWORDS if kw in text)
        system_score = sum(1 for kw in cls.SYSTEM_KEYWORDS if kw in text)
        security_score = sum(1 for kw in cls.SECURITY_KEYWORDS if kw in text)

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
# Multi-Signal Evidence Scorer (General & Penalty-Aware)
# ============================================================================

class EvidenceScorer:
    """
    Chấm điểm đa tín hiệu (Multi-Signal Evidence Scoring) cho từng bullet point:
    1. Responsibility Fit (30%): So khớp với core problem statements của JD.
    2. Capability Alignment (25%): Tích vô hướng với vector năng lực đa chiều của JD.
    3. Technology Precision Fit (20%): Trọng số Required (1.0), Preferred (0.7), Implicit (0.4).
    4. Evidence & Metric Strength (15%): Có chỉ số định lượng cụ thể và tech count.
    5. JD Importance Weight (10%): Nhân hệ số ưu tiên bài toán cốt lõi.
    6. Negative Irrelevance Penalty (-15%): Phạt nếu công nghệ hoàn toàn lệch pha với JD.
    """

    @classmethod
    def infer_capabilities(cls, title: str, detail: str, technologies: List[str]) -> List[str]:
        text = f"{title} {detail}"
        return fact_graph_builder.infer_capabilities(text, technologies)

    @classmethod
    def extract_metrics(cls, text: str) -> List[str]:
        facts = fact_graph_builder.extract_metric_facts(text, "temp")
        return [f.raw_token for f in facts]

    @classmethod
    def score_evidence(
        cls,
        project_name: str,
        evidence_point: Dict[str, Any],
        project_technologies: List[str],
        job: Job,
        role_family: str,
        matched_skills: List[str],
        jd_profile: Optional[JDCapabilityProfile] = None,
        fact_node: Optional[FactNode] = None,
    ) -> ScoredEvidenceItem:
        title = evidence_point.get("title", "") if isinstance(evidence_point, dict) else ""
        detail = evidence_point.get("detail", "") if isinstance(evidence_point, dict) else str(evidence_point)
        evidence_techs = evidence_point.get("technologies", project_technologies) if isinstance(evidence_point, dict) else project_technologies

        profile = jd_profile or jd_capability_analyzer.analyze_job(job)
        capabilities = cls.infer_capabilities(title, detail, evidence_techs)
        metrics = cls.extract_metrics(detail)

        claim_text = f"{title}: {detail}" if title else detail

        # 1. Responsibility Fit (30%)
        resp_scores = []
        for problem in profile.core_problem_statements:
            p_score = fuzz.partial_ratio(claim_text.lower(), problem.lower())
            t_score = fuzz.token_set_ratio(claim_text.lower(), problem.lower())
            resp_scores.append(max(p_score, t_score) / 100.0)
        
        # Token overlap giữa claim text và JD context
        jd_context = f"{job.title} {job.description or ''} {job.requirements_summary or ''}".lower()
        jd_words = set(re.findall(r"[a-zA-Z0-9_\+\#\.\-]+", jd_context))
        claim_words = set(re.findall(r"[a-zA-Z0-9_\+\#\.\-]+", claim_text.lower()))
        common_words = claim_words & jd_words
        term_overlap = len(common_words) / max(len(claim_words), 1)
        resp_scores.append(min(1.0, term_overlap * 2.5))

        gen_score = max(
            fuzz.partial_ratio(claim_text.lower(), jd_context),
            fuzz.token_set_ratio(claim_text.lower(), jd_context)
        ) / 100.0
        resp_scores.append(gen_score)
        responsibility_score = max(max(resp_scores) if resp_scores else 0.50, 0.40)

        # 2. Capability Alignment (30%)
        cap_alignment_scores = []
        for cap in capabilities:
            dom = CAP_TO_DOMAIN_MAP.get(cap.lower(), cap.lower())
            cap_weight = profile.capability_vector.get(dom, profile.capability_vector.get(cap, 0.40))
            cap_alignment_scores.append(cap_weight)
        capability_score = max(cap_alignment_scores) if cap_alignment_scores else 0.50

        # 3. Technology Precision Fit (25%)
        tech_points = 0.0
        for tech in evidence_techs:
            t_low = tech.lower()
            req_type = profile.skill_classifications.get(tech, SkillRequirementType.IRRELEVANT)
            if req_type == SkillRequirementType.REQUIRED or t_low in jd_words:
                tech_points += 1.0
            elif req_type == SkillRequirementType.PREFERRED or any(t_low in w for w in jd_words):
                tech_points += 0.8
            elif req_type == SkillRequirementType.IMPLICIT:
                tech_points += 0.5
            elif t_low in [s.lower() for s in matched_skills]:
                tech_points += 0.9
            else:
                tech_points += 0.2
        
        tech_fit_score = min(1.0, (tech_points / max(len(evidence_techs), 1)) * 1.3) if evidence_techs else 0.40

        # 4. Evidence & Metric Strength (15%)
        evidence_strength_score = 0.50
        if metrics:
            evidence_strength_score += 0.30
        if len(evidence_techs) >= 3:
            evidence_strength_score += 0.20
        evidence_strength_score = min(1.0, evidence_strength_score)

        # 5. Negative Irrelevance Penalty (Phạt nếu công nghệ hoàn toàn lệch domain JD)
        irrelevance_penalty = 0.0
        top_jd_domains = set(profile.primary_domains)
        bullet_domains = {CAP_TO_DOMAIN_MAP.get(c.lower(), c.lower()) for c in capabilities}
        if bullet_domains and not (bullet_domains & top_jd_domains):
            if "general" not in top_jd_domains and max(profile.capability_vector.values()) >= 0.80:
                irrelevance_penalty = 0.10

        # 6. JD Importance Multiplier
        jd_importance_weight = 1.0
        if any(kw in claim_text.lower() for kw in profile.primary_domains):
            jd_importance_weight = 1.1

        # Tổng hợp điểm số đa tín hiệu
        base_composite = (
            0.30 * responsibility_score
            + 0.30 * capability_score
            + 0.25 * tech_fit_score
            + 0.15 * evidence_strength_score
        )
        
        final_score = (base_composite * jd_importance_weight) - irrelevance_penalty
        final_score = round(min(1.0, max(0.0, final_score)), 4)

        if not fact_node:
            p_slug = re.sub(r"[^a-zA-Z0-9_]", "_", project_name.lower()).strip("_")
            fact_node = FactNode(
                fact_id=f"project.{p_slug}.temp_bullet",
                entity_type="PROJECT",
                entity_id=project_name,
                raw_statement=claim_text,
                technologies=evidence_techs,
                capabilities=capabilities,
                metrics=[MetricFact(f"metric_{i}", 0.0, "", "", m) for i, m in enumerate(metrics)],
            )

        return ScoredEvidenceItem(
            fact_node=fact_node,
            project_name=project_name,
            evidence_title=title,
            evidence_detail=detail,
            technologies=evidence_techs,
            total_score=final_score,
            responsibility_score=round(responsibility_score, 4),
            capability_score=round(capability_score, 4),
            tech_fit_score=round(tech_fit_score, 4),
            evidence_strength_score=round(evidence_strength_score, 4),
            jd_importance_weight=jd_importance_weight,
            irrelevance_penalty=irrelevance_penalty,
            matched_capabilities=capabilities,
            metrics=metrics,
        )


# ============================================================================
# Diverse Evidence Selector (MMR-style)
# ============================================================================

class DiverseEvidenceSelector:
    """Chọn lọc tập bằng chứng hàng đầu đảm bảo độ phủ đa dạng các năng lực."""

    @classmethod
    def select_diverse_evidence(
        cls,
        all_scored_evidence: List[ScoredEvidenceItem],
        limit: int = 3,
        min_threshold: float = 0.30,
    ) -> List[ScoredEvidenceItem]:
        qualified = [e for e in all_scored_evidence if e.total_score >= min_threshold]
        if not qualified:
            qualified = all_scored_evidence

        sorted_ev = sorted(qualified, key=lambda e: e.total_score, reverse=True)

        selected: List[ScoredEvidenceItem] = []
        covered_capabilities: Set[str] = set()

        for item in sorted_ev:
            item_caps = set(item.matched_capabilities or item.fact_node.capabilities)
            if len(selected) < limit:
                if not covered_capabilities or not item_caps.issubset(covered_capabilities):
                    selected.append(item)
                    covered_capabilities.update(item_caps)

        for item in sorted_ev:
            if len(selected) >= limit:
                break
            if item not in selected:
                selected.append(item)

        return selected


# ============================================================================
# Grounded Summary Synthesizer (Evidence-Locked & Hybrid-Aware)
# ============================================================================

class AdaptiveSummaryBuilder:
    """
    Xây dựng Summary định vị thích ứng không dùng template cứng:
    - Danh tính học vấn thật: Trường ĐH KHTN (VNUHCM-US), chuyên ngành Cyber Security, GPA thật.
    - Định vị chuyên môn theo phổ năng lực JD kết hợp bằng chứng dự án đã kiểm chứng.
    """

    @classmethod
    def build_summary(
        cls,
        candidate: Candidate,
        role_family: str,
        target_title: str,
        top_evidence: List[ScoredEvidenceItem],
        matched_skills: List[str],
        jd_profile: Optional[JDCapabilityProfile] = None,
    ) -> str:
        edu_major = "Computer Science (Cyber Security)"
        edu_school = "VNUHCM - University of Science"
        if candidate.education and len(candidate.education) > 0:
            edu_0 = candidate.education[0]
            edu_major = edu_0.get("field", edu_major)
            edu_school = edu_0.get("institution", edu_school)

        # Thu thập các năng lực hàng đầu từ top evidence
        verified_caps = []
        for e in top_evidence:
            verified_caps.extend(e.matched_capabilities)
        unique_caps = list(dict.fromkeys(verified_caps))

        profile = jd_profile or JDCapabilityProfile(
            capability_vector={"backend": 0.8}, primary_domains=[role_family]
        )
        primary_doms = profile.primary_domains

        # Xác định các điểm sáng kỹ thuật thực chiến
        has_api_db = any(c in unique_caps for c in ["api", "database"])
        has_crypto_pki = any(c in unique_caps for c in ["crypto", "system_programming", "security"])
        has_realtime_infra = any(c in unique_caps for c in ["realtime", "infra"])
        has_mobile = "mobile" in unique_caps

        if "systems" in primary_doms or "security" in primary_doms:
            if has_crypto_pki:
                summary = (
                    f"Final-year {edu_major} student at {edu_school} with deep foundations in modern C++, "
                    f"Public Key Infrastructure (PKI), and applied cryptography. Hands-on experience architecting "
                    f"zero-knowledge security workflows, IEEE 802.1X EAP-TLS protocol emulation, X.509 certificate chain validation with OpenSSL, "
                    f"and serverless cryptographic synchronization. Seeking a {target_title} position to apply secure architecture and systems engineering practices."
                )
            else:
                summary = (
                    f"Final-year {edu_major} student at {edu_school} specializing in system-level software engineering, "
                    f"cloud infrastructure, and low-latency network protocols. Practical experience developing high-performance "
                    f"serverless edge services and protocol simulations. Seeking a {target_title} position to build robust, scalable, and resilient systems."
                )
        elif "mobile" in primary_doms or has_mobile and "mobile" in profile.capability_vector and profile.capability_vector["mobile"] >= 0.40:
            summary = (
                f"Final-year {edu_major} student at {edu_school} with strong expertise in cross-platform mobile development with Flutter/Dart "
                f"and secure serverless backends with Cloudflare Workers/Hono. Experienced in architecting offline-first local storage, "
                f"hardware-backed keystores, and zero-knowledge synchronization APIs. Seeking a {target_title} role to engineer high-quality, secure client-server applications."
            )
        elif "frontend" in primary_doms:
            summary = (
                f"Final-year {edu_major} student at {edu_school} with practical experience engineering responsive real-time web applications "
                f"with React, TypeScript, and Tailwind CSS. Hands-on background connecting UI clients to stateful edge WebSockets and serverless APIs. "
                f"Seeking a {target_title} position to deliver polished, resilient, and performant user experiences."
            )
        elif "backend" in primary_doms or has_api_db:
            summary = (
                f"Final-year {edu_major} student at {edu_school} specializing in backend software engineering, "
                f"relational data modeling, and distributed serverless APIs. Hands-on experience architecting high-throughput "
                f"REST and WebSocket services with Cloudflare Workers, Hono, and SQLite/D1, backed by client-side cryptographic hashing "
                f"and dynamic rate limiting. Seeking a {target_title} position to build scalable, secure, and resilient backend systems."
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
    """
    Facade điều phối toàn bộ lớp Resume Intelligence:
    1. Trích xuất Fact Graph cấu trúc từ Candidate.
    2. Phân tích JD Capability Profile đa chiều.
    3. Chấm điểm minh chứng đa tín hiệu (Multi-Signal Evidence Scoring).
    4. Tuyển chọn dự án có mục tiêu (Targeted MMR) và phân bổ Layout Budget.
    5. Xây dựng ResumeStrategy làm Intermediate Representation duy nhất.
    """

    @classmethod
    def build_strategy(
        cls,
        candidate: Candidate,
        job: Job,
        match_record: Optional[JobMatch] = None,
        custom_tone: str = "professional_and_humble",
        layout_budget: Optional[LayoutBudget] = None,
    ) -> ResumeStrategy:
        budget = layout_budget or LayoutBudget()

        # 1. Xây dựng Fact Graph & JD Capability Profile
        fact_nodes = fact_graph_builder.build_fact_graph(candidate)
        jd_profile = jd_capability_analyzer.analyze_job(job)
        role_family = RoleClassifier.classify_role(job)
        raw_title = job.title or candidate.headline or "Software Engineer Intern"
        target_title = normalize_target_title_to_english(raw_title, role_family)

        # 2. Thu thập matched skills
        matched_skills = []
        if match_record and match_record.matched_skills:
            matched_skills = match_record.matched_skills
        else:
            candidate_skills = []
            if "skills" in candidate.__dict__ and candidate.skills:
                candidate_skills = [s.name for s in candidate.skills]
            jd_text = f"{job.title} {job.description or ''} {job.requirements_summary or ''}".lower()
            for s in candidate_skills:
                if s.lower() in jd_text:
                    matched_skills.append(s)

        # 3. Chấm điểm từng Evidence Point trong từng Project
        scored_projects: List[ScoredProjectCandidate] = []
        all_scored_evidences: List[ScoredEvidenceItem] = []

        from app.services.tailoring.fact_graph import safe_get_relation
        candidate_projects = safe_get_relation(candidate, "projects")
        for proj in candidate_projects:
            proj_ev_scored: List[ScoredEvidenceItem] = []
            p_slug = re.sub(r"[^a-zA-Z0-9_]", "_", proj.name.lower()).strip("_")

            if proj.evidence_points:
                for b_idx, ev in enumerate(proj.evidence_points):
                    bullet_fact_id = f"project.{p_slug}.bullet_{b_idx+1}"
                    f_node = fact_nodes.get(bullet_fact_id)

                    scored_ev = EvidenceScorer.score_evidence(
                        project_name=proj.name,
                        evidence_point=ev,
                        project_technologies=proj.technologies or [],
                        job=job,
                        role_family=role_family,
                        matched_skills=matched_skills,
                        jd_profile=jd_profile,
                        fact_node=f_node,
                    )
                    proj_ev_scored.append(scored_ev)
                    all_scored_evidences.append(scored_ev)

            # Sắp xếp bullet points trong project theo score giảm dần
            proj_ev_scored.sort(key=lambda e: e.total_score, reverse=True)

            # Aggregate Project Score
            if proj_ev_scored:
                top_scores = [e.total_score for e in proj_ev_scored[:2]]
                proj_score = sum(top_scores) / len(top_scores)
            else:
                proj_score = 0.50

            all_caps = []
            for ev in proj_ev_scored:
                all_caps.extend(ev.matched_capabilities)
            unique_caps = list(dict.fromkeys(all_caps))

            scored_projects.append(
                ScoredProjectCandidate(
                    project=proj,
                    project_score=round(proj_score, 4),
                    ranked_evidence=proj_ev_scored,
                    capabilities=unique_caps,
                    matched_technologies=[t for t in (proj.technologies or []) if t.lower() in [m.lower() for m in matched_skills]],
                )
            )

        # 4. Tuyển chọn Dự án & Phân bổ Bố cục (Targeted MMR)
        from app.services.tailoring.project_selector import project_selector
        selection_result = project_selector.select_projects(
            candidate_projects=scored_projects,
            job=job,
            role_family=role_family,
            matched_skills=matched_skills,
            layout_budget=budget,
            jd_capability_profile=jd_profile,
        )
        selected_projects = selection_result.selected_projects

        # 5. Tuyển chọn Diverse Evidence cho Cover Letter
        selected_evidence = DiverseEvidenceSelector.select_diverse_evidence(
            all_scored_evidence=all_scored_evidences,
            limit=3,
            min_threshold=0.30,
        )

        # 6. Sắp xếp Kỹ năng ưu tiên (Priority Skills)
        candidate_skills_list = []
        skills_rel = safe_get_relation(candidate, "skills")
        if skills_rel:
            candidate_skills_list = [s.name for s in skills_rel]
        if not candidate_skills_list:
            candidate_skills_list = ["C++", "Python", "JavaScript", "TypeScript", "SQL", "Linux", "Docker", "X.509 PKI", "OpenSSL"]

        matched_set = {s.lower() for s in matched_skills}

        def skill_rank_key(skill_name: str) -> Tuple[int, int]:
            s_lower = skill_name.lower()
            # 1. Trực tiếp matched trong JD
            is_matched = 1 if s_lower in matched_set else 0
            # 2. Trọng số yêu cầu trong JD Capability Profile
            req_type = jd_profile.skill_classifications.get(skill_name, SkillRequirementType.IRRELEVANT)
            req_weight = 0
            if req_type == SkillRequirementType.REQUIRED:
                req_weight = 30
            elif req_type == SkillRequirementType.PREFERRED:
                req_weight = 20
            elif req_type == SkillRequirementType.IMPLICIT:
                req_weight = 10
            # 3. Domain vector affinity
            for dom, w in jd_profile.capability_vector.items():
                if any(kw in s_lower for kw in DOMAIN_KEYWORD_TAXONOMY.get(dom, set())):
                    req_weight = max(req_weight, int(w * 10))
            return (is_matched, req_weight)

        priority_skills = sorted(candidate_skills_list, key=skill_rank_key, reverse=True)

        # 7. Xây dựng Grounded Summary
        adaptive_summary = AdaptiveSummaryBuilder.build_summary(
            candidate=candidate,
            role_family=role_family,
            target_title=target_title,
            top_evidence=selected_evidence,
            matched_skills=matched_skills,
            jd_profile=jd_profile,
        )

        # Top Capabilities
        all_caps = []
        for e in selected_evidence:
            all_caps.extend(e.matched_capabilities)
        top_capabilities = list(dict.fromkeys(all_caps))

        top_project_name = selected_projects[0].project.name if selected_projects else (scored_projects[0].project.name if scored_projects else 'None')
        logger.info(
            f"Resume Strategy built: role_family='{role_family}', target_title='{target_title}', "
            f"selected_projects_count={len(selected_projects)}, top_project='{top_project_name}'"
        )

        # Xây dựng Explainability Matrix
        explainability_matrix = {
            "jd_capability_vector": jd_profile.capability_vector,
            "primary_domains": jd_profile.primary_domains,
            "selected_projects": [p.project.name for p in selected_projects],
            "selection_reasons": selection_result.reasons,
            "project_scores": selection_result.scores,
        }

        return ResumeStrategy(
            role_family=role_family,
            target_title=target_title,
            adaptive_summary=adaptive_summary,
            priority_skills=priority_skills,
            ranked_projects=selected_projects,
            selected_projects=selected_projects,
            selected_evidence=selected_evidence,
            matched_skills=matched_skills,
            top_capabilities=top_capabilities,
            jd_capability_profile=jd_profile,
            layout_budget=budget,
            project_selection_result=selection_result,
            explainability_matrix=explainability_matrix,
            all_projects=scored_projects,
            all_scored_evidence=all_scored_evidences,
        )


resume_intelligence = ResumeIntelligenceEngine()
