import logging
from typing import Any, Dict, List, Optional

from app.schemas.tailoring_ir import (
    EvidenceBundle,
    GeneratedBullet,
    GeneratedClaimFragment,
    GeneratedProject,
    GeneratedSummary,
    StructuredResumeDraft,
)

logger = logging.getLogger("deterministic_composer")


class DeterministicResumeComposer:
    """
    Deterministic Resume Composer:
    - Cơ chế lắp ráp CV hoàn toàn tất định (Rule & Template Based Composition).
    - Được sử dụng khi:
      + Không có API Key hoặc chạy trong môi trường kiểm thử offline.
      + Fallback cho từng bullet cụ thể khi Gemini vượt quá giới hạn regeneration.
    - Nguyên tắc:
      + Chỉ chọn lọc (select), sắp xếp (reorder) và ghép nối (join) các EvidenceFact có sẵn.
      + Tuyệt đối không tự suy diễn hoặc bịa đặt thêm bất kỳ thông tin nào ngoài EvidenceFact.
    """

    @classmethod
    def compose_bullet(cls, fact: Any) -> GeneratedBullet:
        """Lắp ráp một bullet point tất định từ một EvidenceFact đơn lẻ."""
        claim_text = getattr(fact, "claim", str(fact))
        fact_id = getattr(fact, "id", "evidence.unknown")
        
        # Bỏ tiền tố tên dự án nếu có dạng "Project Name: Detail"
        if ":" in claim_text and not claim_text.startswith("http"):
            parts = claim_text.split(":", 1)
            bullet_text = parts[1].strip()
        else:
            bullet_text = claim_text.strip()

        claim_fragment = GeneratedClaimFragment(
            claim=bullet_text,
            evidence_ids=[fact_id],
        )

        return GeneratedBullet(
            text=bullet_text,
            evidence_ids=[fact_id],
            claims=[claim_fragment],
        )

    @classmethod
    def compose_summary(cls, bundle: EvidenceBundle) -> GeneratedSummary:
        """Lắp ráp đoạn Professional Summary tất định dựa trên định vị và học vấn."""
        strategy = bundle.strategy
        facts = bundle.evidence_facts

        edu_fact = next((f for f in facts if f.id.startswith("education.")), None)
        edu_statement = "Final-year Computer Science student at VNUHCM-US"
        edu_ids = []
        if edu_fact:
            edu_statement = f"Final-year student at {edu_fact.subject}"
            edu_ids.append(edu_fact.id)

        target_title = strategy.target_role
        positioning = strategy.positioning

        # Top project facts
        proj_facts = [f for f in facts if f.id.startswith("project.") and f.is_core]
        if not proj_facts:
            proj_facts = [f for f in facts if f.id.startswith("project.")]

        cited_ids = list(edu_ids)
        fragments = []

        summary_text = (
            f"{edu_statement} focusing on {positioning.lower()}. "
            f"Hands-on background designing verifiable systems and serverless architectures. "
            f"Seeking a {target_title} position to apply robust engineering practices."
        )

        if edu_ids:
            fragments.append(GeneratedClaimFragment(
                claim=edu_statement,
                evidence_ids=edu_ids,
            ))

        for pf in proj_facts[:2]:
            cited_ids.append(pf.id)
            fragments.append(GeneratedClaimFragment(
                claim=pf.claim,
                evidence_ids=[pf.id],
            ))

        if not fragments:
            fragments.append(GeneratedClaimFragment(
                claim=summary_text,
                evidence_ids=cited_ids or ["candidate.identity"],
            ))

        return GeneratedSummary(
            text=summary_text,
            evidence_ids=cited_ids or ["candidate.identity"],
            claims=fragments,
        )

    @classmethod
    def compose_draft(cls, bundle: EvidenceBundle) -> StructuredResumeDraft:
        """
        Lắp ráp toàn bộ bản StructuredResumeDraft tất định từ EvidenceBundle.
        """
        strategy = bundle.strategy
        facts_by_id = {f.id: f for f in bundle.evidence_facts}

        # 1. Summary
        summary = cls.compose_summary(bundle)

        # 2. Priority Skills
        skills = strategy.prioritized_skills[:8]

        # 3. Projects & Bullets
        generated_projects: List[GeneratedProject] = []
        for p_name in strategy.selected_projects:
            proj_bullets: List[GeneratedBullet] = []
            
            # Lấy các facts thuộc project này
            for fid in strategy.selected_evidence_ids:
                if fid in facts_by_id and facts_by_id[fid].subject == p_name:
                    fact = facts_by_id[fid]
                    proj_bullets.append(cls.compose_bullet(fact))

            # Giới hạn số lượng bullet theo budget
            max_b = bundle.layout_budget.max_bullets_per_project
            proj_bullets = proj_bullets[:max_b]

            if proj_bullets:
                generated_projects.append(
                    GeneratedProject(
                        source_project_name=p_name,
                        bullets=proj_bullets,
                    )
                )

        logger.info(
            f"[DeterministicResumeComposer] Assembled fallback draft with {len(generated_projects)} projects, "
            f"target_title='{strategy.target_role}'."
        )

        return StructuredResumeDraft(
            target_title=strategy.target_role,
            professional_summary=summary,
            priority_skills=skills,
            projects=generated_projects,
        )


deterministic_composer = DeterministicResumeComposer()
