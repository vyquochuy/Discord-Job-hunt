import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.schemas.tailoring_ir import (
    EvidenceBundle,
    EvidenceFact,
    GeneratedBullet,
    GeneratedClaimFragment,
    GeneratedProject,
    GeneratedSummary,
    StructuredResumeDraft,
    ValidationViolation,
)
from app.services.tailoring.deterministic_composer import deterministic_composer
from app.services.tailoring.prompts.resume_prompts import (
    RESUME_WRITER_SYSTEM_PROMPT,
    build_bullet_regeneration_prompt,
    build_resume_generation_prompt,
)

logger = logging.getLogger("gemini_resume_writer")


class ResumeSemanticWriter:
    """
    Gemini Semantic Resume Writer:
    - Chịu trách nhiệm may đo ngữ nghĩa (Semantic Rewriting) cho Resume dựa trên EvidenceBundle.
    - Đảm bảo tuân thủ mô hình Structured JSON Output.
    - Model và API Key được cấu hình linh hoạt qua biến môi trường (không hardcode).
    - Hỗ trợ gọi Unit-Level Regeneration cho từng bullet độc lập bị lỗi kiểm chứng.
    - Tự động chuyển tiếp qua DeterministicResumeComposer khi không có API Key hoặc chạy offline.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "GOOGLE_API_KEY", None) or getattr(settings, "OPENAI_API_KEY", None)
        self.api_base_url = api_base_url or getattr(settings, "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

    async def _call_gemini_json(self, system_instruction: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Gọi REST API của Gemini với định dạng Structured JSON mode."""
        if not self.api_key:
            return None

        # Endpoint format for Google Gemini v1beta REST API:
        # POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}
        url = f"{self.api_base_url}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
                    return None
                
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None
                
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    return None
                
                raw_text = parts[0].get("text", "").strip()
                return json.loads(raw_text)

        except Exception as e:
            logger.warning(f"Error communicating with Gemini API: {e}. Falling back to deterministic composition.")
            return None

    async def generate_resume_draft(self, bundle: EvidenceBundle) -> StructuredResumeDraft:
        """
        Sinh bản StructuredResumeDraft đầy đủ từ EvidenceBundle.
        Nếu không có API Key hoặc gọi API lỗi, sử dụng DeterministicResumeComposer.
        """
        if not self.api_key:
            logger.info("[ResumeSemanticWriter] No Gemini API key detected. Using DeterministicResumeComposer.")
            return deterministic_composer.compose_draft(bundle)

        user_prompt = build_resume_generation_prompt(bundle)
        raw_json = await self._call_gemini_json(
            system_instruction=RESUME_WRITER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        if not raw_json:
            logger.info("[ResumeSemanticWriter] Gemini call failed or returned empty. Using DeterministicResumeComposer fallback.")
            return deterministic_composer.compose_draft(bundle)

        try:
            # Parse vào Pydantic model StructuredResumeDraft
            draft = StructuredResumeDraft.model_validate(raw_json)
            logger.info(f"[ResumeSemanticWriter] Successfully generated draft with model='{self.model}'.")
            return draft
        except Exception as e:
            logger.warning(f"[ResumeSemanticWriter] Failed to parse Gemini response into StructuredResumeDraft: {e}. Using fallback.")
            return deterministic_composer.compose_draft(bundle)

    async def regenerate_bullet(
        self,
        unit_id: str,
        project_name: str,
        failed_text: str,
        violations: List[ValidationViolation],
        supported_evidence_facts: List[EvidenceFact],
        target_role: str,
    ) -> GeneratedBullet:
        """
        Tái sinh (Regenerate) DUY NHẤT một bullet bị vi phạm kiểm chứng.
        Nếu không có API key hoặc API lỗi, lấy deterministic fallback cho fact đầu tiên.
        """
        if not self.api_key or not supported_evidence_facts:
            fallback_fact = supported_evidence_facts[0] if supported_evidence_facts else None
            if fallback_fact:
                return deterministic_composer.compose_bullet(fallback_fact)
            return GeneratedBullet(
                text=failed_text,
                evidence_ids=[],
                claims=[],
            )

        user_prompt = build_bullet_regeneration_prompt(
            unit_id=unit_id,
            project_name=project_name,
            failed_text=failed_text,
            violations=violations,
            supported_evidence_facts=supported_evidence_facts,
            target_role=target_role,
        )

        raw_json = await self._call_gemini_json(
            system_instruction=RESUME_WRITER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        if not raw_json:
            fallback_fact = supported_evidence_facts[0]
            return deterministic_composer.compose_bullet(fallback_fact)

        try:
            return GeneratedBullet.model_validate(raw_json)
        except Exception as e:
            logger.warning(f"[ResumeSemanticWriter] Failed to parse regenerated bullet: {e}. Using deterministic fallback.")
            fallback_fact = supported_evidence_facts[0]
            return deterministic_composer.compose_bullet(fallback_fact)

    async def regenerate_summary(
        self,
        failed_text: str,
        violations: List[ValidationViolation],
        bundle: EvidenceBundle,
    ) -> GeneratedSummary:
        """Tái sinh duy nhất đoạn Professional Summary."""
        if not self.api_key:
            return deterministic_composer.compose_summary(bundle)

        return deterministic_composer.compose_summary(bundle)


resume_semantic_writer = ResumeSemanticWriter()
