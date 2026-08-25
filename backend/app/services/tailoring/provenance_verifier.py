import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz

from app.models.candidate import Candidate
from app.schemas.resume import EvidenceMapItem
from app.schemas.tailoring_ir import (
    ClaimVerificationStatus,
    DecomposedClaim,
    FactNode,
    MetricFact,
)
from app.services.tailoring.fact_graph import fact_graph_builder

logger = logging.getLogger("provenance_verifier")


class ProvenanceVerifier:
    """
    Engine kiểm chứng nguồn gốc sự thật (Deterministic Claim-Level Provenance Engine):
    - Đối soát 100% claim, metric, con số và công nghệ với Đồ thị Sự thật bất biến (Fact Graph).
    - Phân rã bullet point thành các atomic claims để kiểm chứng độc lập.
    - Phát hiện các con số/thành tích bịa đặt (hallucinated metrics).
    - Tính điểm tin cậy Provenance Score (0.0 - 100.0%).
    """

    @staticmethod
    def extract_numbers_and_metrics(text: str) -> Set[str]:
        """Trích xuất tất cả các con số, phần trăm, độ trễ và thông số kỹ thuật định lượng."""
        if not text:
            return set()
        pattern = r"\b\d+(?:\.\d+)?(?:ms|s|%|req/min|req/10s|MB|GB|KB|POPs?|PoP|tables?|devices?|threshold)?\b"
        found = set(re.findall(pattern, text, re.IGNORECASE))
        return found

    @classmethod
    def decompose_claims(cls, text: str, bullet_ref: str = "") -> List[DecomposedClaim]:
        """Phân rã một bullet point hoặc đoạn văn bản thành các atomic claims độc lập."""
        if not text:
            return []
        
        clauses = re.split(r"[;\n•\–]", text)
        decomposed: List[DecomposedClaim] = []

        for idx, clause in enumerate(clauses):
            c_text = clause.strip()
            if len(c_text) < 5:
                continue
            
            # Trích xuất metrics và công nghệ có trong clause
            metrics = list(cls.extract_numbers_and_metrics(c_text))
            
            decomposed.append(
                DecomposedClaim(
                    claim_id=f"{bullet_ref}.claim_{idx+1}",
                    bullet_ref=bullet_ref,
                    action_text=c_text,
                    claimed_metrics=metrics,
                )
            )

        if not decomposed:
            decomposed.append(
                DecomposedClaim(
                    claim_id=f"{bullet_ref}.claim_1",
                    bullet_ref=bullet_ref,
                    action_text=text,
                    claimed_metrics=list(cls.extract_numbers_and_metrics(text)),
                )
            )

        return decomposed

    @classmethod
    def collect_candidate_facts(cls, candidate: Candidate) -> List[Dict[str, Any]]:
        """
        Gom toàn bộ các sự thật (Facts) có sẵn từ FactGraph thành danh sách tham chiếu.
        """
        fact_nodes = fact_graph_builder.build_fact_graph(candidate)
        facts: List[Dict[str, Any]] = []

        for fid, fnode in fact_nodes.items():
            facts.append({
                "source_entity_type": fnode.entity_type,
                "source_entity_id": fnode.entity_id,
                "fact_text": fnode.raw_statement,
                "technologies": fnode.technologies,
                "metrics": [m.raw_token for m in fnode.metrics],
                "fact_id": fid,
            })

        # Bổ sung raw master resume nếu có
        if getattr(candidate, "raw_master_resume_tex", None):
            facts.append({
                "source_entity_type": "MASTER_RESUME",
                "source_entity_id": "master-resume.tex",
                "fact_text": candidate.raw_master_resume_tex,
                "technologies": [],
                "metrics": list(cls.extract_numbers_and_metrics(candidate.raw_master_resume_tex)),
                "fact_id": "master_resume.raw",
            })

        return facts

    @classmethod
    def verify_claim(
        cls,
        claim_text: str,
        section: str,
        bullet_index: int,
        candidate_facts: List[Dict[str, Any]],
        all_candidate_metrics: Set[str],
    ) -> EvidenceMapItem:
        """
        Kiểm tra 1 bullet point / claim trong CV đối soát với Fact Graph.
        """
        claim_metrics = cls.extract_numbers_and_metrics(claim_text)

        # 1. Structured / Semantic Fact Matching
        best_match_fact = None
        best_score = 0.0

        for f in candidate_facts:
            fact_str = f["fact_text"]
            p_score = fuzz.partial_ratio(claim_text.lower(), fact_str.lower())
            t_score = fuzz.token_set_ratio(claim_text.lower(), fact_str.lower())
            score = max(p_score, t_score)
            if score > best_score:
                best_score = score
                best_match_fact = f

        # 2. Metric Integrity Check
        is_verified = True
        notes = []

        # Các số thông thường bỏ qua kiểm tra hallucination (ví dụ: năm, thứ tự)
        unverified_metrics = {
            m for m in claim_metrics - all_candidate_metrics
            if m not in {"1", "2", "3", "4", "5", "2022", "2025", "2026", "Oct", "Expected"}
        }

        if unverified_metrics and best_score < 80.0:
            is_verified = False
            notes.append(f"Unverified metrics detected: {', '.join(unverified_metrics)}")

        if best_score < 50.0 and is_verified:
            is_verified = False
            notes.append(f"Low semantic support (Score: {best_score:.1f})")

        status = ClaimVerificationStatus.VERIFIED if is_verified else ClaimVerificationStatus.UNVERIFIED
        if not is_verified and unverified_metrics:
            status = ClaimVerificationStatus.CONFLICTING

        similarity_norm = min(1.0, max(0.0, best_score / 100.0))

        return EvidenceMapItem(
            section=section,
            bullet_index=bullet_index,
            claim_text=claim_text,
            source_entity_type=best_match_fact["source_entity_type"] if best_match_fact else "UNKNOWN",
            source_entity_id=best_match_fact["source_entity_id"] if best_match_fact else None,
            original_fact=best_match_fact["fact_text"] if best_match_fact else "No matching fact found",
            is_verified=is_verified,
            similarity_score=round(similarity_norm, 4),
            notes="; ".join(notes) if notes else "Fact verified with Ground Truth",
        )

    @classmethod
    def verify_resume(
        cls,
        candidate: Candidate,
        tailored_sections: Dict[str, List[str]],
    ) -> Tuple[List[EvidenceMapItem], float, bool]:
        """
        Kiểm chứng toàn diện các sections của Resume.
        Trả về: (evidence_items, provenance_score, is_verified).
        """
        candidate_facts = cls.collect_candidate_facts(candidate)

        # Gom toàn bộ metrics có trong facts
        all_metrics: Set[str] = set()
        for f in candidate_facts:
            all_metrics.update(f.get("metrics", []))
            all_metrics.update(cls.extract_numbers_and_metrics(f["fact_text"]))

        evidence_items: List[EvidenceMapItem] = []
        verified_count = 0
        total_items = 0

        for section_name, claims in tailored_sections.items():
            for idx, claim in enumerate(claims):
                if not claim or not claim.strip():
                    continue
                total_items += 1
                ev_item = cls.verify_claim(
                    claim_text=claim,
                    section=section_name,
                    bullet_index=idx,
                    candidate_facts=candidate_facts,
                    all_candidate_metrics=all_metrics,
                )
                evidence_items.append(ev_item)
                if ev_item.is_verified:
                    verified_count += 1

        provenance_score = (verified_count / max(total_items, 1)) * 100.0
        provenance_score = round(provenance_score, 1)
        is_fully_verified = (provenance_score >= 90.0)

        logger.info(
            f"[ProvenanceVerifier] Checked {total_items} claims. Score: {provenance_score}%. Verified: {is_fully_verified}."
        )
        return evidence_items, provenance_score, is_fully_verified


provenance_verifier = ProvenanceVerifier()
