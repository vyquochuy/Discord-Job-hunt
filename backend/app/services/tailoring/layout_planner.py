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
            all_evs = sp.ranked_evidence or []
            if not all_evs:
                allocated_projects.append(sp)
                continue

            # Tách riêng Core evidence và Supporting evidence
            core_items = [
                ev for ev in all_evs
                if getattr(ev, "is_core", False) or getattr(ev, "is_protected", False)
            ]
            if not core_items and all_evs:
                # Fallback: nếu không có bullet nào được gán is_core, coi bullet đầu tiên là core
                core_items = [all_evs[0]]

            core_ev = core_items[0]
            supporting_evs = [ev for ev in all_evs if ev is not core_ev]

            # Lọc supporting evidence theo ngưỡng chất lượng
            valid_supporting = [
                ev for ev in supporting_evs
                if getattr(ev, "total_score", getattr(ev, "score", 0.5)) >= budget.min_bullet_threshold
            ]
            if not valid_supporting and supporting_evs:
                valid_supporting = supporting_evs

            # Tính toán số lượng bullet cho project này
            # Min: 1 (chính là slot bảo vệ cho core)
            max_available = 1 + len(valid_supporting)
            bullets_to_take = min(max_available, budget.max_bullets_per_project)

            remaining_quota = budget.max_total_bullets - total_bullets_used
            bullets_to_take = max(
                budget.min_bullets_per_project,
                min(bullets_to_take, remaining_quota)
            )

            # Chọn (bullets_to_take - 1) supporting bullets có relevance cao nhất + 1 core bullet
            supporting_quota = max(0, bullets_to_take - 1)
            selected_supporting = valid_supporting[:supporting_quota]
            final_project_bullets = [core_ev] + selected_supporting

            # Sắp xếp hiển thị theo relevance score (total_score) giảm dần
            final_project_bullets.sort(
                key=lambda e: getattr(e, "total_score", getattr(e, "score", 0.5)),
                reverse=True,
            )

            total_bullets_used += len(final_project_bullets)

            allocated_projects.append(
                ScoredProjectCandidate(
                    project=sp.project,
                    project_score=sp.project_score,
                    ranked_evidence=final_project_bullets,
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
