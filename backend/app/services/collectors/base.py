import abc
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.job import JobExtractedData


class RawJobData(BaseModel):
    """DTO truyền dữ liệu thô thu thập được từ Collector về Ingestion Pipeline."""
    source: str
    source_url: str
    source_job_id: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    raw_html: Optional[str] = None
    content_hash: str = Field(..., description="SHA-256 hash của nội dung thực tế")


class BaseJobCollector(abc.ABC):
    """
    Lớp cơ sở trừu tượng cho tất cả các Job Collector Source Adapters.
    """

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Tên định danh nguồn (VD: 'itviec', 'remotive', 'topcv')."""
        pass

    @abc.abstractmethod
    async def fetch_jobs(self, limit: int = 20) -> List[RawJobData]:
        """Thu thập danh sách tin thô từ nguồn."""
        pass

    @abc.abstractmethod
    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        """Bóc tách thô (Deterministic Parsing) từ RawJobData thành JobExtractedData."""
        pass

    @staticmethod
    def compute_content_hash(content: Any) -> str:
        """
        Tính SHA-256 hash của nội dung tin tuyển dụng để kiểm tra thay đổi.
        Hỗ trợ cả dict, list và text string.
        """
        if isinstance(content, (dict, list)):
            serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
        else:
            serialized = str(content or "").strip()

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
