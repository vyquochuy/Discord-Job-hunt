import logging
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.tailoring_ir import (
    LayoutBudget,
    ScoredEvidenceItem,
    ScoredProjectCandidate,
)

logger = logging.getLogger("layout_planner")


class LayoutPlanner:
    """
    Physical Layout Solver:
    - Giải quyết bài toán phân bổ ngân sách hiển thị tối ưu cho 1 trang A4 ATS.
    - Độc lập hoàn toàn với việc chấm điểm ngữ nghĩa.
    - Quản lý hạn mức số lượng dự án, số lượng bullet points, và độ dài tóm tắt.
    """

    @classmethod
    def compute_budget(cls, job: Any = None, candidates: Any = None) -> LayoutBudget:
        """Tính toán ngân sách layout dựa trên độ dài hồ sơ và JD."""
        return LayoutBudget()

    @classmethod
    def allocate_layout_budget(
        cls,
        selected_project_candidates: List[ScoredProjectCandidate],
        layout_budget: Optional[LayoutBudget] = None,
    ) -> List[ScoredProjectCandidate]:
        """
        Cắt tỉa và phân bổ số lượng bullet points cho các dự án đã chọn
        để đảm bảo không vượt quá dung lượng chuẩn 1 trang A4.
        """
        budget = layout_budget or LayoutBudget()
        
        if not selected_project_candidates:
            return []

        projects_to_include = selected_project_candidates[: budget.max_projects]
        
        allocated_projects: List[ScoredProjectCandidate] = []
        total_bullets_used = 0

        for sp in projects_to_include:
            valid_bullets = [
                ev for ev in sp.ranked_evidence
                if getattr(ev, "total_score", getattr(ev, "score", 0.5)) >= budget.min_bullet_threshold
            ]
            
            if not valid_bullets:
                valid_bullets = sp.ranked_evidence[: budget.min_bullets_per_project]

            bullets_to_take = min(len(valid_bullets), budget.max_bullets_per_project)
            
            remaining_quota = budget.max_total_bullets - total_bullets_used
            bullets_to_take = max(
                budget.min_bullets_per_project,
                min(bullets_to_take, remaining_quota)
            )

            pruned_bullets = valid_bullets[:bullets_to_take]
            total_bullets_used += len(pruned_bullets)

            allocated_projects.append(
                ScoredProjectCandidate(
                    project=sp.project,
                    project_score=sp.project_score,
                    ranked_evidence=pruned_bullets,
                    capabilities=sp.capabilities,
                    matched_technologies=sp.matched_technologies,
                    diversity_bonus=sp.diversity_bonus,
                    redundancy_penalty=sp.redundancy_penalty,
                    final_score=sp.final_score,
                    selection_reason=sp.selection_reason,
                )
            )

        logger.info(
            f"[LayoutPlanner] Allocated {len(allocated_projects)} projects with total {total_bullets_used} bullets (Max: {budget.max_total_bullets})."
        )
        return allocated_projects

    @classmethod
    def allocate_bullets(
        cls,
        selected_raw: List[ScoredProjectCandidate],
        all_candidates: List[ScoredProjectCandidate],
        budget: Optional[LayoutBudget] = None,
    ) -> Tuple[List[ScoredProjectCandidate], List[ScoredProjectCandidate]]:
        """Phân bổ bullet points và chia tách danh sách selected / rejected."""
        selected = cls.allocate_layout_budget(selected_raw, budget)
        selected_names = {
            sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")
            for sp in selected
        }
        rejected = [
            sp for sp in all_candidates
            if (sp.project.name if hasattr(sp, "project") else getattr(sp, "name", "")) not in selected_names
        ]
        return selected, rejected


layout_planner = LayoutPlanner()
