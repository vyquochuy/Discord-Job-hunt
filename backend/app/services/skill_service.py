import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import SkillCategoryEnum
from app.repositories.skill import SkillRepository
from app.schemas.job import DesiredJobSkill
from app.services.normalization.skill_normalizer import SkillNormalizer, skill_normalizer as default_normalizer

logger = logging.getLogger(__name__)


class SkillService:
    """
    Domain Service quản lý nghiệp vụ chuẩn hóa, gộp (merge) và đối soát kỹ năng của Job,
    độc lập hoàn toàn khỏi SQLAlchemy ORM model JobSkill.
    """

    def __init__(
        self,
        skill_repo: Optional[SkillRepository] = None,
        normalizer: Optional[SkillNormalizer] = None,
    ):
        self.skill_repo = skill_repo or SkillRepository()
        self.normalizer = normalizer or default_normalizer

    def merge_job_skills(
        self,
        required_skills: List[Any],
        nice_skills: List[Any],
        default_required_conf: float = 1.0,
        default_nice_conf: float = 0.85,
        default_required_source: str = "explicit",
        default_nice_source: str = "inferred",
    ) -> List[DesiredJobSkill]:
        """
        Chuẩn hóa, gộp và phân giải xung đột giữa kỹ năng Bắt buộc (Required) và Ưu tiên (Nice-to-have).
        
        Quy tắc nghiệp vụ:
        1. Precedence: Nếu một skill xuất hiện ở cả hai nơi, is_required=True (Required) luôn thắng.
        2. Confidence Resolution: Giữ giá trị lớn nhất max(conf_req, conf_nice), không gán cứng 1.0.
        3. Provenance Source: Ưu tiên source của required tier nếu trùng.
        """
        merged: Dict[str, Dict[str, Any]] = {}

        def _process_item(
            item: Any,
            is_req: bool,
            def_conf: float,
            def_source: str,
        ) -> None:
            if not item:
                return

            canonical: Optional[str] = None
            category: SkillCategoryEnum = SkillCategoryEnum.OTHER
            confidence: float = def_conf
            source: str = def_source

            if isinstance(item, str):
                norm_c, norm_cat = self.normalizer.normalize_skill(item)
                if norm_c:
                    canonical = norm_c
                    category = norm_cat
            elif isinstance(item, (tuple, list)):
                if len(item) >= 2:
                    canonical = str(item[0])
                    category = item[1] if isinstance(item[1], SkillCategoryEnum) else SkillCategoryEnum.OTHER
                if len(item) >= 3 and isinstance(item[2], (int, float)):
                    confidence = float(item[2])
                if len(item) >= 4 and isinstance(item[3], str):
                    source = item[3]
            elif isinstance(item, DesiredJobSkill):
                canonical = item.canonical_name
                category = item.category
                confidence = item.confidence
                source = item.source
                is_req = item.is_required

            if not canonical:
                return

            if canonical in merged:
                existing = merged[canonical]
                existing["is_required"] = existing["is_required"] or is_req
                existing["confidence"] = max(existing["confidence"], confidence)
                if existing["category"] == SkillCategoryEnum.OTHER and category != SkillCategoryEnum.OTHER:
                    existing["category"] = category
                if is_req:
                    existing["source"] = source
            else:
                merged[canonical] = {
                    "canonical_name": canonical,
                    "category": category,
                    "is_required": is_req,
                    "confidence": confidence,
                    "source": source,
                }

        for item in required_skills:
            _process_item(item, is_req=True, def_conf=default_required_conf, def_source=default_required_source)

        for item in nice_skills:
            _process_item(item, is_req=False, def_conf=default_nice_conf, def_source=default_nice_source)

        return [
            DesiredJobSkill(
                canonical_name=data["canonical_name"],
                category=data["category"],
                is_required=data["is_required"],
                confidence=data["confidence"],
                source=data["source"],
            )
            for data in merged.values()
        ]

    async def sync_job_skills(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        norm_required: List[Any],
        norm_nice: List[Any],
        source: Optional[str] = None,
        required_conf: float = 1.0,
        nice_conf: float = 0.85,
    ) -> List[DesiredJobSkill]:
        """
        Đồng bộ toàn bộ danh mục kỹ năng của một Job vào database theo cơ chế Declarative Reconciliation.
        
        Invariant:
        - Số lượng queries cho toàn bộ danh mục là O(1), không có per-skill loop.
        - Idempotent: gọi nhiều lần cho cùng 1 desired state cho ra kết quả DB giống nhau.
        - Không bao giờ commit session. Outer pipeline sở hữu transaction boundary.
        """
        req_src = source or "explicit"
        nice_src = "inferred"

        desired_skills = self.merge_job_skills(
            required_skills=norm_required,
            nice_skills=norm_nice,
            default_required_conf=required_conf,
            default_nice_conf=nice_conf,
            default_required_source=req_src,
            default_nice_source=nice_src,
        )

        if not desired_skills:
            await self.skill_repo.reconcile_job_skills(session, job_id, [], {})
            return []

        canonical_names = [s.canonical_name for s in desired_skills]

        # 1. Bulk resolve skills đã có trong DB
        skill_lookup = await self.skill_repo.resolve_skills_bulk(session, canonical_names)

        # 2. Phát hiện và bulk ensure missing skills
        missing_skills = [
            s for s in desired_skills if s.canonical_name not in skill_lookup
        ]
        if missing_skills:
            newly_created = await self.skill_repo.ensure_missing_skills(session, missing_skills)
            skill_lookup.update(newly_created)

        # 3. Reconcile quan hệ JobSkill (diffing insert/update/delete)
        await self.skill_repo.reconcile_job_skills(session, job_id, desired_skills, skill_lookup)

        return desired_skills


skill_service = SkillService()
