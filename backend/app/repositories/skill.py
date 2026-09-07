import logging
import uuid
from typing import Dict, List, Optional, Set
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Skill, JobSkill, SkillCategoryEnum
from app.schemas.job import DesiredJobSkill

logger = logging.getLogger(__name__)


class SkillRepository:
    """
    Repository phụ trách lưu trữ, truy vấn và đối soát (reconcile) danh mục Skill
    và quan hệ JobSkill trong cơ sở dữ liệu.
    """

    @staticmethod
    async def resolve_skills_bulk(
        session: AsyncSession,
        canonical_names: List[str]
    ) -> Dict[str, Skill]:
        """
        Truy vấn bulk các skills đã có trong database theo danh sách canonical_name.
        Độ phức tạp I/O: 1 câu query SQL duy nhất (O(1) roundtrip).
        """
        if not canonical_names:
            return {}

        unique_names = list(set(name for name in canonical_names if name))
        if not unique_names:
            return {}

        stmt = select(Skill).where(Skill.canonical_name.in_(unique_names))
        result = await session.execute(stmt)
        skills = result.scalars().all()
        return {s.canonical_name: s for s in skills}

    @staticmethod
    async def ensure_missing_skills(
        session: AsyncSession,
        missing_skills: List[DesiredJobSkill]
    ) -> Dict[str, Skill]:
        """
        Bulk insert các kỹ năng chưa có trong DB với cơ chế dialect-aware upsert (ON CONFLICT DO NOTHING),
        chống race condition khi có nhiều tasks/workers cùng cào một skill mới tinh.
        Sau đó truy vấn lại để trả về dict đầy đủ {canonical_name: Skill}.
        """
        if not missing_skills:
            return {}

        unique_missing: Dict[str, DesiredJobSkill] = {}
        for s in missing_skills:
            if s.canonical_name and s.canonical_name not in unique_missing:
                unique_missing[s.canonical_name] = s

        if not unique_missing:
            return {}

        try:
            bind = session.get_bind()
            dialect_name = bind.dialect.name if bind else "postgresql"
        except Exception:
            dialect_name = "postgresql"

        values = [
            {
                "id": uuid.uuid4(),
                "canonical_name": ds.canonical_name,
                "category": ds.category,
            }
            for ds in unique_missing.values()
        ]

        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = (
                pg_insert(Skill)
                .values(values)
                .on_conflict_do_nothing(index_elements=["canonical_name"])
            )
            await session.execute(stmt)
        elif dialect_name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = (
                sqlite_insert(Skill)
                .values(values)
                .on_conflict_do_nothing(index_elements=["canonical_name"])
            )
            await session.execute(stmt)
        else:
            for val in values:
                existing = await session.execute(
                    select(Skill).where(Skill.canonical_name == val["canonical_name"])
                )
                if not existing.scalars().first():
                    session.add(Skill(**val))
            await session.flush()

        stmt_reload = select(Skill).where(
            Skill.canonical_name.in_(list(unique_missing.keys()))
        )
        res_reload = await session.execute(stmt_reload)
        return {s.canonical_name: s for s in res_reload.scalars().all()}

    @staticmethod
    async def reconcile_job_skills(
        session: AsyncSession,
        job_id: uuid.UUID,
        desired_skills: List[DesiredJobSkill],
        skill_lookup: Dict[str, Skill],
    ) -> None:
        """
        Thực hiện Declarative Reconciliation giữa Desired State và Database State:
        - desired - existing  -> Bulk INSERT
        - existing ∩ desired  -> UPDATE nếu có thay đổi metadata (is_required, confidence, source)
        - existing - desired  -> Bulk DELETE
        Độ phức tạp I/O: Tối đa 1 SELECT + 1 INSERT/DELETE/UPDATE bulk, không có per-skill loop!
        Tuyệt đối không commit transaction tại đây.
        """
        desired_by_skill_id: Dict[uuid.UUID, DesiredJobSkill] = {}
        for ds in desired_skills:
            skill_obj = skill_lookup.get(ds.canonical_name)
            if skill_obj:
                desired_by_skill_id[skill_obj.id] = ds

        stmt = select(JobSkill).where(JobSkill.job_id == job_id)
        res = await session.execute(stmt)
        existing_job_skills = res.scalars().all()
        existing_by_skill_id: Dict[uuid.UUID, JobSkill] = {
            js.skill_id: js for js in existing_job_skills
        }

        desired_skill_ids = set(desired_by_skill_id.keys())
        existing_skill_ids = set(existing_by_skill_id.keys())

        # 1. TO INSERT: desired - existing
        to_insert_ids = desired_skill_ids - existing_skill_ids
        if to_insert_ids:
            new_job_skills = [
                JobSkill(
                    job_id=job_id,
                    skill_id=s_id,
                    is_required=desired_by_skill_id[s_id].is_required,
                    confidence=desired_by_skill_id[s_id].confidence,
                    source=desired_by_skill_id[s_id].source,
                )
                for s_id in to_insert_ids
            ]
            session.add_all(new_job_skills)

        # 2. TO UPDATE: existing ∩ desired
        to_update_ids = desired_skill_ids & existing_skill_ids
        for s_id in to_update_ids:
            current_js = existing_by_skill_id[s_id]
            target_ds = desired_by_skill_id[s_id]

            if current_js.is_required != target_ds.is_required:
                current_js.is_required = target_ds.is_required
            if abs(current_js.confidence - target_ds.confidence) > 1e-4:
                current_js.confidence = target_ds.confidence
            if current_js.source != target_ds.source:
                current_js.source = target_ds.source

        # 3. TO DELETE: existing - desired
        to_delete_ids = list(existing_skill_ids - desired_skill_ids)
        if to_delete_ids:
            await session.execute(
                delete(JobSkill).where(
                    JobSkill.job_id == job_id,
                    JobSkill.skill_id.in_(to_delete_ids),
                )
            )
