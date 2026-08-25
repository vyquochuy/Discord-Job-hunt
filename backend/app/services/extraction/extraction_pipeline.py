import logging
from typing import Optional

from app.core.config import settings
from app.services.ai.llm_extractor import llm_extractor
from app.services.extraction.heuristic_extractor import (
    ExtractionResult,
    FieldConfidence,
    heuristic_extractor,
)

logger = logging.getLogger("extraction_pipeline")


class JobExtractionPipeline:
    """
    Pipeline điều phối quá trình trích xuất:
    1. Chạy Heuristic Extractor siêu tốc với đánh giá Confidence per-field.
    2. Nếu Confidence >= Threshold -> Chấp nhận kết quả Heuristic (0 LLM Cost).
    3. Nếu Confidence < Threshold và có LLM -> Fallback gọi Structured LLM Extractor để hoàn thiện.
    4. Nếu không có LLM -> Trả về kết quả Heuristic kèm trạng thái PARTIAL và warnings.
    """

    def __init__(self, confidence_threshold: float = 0.65):
        self.confidence_threshold = confidence_threshold

    async def extract(
        self,
        clean_text: str,
        initial_title: Optional[str] = None,
        use_llm: Optional[bool] = None,
    ) -> ExtractionResult:
        """
        Trích xuất thông tin việc làm từ văn bản thuần túy.
        """
        # BƯỚC 1: Chạy Heuristic Extractor trước
        result = heuristic_extractor.extract(clean_text, initial_title=initial_title)

        # Quyết định có cần gọi LLM không
        # Nếu use_llm=True tường minh -> bắt buộc gọi
        # Nếu use_llm=False tường minh -> không gọi
        # Nếu use_llm=None -> tự động quyết định dựa trên confidence_threshold
        should_call_llm = False
        if use_llm is True:
            should_call_llm = True
        elif use_llm is False:
            should_call_llm = False
        else:
            should_call_llm = result.overall_confidence < self.confidence_threshold

        # BƯỚC 2: Gọi LLM nếu cần và có cấu hình OpenAI
        has_openai = bool(getattr(settings, "OPENAI_API_KEY", None))
        if should_call_llm and has_openai:
            try:
                logger.info(
                    f"Heuristic confidence {result.overall_confidence} < {self.confidence_threshold}. "
                    "Invoking LLM Structured Extraction fallback..."
                )
                llm_data = await llm_extractor.extract_job_details(clean_text, result.data)

                # Merge kết quả LLM vào extraction result
                merged_fields = []
                for fc in result.fields:
                    if fc.field == "skills" and llm_data.skills_required:
                        merged_fields.append(FieldConfidence(
                            field="skills",
                            detected=True,
                            confidence=0.95,
                            value={"required": llm_data.skills_required, "nice_to_have": llm_data.skills_nice_to_have},
                            method="llm"
                        ))
                    elif fc.field == "level" and llm_data.level.value != "UNKNOWN":
                        merged_fields.append(FieldConfidence(
                            field="level",
                            detected=True,
                            confidence=0.90,
                            value=llm_data.level.value,
                            method="llm"
                        ))
                    else:
                        merged_fields.append(fc)

                # Cập nhật lại overall confidence sau khi có LLM
                new_conf = round(min(1.0, max(result.overall_confidence + 0.25, 0.85)), 2)
                return ExtractionResult(
                    data=llm_data,
                    method="heuristic+llm",
                    overall_confidence=new_conf,
                    fields=merged_fields,
                    warnings=result.warnings,
                    extraction_status="PARSED" if new_conf >= self.confidence_threshold else "PARTIAL",
                )
            except Exception as e:
                logger.warning(f"LLM extraction fallback failed: {e}. Keeping heuristic result.")
                result.warnings.append(f"LLM extraction attempt failed: {str(e)}")

        return result


extraction_pipeline = JobExtractionPipeline()
