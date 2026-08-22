import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.matching.models import (
    CandidateProfileDTO,
    Eligibility,
    EvidenceStatus,
    JobMatchInputDTO,
    MatchScoreResult,
    RecommendationCategory,
)


logger = logging.getLogger("explanation_service")


class MatchExplanationService:
    """
    Service sinh nhận xét/giải thích lý do so khớp (Explainable Matching).
    - LLM chỉ đóng vai trò diễn đạt tự nhiên dựa trên các sự thật đã được tính toán sẵn.
    - Tuyệt đối không thay đổi điểm số hay kết luận từ engine.
    - Cung cấp Template Fallback 100% deterministic khi offline hoặc không có API key.
    """

    def __init__(self):
        self.api_key = getattr(settings, "OPENAI_API_KEY", None)
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    def _compute_input_hash(self, score_result: MatchScoreResult) -> str:
        """Tạo SHA-256 hash của signals data để kiểm tra/truy vết audit."""
        signals_json = json.dumps(
            [s.model_dump() for s in score_result.signals], sort_keys=True
        )
        return hashlib.sha256(signals_json.encode("utf-8")).hexdigest()

    def generate_deterministic_explanation(
        self,
        candidate: CandidateProfileDTO,
        job: JobMatchInputDTO,
        score_result: MatchScoreResult,
    ) -> Tuple[str, Dict[str, Any]]:
        """Sinh nhận xét bằng Template hoàn toàn Deterministic (Zero Cost, Zero Hallucination)."""
        input_hash = self._compute_input_hash(score_result)
        lines = []

        # 1. Tổng kết trạng thái và khuyến nghị
        if score_result.eligibility == Eligibility.BLOCKED:
            lines.append(f"⛔ **KHÔNG PHÙ HỢP ỨNG TUYỂN** (Điểm match: {score_result.score:.0f}/100)")
            lines.append("Lý do bị chặn bởi các tiêu chí cứng:")
            for r in score_result.eligibility_reasons:
                lines.append(f"• {r}")
        elif score_result.recommendation == RecommendationCategory.STRONG_MATCH:
            lines.append(f"🌟 **RẤT PHÙ HỢP ({score_result.score:.0f}/100 - STRONG MATCH)**")
            lines.append(f"Hồ sơ của bạn đáp ứng xuất sắc các yêu cầu trọng tâm của vị trí {job.title} tại {job.company_name}.")
        elif score_result.recommendation == RecommendationCategory.GOOD_MATCH:
            lines.append(f"✅ **PHÙ HỢP TỐT ({score_result.score:.0f}/100 - GOOD MATCH)**")
            lines.append(f"Bạn đáp ứng phần lớn các yêu cầu của {job.title} nhưng còn một số điểm cần lưu ý.")
        elif score_result.recommendation == RecommendationCategory.REVIEW_REQUIRED:
            lines.append(f"⚠️ **CẦN XEM XÉT THÊM ({score_result.score:.0f}/100 - REVIEW REQUIRED)**")
            lines.append("Điểm số kỹ năng tốt nhưng có một số thông tin cần bạn xác nhận thêm:")
            for r in score_result.eligibility_reasons:
                lines.append(f"• {r}")
        elif score_result.recommendation == RecommendationCategory.WEAK_MATCH:
            lines.append(f"⚠️ **PHÙ HỢP YẾU ({score_result.score:.0f}/100 - WEAK MATCH)**")
            lines.append("Còn thiếu khá nhiều kỹ năng hoặc kinh nghiệm cần thiết cho vị trí này.")
        else:
            lines.append(f"❌ **MỨC ĐỘ PHÙ HỢP THẤP ({score_result.score:.0f}/100 - POOR MATCH)**")
            lines.append("Hồ sơ hiện tại chưa tương thích với yêu cầu công việc.")

        # 2. Điểm mạnh năng lực & bằng chứng
        if score_result.requirement_evaluations:
            supported_reqs = [
                f"• **{e.requirement.name}**: {e.reason}"
                for e in score_result.requirement_evaluations
                if e.status == EvidenceStatus.SUPPORTED
            ]
            if supported_reqs:
                lines.append("\n**Bằng chứng năng lực phù hợp:**")
                lines.extend(supported_reqs[:4])

        # 3. Điểm mạnh kỹ năng
        if score_result.skill_match.matched_required:
            skills_str = ", ".join(score_result.skill_match.matched_required)
            lines.append(f"\n**Kỹ năng kỹ thuật:** Đáp ứng công nghệ: {skills_str}.")

        # 4. Kỹ năng còn thiếu
        if score_result.skill_match.missing_required:
            missing_str = ", ".join(score_result.skill_match.missing_required)
            lines.append(f"**Kỹ năng còn thiếu:** {missing_str}.")

        if score_result.skill_match.missing_preferred and len(score_result.skill_match.missing_preferred) > 0:
            pref_str = ", ".join(score_result.skill_match.missing_preferred)
            lines.append(f"**Kỹ năng ưu tiên gợi ý học thêm:** {pref_str}.")


        # 4. Cảnh báo (nếu có)
        if score_result.warnings:
            lines.append("\n**Lưu ý:**")
            for w in score_result.warnings:
                lines.append(f"• {w}")

        explanation_text = "\n".join(lines)

        raw_payload = {
            "generated_by": "deterministic",
            "explanation_version": "v1",
            "model": None,
            "prompt_version": None,
            "input_hash": input_hash,
        }

        return explanation_text, raw_payload

    async def generate_explanation(
        self,
        candidate: CandidateProfileDTO,
        job: JobMatchInputDTO,
        score_result: MatchScoreResult,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Sinh nhận xét bằng LLM (nếu có API Key) hoặc Fallback về Template Deterministic.
        """
        # Nếu không có OpenAI Key -> dùng template
        if not self.client:
            return self.generate_deterministic_explanation(candidate, job, score_result)

        input_hash = self._compute_input_hash(score_result)

        system_prompt = """You are an AI Career Advisor. Your task is to generate a concise, encouraging, and structured Vietnamese explanation for a candidate regarding their match analysis for a job.
STRICT RULES:
1. Do NOT calculate or alter the score. Use the exact score and recommendation category provided.
2. Ground all points strictly in the provided signals, matched skills, and missing requirements. Do not hallucinate qualifications.
3. Structure your response with:
   - Summary & Recommendation verdict
   - Key Strengths (relevant skills & projects)
   - Gaps & Missing Requirements (skills to learn or highlight)
   - Actionable Advice for Tailoring Resume or Applying."""

        user_content = json.dumps({
            "candidate_name": candidate.full_name,
            "job_title": job.title,
            "company": job.company_name,
            "score": score_result.score,
            "eligibility": score_result.eligibility.value,
            "eligibility_reasons": score_result.eligibility_reasons,
            "recommendation": score_result.recommendation.value,
            "matched_required_skills": score_result.skill_match.matched_required,
            "missing_required_skills": score_result.skill_match.missing_required,
            "missing_preferred_skills": score_result.skill_match.missing_preferred,
            "warnings": score_result.warnings,
        }, ensure_ascii=False)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            content = response.choices[0].message.content
            if content and len(content.strip()) > 20:
                raw_payload = {
                    "generated_by": "llm",
                    "explanation_version": "v1",
                    "model": self.model,
                    "prompt_version": "match-explanation-v1",
                    "input_hash": input_hash,
                }
                return content.strip(), raw_payload
        except Exception as e:
            logger.warning(f"LLM explanation generation failed: {e}. Using deterministic template fallback.")

        return self.generate_deterministic_explanation(candidate, job, score_result)


explanation_service = MatchExplanationService()
