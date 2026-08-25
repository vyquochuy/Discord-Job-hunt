import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.job import Job
from app.schemas.tailoring_ir import (
    JDCapabilityProfile,
    LayoutBudget,
    ProjectScoringDetail,
    ProjectSelectionResult,
    ScoredEvidenceItem,
    ScoredProjectCandidate,
    SkillRequirementType,
)
from app.services.tailoring.jd_capability_analyzer import jd_capability_analyzer
from app.services.tailoring.layout_planner import layout_planner

logger = logging.getLogger("project_selector")

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


class StrategicProjectSelector:
    """
    Tuyển chọn và sắp xếp các dự án (Project Selection & Targeted MMR):
    1. Chấm điểm đa tín hiệu cho từng dự án (Multi-Signal Scoring):
       - Semantic relevance từ evidence bullets.
       - Role fit tương thích với JD Capability Vector.
       - Direct technology overlap với JD matched skills.
       - Irrelevance penalty cho tech stack không liên quan.
    2. Tuyển chọn danh mục tối ưu bằng Targeted MMR (Maximal Marginal Relevance):
       - Chỉ cộng điểm Diversity Bonus khi năng lực mới được JD yêu cầu rõ rệt.
       - Áp dụng Redundancy Penalty cho các dự án trùng lặp năng lực đã có.
    3. Cắt gọt và phân bổ số lượng bullet points theo ngân sách bố cục (Layout Budget).
    4. Sinh Ma trận giải trình lý do tuyển chọn (Selection Explainability Matrix).
    """

    @classmethod
    def _score_project(
        cls,
        sp: ScoredProjectCandidate,
        job: Job,
        role_family: str,
        matched_skills: List[str],
        jd_profile: JDCapabilityProfile,
    ) -> ProjectScoringDetail:
        """Tính toán điểm chi tiết đa tín hiệu cho 1 dự án đối chiếu với JD."""
        proj = sp.project

        # 1. Relevance Score từ top evidence items
        if sp.ranked_evidence:
            top_ev_scores = [getattr(e, "total_score", getattr(e, "score", 0.5)) for e in sp.ranked_evidence[:2]]
            relevance_score = sum(top_ev_scores) / len(top_ev_scores)
        else:
            relevance_score = getattr(sp, "project_score", 0.5)

        # 2. Role Fit Score tương thích với Capability Profile
        unique_caps = sp.capabilities or []
        if not unique_caps and sp.ranked_evidence:
            for e in sp.ranked_evidence:
                unique_caps.extend(getattr(e, "capabilities", getattr(e, "matched_capabilities", [])))
            unique_caps = list(dict.fromkeys(unique_caps))

        role_fit_scores = []
        for c in unique_caps:
            domain = CAP_TO_DOMAIN_MAP.get(c.lower(), c.lower())
            role_fit_scores.append(jd_profile.capability_vector.get(domain, 0.40))
        role_fit_score = max(role_fit_scores) if role_fit_scores else 0.50

        # 3. Direct Tech Overlap Score
        matched_set = {s.lower() for s in (matched_skills or [])}
        jd_context_tokens = set(re.findall(r"[a-zA-Z0-9_\+\#\.\-]+", f"{getattr(job, 'title', '')} {getattr(job, 'requirements_summary', '') or ''} {getattr(job, 'description', '') or ''}".lower()))
        proj_techs = [t.lower() for t in (proj.technologies or [])]
        overlap_count = sum(1 for t in proj_techs if t in matched_set or t in jd_context_tokens or any(m in t for m in matched_set))
        tech_overlap_score = min(1.0, (overlap_count + (1 if matched_set else 0)) / max(2, len(matched_skills or [2])))

        # 4. Irrelevance Penalty (Chỉ phạt nếu cả tech lẫn capabilities đều không liên quan JD chuyên biệt)
        irrelevance_penalty = 0.0
        if proj_techs and not overlap_count and role_fit_score < 0.25 and max(jd_profile.capability_vector.values()) >= 0.80:
            irrelevance_penalty = 0.10

        # Tổng hợp điểm số cơ bản
        final_score = (
            (relevance_score * 0.50)
            + (role_fit_score * 0.30)
            + (tech_overlap_score * 0.20)
            - irrelevance_penalty
        )
        final_score = round(min(1.0, max(0.0, final_score)), 4)

        reasons = []
        if relevance_score >= 0.70:
            reasons.append(f"High evidence relevance ({relevance_score:.2f})")
        if role_fit_score >= 0.60:
            reasons.append(f"Strong domain fit ({role_fit_score:.2f})")
        if tech_overlap_score >= 0.40:
            reasons.append(f"Direct technology alignment ({overlap_count} matched)")
        if irrelevance_penalty > 0:
            reasons.append("Unrelated technology penalty (-0.10)")

        return ProjectScoringDetail(
            project_name=proj.name,
            relevance_score=round(relevance_score, 4),
            role_fit_score=round(role_fit_score, 4),
            tech_overlap_score=round(tech_overlap_score, 4),
            irrelevance_penalty=round(irrelevance_penalty, 4),
            final_score=final_score,
            capabilities=unique_caps,
            selection_reasons=reasons or ["Baseline project alignment"],
        )

    @classmethod
    def select_projects(
        cls,
        candidate_projects: List[ScoredProjectCandidate],
        job: Job,
        role_family: str,
        matched_skills: List[str],
        layout_budget: Optional[LayoutBudget] = None,
        jd_capability_profile: Optional[JDCapabilityProfile] = None,
    ) -> ProjectSelectionResult:
        """
        Thực hiện tuyển chọn dự án theo thuật toán Targeted MMR.
        """
        if not candidate_projects:
            return ProjectSelectionResult(
                selected_projects=[],
                rejected_projects=[],
                scores={},
                reasons={},
                scoring_details={},
                layout_budget=layout_budget or LayoutBudget(),
            )

        budget = layout_budget or layout_planner.compute_budget(job, candidate_projects)
        jd_profile = jd_capability_profile or jd_capability_analyzer.analyze_job(job)

        # 1. Chấm điểm độc lập từng dự án
        scoring_details: Dict[str, ProjectScoringDetail] = {}
        for sp in candidate_projects:
            p_name = sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")
            detail = cls._score_project(sp, job, role_family, matched_skills, jd_profile)
            scoring_details[p_name] = detail

        # 2. Targeted MMR Selection Loop
        selected_raw: List[ScoredProjectCandidate] = []
        covered_capabilities: Set[str] = set()
        pool = list(candidate_projects)

        while pool and len(selected_raw) < budget.max_projects:
            best_candidate: Optional[ScoredProjectCandidate] = None
            best_marginal_score = -999.0
            best_diversity_bonus = 0.0
            best_redundancy_penalty = 0.0

            for sp in pool:
                p_name = sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")
                base_detail = scoring_details[p_name]
                p_caps = set(base_detail.capabilities)

                # Targeted Diversity Bonus: Chỉ thưởng khi capability mới có trong JD
                new_caps = p_caps - covered_capabilities
                diversity_bonus = 0.0
                for cap in new_caps:
                    dom = CAP_TO_DOMAIN_MAP.get(cap.lower(), cap.lower())
                    jd_cap_weight = jd_profile.capability_vector.get(dom, 0.40)
                    if jd_cap_weight >= 0.20:
                        diversity_bonus += jd_cap_weight * 0.25
                diversity_bonus = min(0.35, diversity_bonus)

                # Redundancy Penalty: Nếu không bổ sung năng lực mới và năng lực cũ đã phủ kín
                redundancy_penalty = 0.0
                if selected_raw and not new_caps:
                    redundancy_penalty = 0.25

                marginal_score = (
                    base_detail.final_score
                    + diversity_bonus
                    - redundancy_penalty
                )
                marginal_score = round(min(1.0, max(0.0, marginal_score)), 4)

                if marginal_score > best_marginal_score:
                    best_marginal_score = marginal_score
                    best_candidate = sp
                    best_diversity_bonus = diversity_bonus
                    best_redundancy_penalty = redundancy_penalty

            if not best_candidate:
                break

            # Kiểm tra ngưỡng tin cậy tối thiểu
            cand_name = best_candidate.project.name if hasattr(best_candidate, "project") else getattr(best_candidate, "name", "")
            base_score = scoring_details[cand_name].final_score

            if base_score < budget.min_project_threshold and len(selected_raw) >= budget.min_projects:
                logger.info(
                    f"Project '{cand_name}' (Score: {base_score:.3f}) is below threshold "
                    f"{budget.min_project_threshold}. Stopping selection."
                )
                break

            # Cập nhật lý do nếu có MMR effect
            if best_diversity_bonus > 0:
                scoring_details[cand_name].selection_reasons.append(
                    f"Targeted diversity bonus (+{best_diversity_bonus:.2f})"
                )
            if best_redundancy_penalty > 0:
                scoring_details[cand_name].selection_reasons.append(
                    f"Redundancy penalty (-{best_redundancy_penalty:.2f})"
                )

            selected_raw.append(best_candidate)
            pool.remove(best_candidate)
            covered_capabilities.update(scoring_details[cand_name].capabilities)

        # Fallback nếu chưa đủ số dự án tối thiểu
        if len(selected_raw) < budget.min_projects and pool:
            for sp in sorted(pool, key=lambda x: scoring_details[x.project.name if hasattr(x, "project") else getattr(x, "name", "")].final_score, reverse=True):
                selected_raw.append(sp)
                if len(selected_raw) >= budget.min_projects:
                    break

        # 3. Phân bổ số lượng bullet points theo Layout Planner
        selected_candidates, rejected_candidates = layout_planner.allocate_bullets(
            selected_raw=selected_raw,
            all_candidates=candidate_projects,
            budget=budget,
        )

        selected_names_set = {
            sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")
            for sp in selected_candidates
        }

        scores_dict = {
            (sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")): scoring_details[
                sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")
            ].final_score
            for sp in candidate_projects
        }

        reasons_dict = {}
        for sp in candidate_projects:
            p_name = sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")
            base_reasons = "; ".join(scoring_details[p_name].selection_reasons)
            if p_name in selected_names_set:
                reasons_dict[p_name] = f"Được chọn: {base_reasons}"
            else:
                reasons_dict[p_name] = f"Loại bỏ: {base_reasons}"

        logger.info(
            f"[ProjectSelector] Selected {len(selected_candidates)}/{len(candidate_projects)} "
            f"projects for role '{role_family}': {[p.project.name for p in selected_candidates]}"
        )

        return ProjectSelectionResult(
            selected_projects=selected_candidates,
            rejected_projects=rejected_candidates,
            scores=scores_dict,
            reasons=reasons_dict,
            scoring_details=scoring_details,
            layout_budget=budget,
        )


project_selector = StrategicProjectSelector()
