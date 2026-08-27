import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.tailoring_ir import (
    EvidenceBundle,
    EvidenceFact,
    GeneratedBullet,
    GeneratedClaimFragment,
    GeneratedProject,
    GeneratedSummary,
    StructuredResumeDraft,
    ValidationReport,
    ValidationViolation,
    ValidationViolationType,
)
from app.services.tailoring.alias_registry import alias_registry
from app.services.tailoring.deterministic_composer import deterministic_composer
from app.services.tailoring.gemini_resume_writer import resume_semantic_writer

logger = logging.getLogger("evidence_validator")


class ClaimLevelValidator:
    """
    Tầng kiểm chứng hạt nhân (Claim-Level Anti-Hallucination Validator):
    - Hoạt động độc lập và hoàn toàn tất định (Deterministic Engine là Single Source of Truth).
    - Kiểm tra 6 tầng kiểm định:
      1. Schema & Structure Validation
      2. Evidence ID Existence Validation
      3. Technology Validation (thông qua Canonical Alias Registry)
      4. Metric Integrity Validation (con số, %, độ trễ, lưu lượng)
      5. Experience Inflation Validation (phát hiện thêu dệt production/lead)
      6. Unsupported JD Requirement Fabrication Check (chặn đứng mọi buzzword bịa đặt)
    """

    METRIC_PATTERN = r"\b(\d+(?:\.\d+)?)\s*(ms|s|%|req/min|req/10s|MB|GB|KB|POPs?|PoP|tables?|devices?|threshold|qps|users?)\b"
    EXCLUDED_NUMBERS = {"1", "2", "3", "4", "5", "2022", "2023", "2024", "2025", "2026", "2027"}

    FORBIDDEN_INFLATION_PATTERNS = [
        r"\b(?:led|managed)\s+(?:a\s+team\s+of|an\s+engineering\s+team\s+of)\b",
        r"\bproduction\s+(?:enterprise|distributed)\s+cluster\b",
        r"\bchief\s+architect\b",
        r"\bprincipal\s+engineer\b",
        r"\b100%\s+uptime\b",
        r"\b99\.999%\s+uptime\b",
    ]

    @classmethod
    def extract_metrics(cls, text: str) -> Set[str]:
        """Trích xuất tất cả các chỉ số định lượng từ văn bản."""
        if not text:
            return set()
        matches = re.finditer(cls.METRIC_PATTERN, text, re.IGNORECASE)
        found = set()
        for m in matches:
            found.add(m.group(0).strip().lower())
        return found

    @classmethod
    def validate_bullet(
        cls,
        bullet: GeneratedBullet,
        unit_id: str,
        project_name: str,
        bundle: EvidenceBundle,
    ) -> List[ValidationViolation]:
        """Kiểm chứng chi tiết cho 1 bullet point."""
        violations: List[ValidationViolation] = []
        facts_by_id = {f.id: f for f in bundle.evidence_facts}
        strategy = bundle.strategy

        # 1. Evidence ID Validation
        if not bullet.evidence_ids:
            violations.append(
                ValidationViolation(
                    violation_type=ValidationViolationType.INVALID_EVIDENCE_ID,
                    section=f"project.{project_name}",
                    unit_id=unit_id,
                    offending_text=bullet.text,
                    reason="Bullet does not cite any Evidence IDs.",
                )
            )
            return violations

        referenced_facts: List[EvidenceFact] = []
        for eid in bullet.evidence_ids:
            if eid not in facts_by_id:
                violations.append(
                    ValidationViolation(
                        violation_type=ValidationViolationType.INVALID_EVIDENCE_ID,
                        section=f"project.{project_name}",
                        unit_id=unit_id,
                        offending_text=eid,
                        reason=f"Evidence ID '{eid}' does not exist in the verified Evidence Bundle.",
                    )
                )
            else:
                referenced_facts.append(facts_by_id[eid])

        if not referenced_facts:
            return violations

        # 2. Technology Validation qua Alias Registry
        # Gom các canonical technologies được cấp phép bởi các facts mà bullet này viện dẫn
        allowed_canonical_techs: Set[str] = set()
        for rf in referenced_facts:
            allowed_canonical_techs.update(rf.canonical_technologies)
            for t in rf.technologies:
                c_id = alias_registry.get_canonical_id(t)
                if c_id:
                    allowed_canonical_techs.add(c_id)

        # Trích xuất các công nghệ xuất hiện trong text của bullet
        extracted_techs = alias_registry.extract_technologies_from_text(bullet.text)
        for surface_token, canon_id in extracted_techs:
            if canon_id not in allowed_canonical_techs:
                # Kiểm tra xem có phải công nghệ chung thuộc project hay không
                if canon_id not in strategy.allowed_technologies:
                    violations.append(
                        ValidationViolation(
                            violation_type=ValidationViolationType.UNSUPPORTED_TECHNOLOGY,
                            section=f"project.{project_name}",
                            unit_id=unit_id,
                            offending_text=surface_token,
                            reason=(
                                f"Technology '{surface_token}' (canonical: {canon_id}) is not supported "
                                f"by the cited evidence facts {[f.id for f in referenced_facts]}."
                            ),
                            suggested_correction=f"Remove '{surface_token}' or cite the fact supporting it.",
                        )
                    )

        # 3. Metric Integrity Validation
        bullet_metrics = cls.extract_metrics(bullet.text)
        supported_metrics: Set[str] = set()
        for rf in referenced_facts:
            for m in rf.metrics:
                supported_metrics.add(m.lower().strip())
                # Normalize raw tokens like "~45ms" -> "45ms"
                clean_m = re.sub(r"[~><]", "", m).strip().lower()
                supported_metrics.add(clean_m)

        for bm in bullet_metrics:
            clean_bm = re.sub(r"[~><]", "", bm).strip().lower()
            if bm not in supported_metrics and clean_bm not in supported_metrics:
                # Bỏ qua các số thứ tự thông thường nếu không kèm đơn vị nhạy cảm
                val_match = re.match(r"^(\d+)", clean_bm)
                if val_match and val_match.group(1) in cls.EXCLUDED_NUMBERS and not any(u in clean_bm for u in ["ms", "%", "qps", "req"]):
                    continue
                violations.append(
                    ValidationViolation(
                        violation_type=ValidationViolationType.UNSUPPORTED_METRIC,
                        section=f"project.{project_name}",
                        unit_id=unit_id,
                        offending_text=bm,
                        reason=f"Metric '{bm}' is not present in the referenced evidence {supported_metrics}.",
                        suggested_correction=f"Use only supported metrics: {list(supported_metrics)}.",
                    )
                )

        # 4. Experience Inflation Validation
        for pat in cls.FORBIDDEN_INFLATION_PATTERNS:
            found = re.findall(pat, bullet.text, re.IGNORECASE)
            if found:
                violations.append(
                    ValidationViolation(
                        violation_type=ValidationViolationType.EXPERIENCE_INFLATION,
                        section=f"project.{project_name}",
                        unit_id=unit_id,
                        offending_text=str(found),
                        reason=f"Exaggerated or inflated claim detected: '{found}'.",
                    )
                )

        # 5. Unsupported JD Requirement Fabrication Check
        for gap in strategy.unsupported_requirements:
            gap_clean = gap.lower().strip()
            if re.search(r"\b" + re.escape(gap_clean) + r"\b", bullet.text.lower()):
                violations.append(
                    ValidationViolation(
                        violation_type=ValidationViolationType.UNSUPPORTED_JD_FABRICATION,
                        section=f"project.{project_name}",
                        unit_id=unit_id,
                        offending_text=gap,
                        reason=f"Fabricated claim for unsupported JD requirement '{gap}'.",
                    )
                )

        # 6. Architectural Scope Consistency Check (client-side vs server-side displacement)
        bullet_lower = bullet.text.lower()
        for rf in referenced_facts:
            rf_claim_lower = rf.claim.lower()
            if "client-side argon2" in rf_claim_lower or "client-side argon2id" in rf_claim_lower:
                if "argon2" in bullet_lower and "client-side" not in bullet_lower:
                    violations.append(
                        ValidationViolation(
                            violation_type=ValidationViolationType.ARCHITECTURAL_SCOPE_SHIFT,
                            section=f"project.{project_name}",
                            unit_id=unit_id,
                            offending_text="Argon2id without client-side modifier",
                            reason="Architectural scope shift: Argon2id hashing is strictly client-side in Zero-Knowledge architecture, but 'client-side' modifier was omitted.",
                            suggested_correction="Specify 'client-side Argon2id password hashing' explicitly.",
                        )
                    )

        return violations

    @classmethod
    def validate_summary(
        cls,
        summary: GeneratedSummary,
        bundle: EvidenceBundle,
    ) -> List[ValidationViolation]:
        """Kiểm chứng tính chân thực của Professional Summary."""
        violations: List[ValidationViolation] = []
        facts_by_id = {f.id: f for f in bundle.evidence_facts}
        strategy = bundle.strategy

        if not summary.text or len(summary.text.strip()) < 10:
            violations.append(
                ValidationViolation(
                    violation_type=ValidationViolationType.SCHEMA_ERROR,
                    section="summary",
                    unit_id="summary",
                    offending_text="",
                    reason="Professional summary is empty or too short.",
                )
            )
            return violations

        # Kiểm tra unsupported JD requirements trong summary
        for gap in strategy.unsupported_requirements:
            gap_clean = gap.lower().strip()
            if re.search(r"\b" + re.escape(gap_clean) + r"\b", summary.text.lower()):
                violations.append(
                    ValidationViolation(
                        violation_type=ValidationViolationType.UNSUPPORTED_JD_FABRICATION,
                        section="summary",
                        unit_id="summary",
                        offending_text=gap,
                        reason=f"Summary falsely claims experience with unsupported requirement '{gap}'.",
                    )
                )

        # Inflation check
        for pat in cls.FORBIDDEN_INFLATION_PATTERNS:
            found = re.findall(pat, summary.text, re.IGNORECASE)
            if found:
                violations.append(
                    ValidationViolation(
                        violation_type=ValidationViolationType.EXPERIENCE_INFLATION,
                        section="summary",
                        unit_id="summary",
                        offending_text=str(found),
                        reason=f"Summary contains inflated seniority claim: '{found}'.",
                    )
                )

        return violations

    @classmethod
    def validate_draft(
        cls,
        draft: StructuredResumeDraft,
        bundle: EvidenceBundle,
    ) -> ValidationReport:
        """
        Kiểm tra toàn diện bản StructuredResumeDraft.
        Trả về ValidationReport phân rã trạng thái Valid / Invalid theo từng Unit.
        """
        all_violations: List[ValidationViolation] = []
        locked_units: Dict[str, Any] = {}
        total_units = 0
        accepted_units = 0

        # 1. Check Summary
        total_units += 1
        sum_violations = cls.validate_summary(draft.professional_summary, bundle)
        if not sum_violations:
            locked_units["summary"] = draft.professional_summary
            accepted_units += 1
        else:
            all_violations.extend(sum_violations)

        # 2. Check Projects & Bullets
        for p_idx, proj in enumerate(draft.projects):
            p_name = proj.source_project_name
            for b_idx, bullet in enumerate(proj.bullets):
                unit_id = f"project.{p_name}.bullet_{b_idx+1}"
                total_units += 1

                b_violations = cls.validate_bullet(
                    bullet=bullet,
                    unit_id=unit_id,
                    project_name=p_name,
                    bundle=bundle,
                )

                if not b_violations:
                    locked_units[unit_id] = bullet
                    accepted_units += 1
                else:
                    all_violations.extend(b_violations)

        provenance_score = round((accepted_units / max(total_units, 1)) * 100.0, 1)
        is_valid = len(all_violations) == 0

        logger.info(
            f"[ClaimLevelValidator] Validated {total_units} units. Accepted: {accepted_units}, "
            f"Violations: {len(all_violations)}, Score: {provenance_score}%."
        )

        return ValidationReport(
            is_valid=is_valid,
            provenance_score=provenance_score,
            violations=all_violations,
            accepted_units_count=accepted_units,
            total_units_count=total_units,
            locked_units=locked_units,
            feedback_for_regeneration=None,
        )


