import logging
from typing import List, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger("embedding_service")


class EmbeddingService:
    """
    Service tạo vector embeddings (1536 chiều) phục vụ:
    1. Semantic Deduplication (Tầng 3)
    2. Phase 3: Matching Candidate Profile ↔ Job Description
    """

    def __init__(self):
        self.api_key = getattr(settings, "OPENAI_API_KEY", None)
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Tạo vector embedding 1536 chiều từ văn bản.
        Trả về None nếu không có API key hoặc lỗi.
        """
        if not text or not text.strip():
            return None

        if not self.client:
            return None

        try:
            # Rút gọn text nếu quá dài
            clean_text = text[:8000].replace("\n", " ")
            response = await self.client.embeddings.create(
                input=[clean_text],
                model=self.model,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None


# Singleton Instance
embedding_service = EmbeddingService()
