import re
from typing import Any, Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz

from app.models.candidate import Candidate
from app.schemas.resume import EvidenceMapItem


class ProvenanceVerifier:
    """
    Engine kiểm chứng nguồn gốc sự thật (Zero-Hallucination Provenance Engine):
    - Đảm bảo mọi claim, metric, con số và công nghệ trong CV được sinh ra đều bắt nguồn 100% từ
      context/master-resume.tex hoặc candidate-profile.yaml.
    - Phát hiện các con số/thành tích bịa đặt (hallucinated metrics).
    - Tính điểm tin cậy Provenance Score (0 - 100).
    """

    @staticmethod
    def extract_numbers_and_metrics(text: str) -> Set[str]:
        """Trích xuất tất cả các con số, phần trăm, độ trễ và thông số kỹ thuật định lượng."""
        if not text:
            return set()
        # Tìm số có đơn vị hoặc số độc lập (vd: 45ms, 200 req/min, 40%, 3.15, 64MB, AES-256)
        pattern = r"\b\d+(?:\.\d+)?(?:ms|s|%|req/min|req/10s|MB|GB|KB|POPs?|PoP)?\b"
        found = set(re.findall(pattern, text, re.IGNORECASE))
        return found

    @classmethod
    def collect_candidate_facts(cls, candidate: Candidate) -> List[Dict[str, Any]]:
        """
        Gom toàn bộ các sự thật (Facts) có sẵn từ candidate profile và master resume thành danh sách tham chiếu.
        """
        facts: List[Dict[str, Any]] = []

        # 1. Projects Facts
        if candidate.projects:
            for proj in candidate.projects:
                proj_name = proj.name
                if proj.summary:
                    facts.append({
                        "source_entity_type": "PROJECT",
                        "source_entity_id": proj_name,
                        "fact_text": f"{proj_name}: {proj.summary}",
                        "technologies": proj.technologies or [],
                    })

                if proj.evidence_points:
                    for idx, ev in enumerate(proj.evidence_points):
                        detail = ev.get("detail", "") if isinstance(ev, dict) else str(ev)
                        title = ev.get("title", "") if isinstance(ev, dict) else f"Evidence {idx+1}"
                        facts.append({
                            "source_entity_type": "PROJECT",
                            "source_entity_id": f"{proj_name}:{title}",
                            "fact_text": detail,
                            "technologies": proj.technologies or [],
                        })

        # 2. Experience Facts
        if candidate.experiences:
            for exp in candidate.experiences:
                if exp.description:
                    facts.append({
                        "source_entity_type": "EXPERIENCE",
                        "source_entity_id": f"{exp.company}:{exp.role}",
                        "fact_text": exp.description,
                        "technologies": [],
                    })
                if exp.achievements:
                    for ach in exp.achievements:
                        facts.append({
                            "source_entity_type": "EXPERIENCE",
                            "source_entity_id": f"{exp.company}:{exp.role}",
                            "fact_text": str(ach),
                            "technologies": [],
                        })

        # 3. Education Facts
        if candidate.education:
            for edu in candidate.education:
                if isinstance(edu, dict):
                    edu_text = f"{edu.get('institution', '')} {edu.get('degree', '')} {edu.get('field', '')} GPA: {edu.get('gpa', '')} Coursework: {', '.join(edu.get('coursework', []))}"
                    facts.append({
                        "source_entity_type": "EDUCATION",
                        "source_entity_id": edu.get("institution", "University"),
                        "fact_text": edu_text,
                        "technologies": [],
                    })

        # 4. Raw Master Resume Text
        if candidate.raw_master_resume_tex:
            facts.append({
                "source_entity_type": "MASTER_RESUME",
                "source_entity_id": "master-resume.tex",
                "fact_text": candidate.raw_master_resume_tex,
                "technologies": [],
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
        Kiểm tra 1 bullet point / claim trong CV đối soát với toàn bộ sự thật của ứng viên.
        """
        claim_metrics = cls.extract_numbers_and_metrics(claim_text)
        
        # Tìm fact có độ tương đồng cao nhất
        best_match_fact = None
        best_score = 0.0

        for f in candidate_facts:
            fact_str = f["fact_text"]
            # RapidFuzz: kết hợp partial_ratio và token_set_ratio để bắt chính xác cả trích đoạn lẫn paraphrase
            p_score = fuzz.partial_ratio(claim_text.lower(), fact_str.lower())
            t_score = fuzz.token_set_ratio(claim_text.lower(), fact_str.lower())
            score = max(p_score, t_score)
            if score > best_score:
                best_score = score
                best_match_fact = f

        # Kiểm tra metric hallucination
        is_verified = True
        notes = []

        unverified_metrics = claim_metrics - all_candidate_metrics
        # Loại bỏ các số nhỏ thông thường như 1, 2, 3 nếu là bullet count
        unverified_metrics = {m for m in unverified_metrics if m not in {"1", "2", "3", "2026"}}

        if unverified_metrics and best_score < 70.0:
            is_verified = False
            notes.append(f"Unverified metrics detected: {', '.join(unverified_metrics)}")

        if best_score < 50.0 and is_verified:
            is_verified = False
            notes.append(f"Low semantic support (Score: {best_score:.1f})")

        similarity_norm = min(1.0, max(0.0, best_score / 100.0))

        return EvidenceMapItem(
            section=section,
            bullet_index=bullet_index,
            claim_text=claim_text,
            source_entity_type=best_match_fact["source_entity_type"] if best_match_fact else "UNKNOWN",
            source_entity_id=best_match_fact["source_entity_id"] if best_match_fact else None,
            original_fact=best_match_fact["fact_text"][:300] if best_match_fact else "No matching fact found",
            is_verified=is_verified,
            similarity_score=round(similarity_norm, 2),
            notes="; ".join(notes) if notes else "Verified with candidate context",
        )

    @classmethod
    def verify_resume(
        cls,
        candidate: Candidate,
        tailored_sections: Dict[str, List[str]],
    ) -> Tuple[List[EvidenceMapItem], float, bool]:
        """
        Kiểm tra toàn bộ các mục trong CV được sinh ra.
        Trả về: (Danh sách EvidenceMapItem, Provenance Score 0-100, is_all_verified).
        """
        candidate_facts = cls.collect_candidate_facts(candidate)
        
        # Gom toàn bộ metrics hợp lệ của candidate
        all_metrics: Set[str] = set()
        for f in candidate_facts:
            all_metrics.update(cls.extract_numbers_and_metrics(f["fact_text"]))

        evidence_items: List[EvidenceMapItem] = []
        total_claims = 0
        verified_claims = 0

        for section_name, claims in tailored_sections.items():
            for idx, claim in enumerate(claims):
                if not claim or not claim.strip():
                    continue
                total_claims += 1
                item = cls.verify_claim(
                    claim_text=claim.strip(),
                    section=section_name,
                    bullet_index=idx,
                    candidate_facts=candidate_facts,
                    all_candidate_metrics=all_metrics,
                )
                evidence_items.append(item)
                if item.is_verified:
                    verified_claims += 1

        if total_claims == 0:
            score = 100.0
            is_verified = True
        else:
            score = round((verified_claims / total_claims) * 100.0, 1)
            is_verified = (score >= 90.0)

        return evidence_items, score, is_verified


provenance_verifier = ProvenanceVerifier()