class UnitRegenerationOrchestrator:
    """
    Orchestrator điều phối vòng lặp Regeneration có kiểm soát (Closed-Loop Unit-Level Regeneration):
    - KHÔNG regenerate toàn bộ Resume.
    - KHÓA (LOCK) toàn bộ các units đã hợp lệ (Valid Units).
    - CHỈ gửi phản hồi lỗi và yêu cầu Gemini viết lại các Units bị vi phạm.
    - Giới hạn max_retries = 2.
    - Nếu sau 2 lần retry vẫn vi phạm, tự động thế chỗ bằng Deterministic fallback bullet.
    """

    MAX_RETRIES = 2

    @classmethod
    async def validate_and_regenerate(
        cls,
        draft: StructuredResumeDraft,
        bundle: EvidenceBundle,
        max_retries: int = MAX_RETRIES,
    ) -> Tuple[StructuredResumeDraft, ValidationReport]:
        """
        Thực thi vòng lặp kiểm tra và tái sinh có mục tiêu.
        Đảm bảo đầu ra cuối cùng 100% đạt chuẩn Zero-Hallucination.
        """
        facts_by_id = {f.id: f for f in bundle.evidence_facts}
        current_draft = draft

        report = ClaimLevelValidator.validate_draft(current_draft, bundle)
        if report.is_valid:
            logger.info("[UnitRegenerationOrchestrator] Initial draft is 100% valid. No regeneration needed.")
            return current_draft, report

        attempt = 0
        while attempt < max_retries and not report.is_valid:
            attempt += 1
            logger.warning(
                f"[UnitRegenerationOrchestrator] Attempt {attempt}/{max_retries}: "
                f"Regenerating {len(report.violations)} invalid units..."
            )

            # Gom các violations theo unit_id
            violations_by_unit: Dict[str, List[ValidationViolation]] = {}
            for v in report.violations:
                violations_by_unit.setdefault(v.unit_id, []).append(v)

            # 1. Tái sinh Summary nếu lỗi
            if "summary" in violations_by_unit:
                logger.info("Regenerating invalid summary...")
                new_summary = await resume_semantic_writer.regenerate_summary(
                    failed_text=current_draft.professional_summary.text,
                    violations=violations_by_unit["summary"],
                    bundle=bundle,
                )
                current_draft.professional_summary = new_summary

            # 2. Tái sinh từng Bullet lỗi trong từng Project
            for proj in current_draft.projects:
                p_name = proj.source_project_name
                # Thu thập verified facts của project này
                proj_facts = [
                    f for f in bundle.evidence_facts
                    if f.subject == p_name or f.id.startswith(f"project.{re.sub(r'[^a-zA-Z0-9_]', '_', p_name.lower()).strip('_')}")
                ]

                new_bullets: List[GeneratedBullet] = []
                for b_idx, bullet in enumerate(proj.bullets):
                    unit_id = f"project.{p_name}.bullet_{b_idx+1}"
                    if unit_id in report.locked_units:
                        # Giữ nguyên bullet đã được khóa (Locked)
                        new_bullets.append(report.locked_units[unit_id])
                    elif unit_id in violations_by_unit:
                        # Tái sinh bullet này
                        logger.info(f"Regenerating invalid unit '{unit_id}'...")
                        reg_bullet = await resume_semantic_writer.regenerate_bullet(
                            unit_id=unit_id,
                            project_name=p_name,
                            failed_text=bullet.text,
                            violations=violations_by_unit[unit_id],
                            supported_evidence_facts=proj_facts,
                            target_role=bundle.strategy.target_role,
                        )
                        new_bullets.append(reg_bullet)
                    else:
                        new_bullets.append(bullet)

                proj.bullets = new_bullets

            # Chạy kiểm tra lại sau khi regenerate
            report = ClaimLevelValidator.validate_draft(current_draft, bundle)

        # Nếu sau max_retries vẫn còn vi phạm, sử dụng deterministic fallback cho các units còn lỗi
        if not report.is_valid:
            logger.warning(
                "[UnitRegenerationOrchestrator] Max retries reached. "
                "Applying deterministic fallback for remaining invalid units."
            )
            fallback_draft = deterministic_composer.compose_draft(bundle)
            
            # Thay thế summary nếu vẫn lỗi
            if "summary" not in report.locked_units:
                current_draft.professional_summary = fallback_draft.professional_summary

            # Thay thế từng bullet nếu vẫn lỗi
            for proj_idx, proj in enumerate(current_draft.projects):
                p_name = proj.source_project_name
                fb_proj = next((fp for fp in fallback_draft.projects if fp.source_project_name == p_name), None)
                
                final_bullets: List[GeneratedBullet] = []
                for b_idx, bullet in enumerate(proj.bullets):
                    unit_id = f"project.{p_name}.bullet_{b_idx+1}"
                    if unit_id in report.locked_units:
                        final_bullets.append(report.locked_units[unit_id])
                    else:
                        if fb_proj and b_idx < len(fb_proj.bullets):
                            final_bullets.append(fb_proj.bullets[b_idx])
                        elif fb_proj and fb_proj.bullets:
                            final_bullets.append(fb_proj.bullets[0])
                        else:
                            final_bullets.append(deterministic_composer.compose_bullet(bundle.evidence_facts[0]))

                proj.bullets = final_bullets

            # Đánh giá lại lần cuối (phải 100% valid)
            report = ClaimLevelValidator.validate_draft(current_draft, bundle)

        logger.info(f"[UnitRegenerationOrchestrator] Final verified score: {report.provenance_score}%. Is valid: {report.is_valid}.")
        return current_draft, report


claim_validator = ClaimLevelValidator()
unit_regeneration_orchestrator = UnitRegenerationOrchestrator()
