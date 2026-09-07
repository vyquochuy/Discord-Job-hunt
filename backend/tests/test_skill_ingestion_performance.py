import asyncio
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.job import Job, JobSkill, JobStatusEnum, RawJob, RawJobStatusEnum, Skill, SkillCategoryEnum
from app.repositories.skill import SkillRepository
from app.schemas.job import DesiredJobSkill
from app.services.skill_service import SkillService


# ==============================================================================
# 1. UNIT TESTS: Domain Logic, Precedence Rules & Confidence Resolution
# ==============================================================================

def test_merge_job_skills_required_only():
    service = SkillService()
    required = [("Python", SkillCategoryEnum.LANGUAGE), ("FastAPI", SkillCategoryEnum.FRAMEWORK)]
    nice = []

    results = service.merge_job_skills(required, nice)
    assert len(results) == 2
    for r in results:
        assert r.is_required is True
        assert r.confidence == 1.0
        assert r.source == "explicit"


def test_merge_job_skills_nice_only():
    service = SkillService()
    required = []
    nice = [("Docker", SkillCategoryEnum.TOOL), ("Kubernetes", SkillCategoryEnum.TOOL)]

    results = service.merge_job_skills(required, nice)
    assert len(results) == 2
    for r in results:
        assert r.is_required is False
        assert r.confidence == 0.85
        assert r.source == "inferred"


def test_merge_job_skills_duplicate_precedence_and_max_confidence():
    """
    Khi một skill xuất hiện ở cả Required và Nice-to-have:
    1. Precedence: is_required=True luôn thắng.
    2. Confidence: Giữ max(conf_req, conf_nice), không bao giờ bị ép cứng về 1.0.
    """
    service = SkillService()
    # Required có Docker với confidence 0.8
    required = [("Docker", SkillCategoryEnum.TOOL, 0.8, "explicit")]
    # Nice-to-have có Docker với confidence 0.95
    nice = [("Docker", SkillCategoryEnum.TOOL, 0.95, "inferred")]

    results = service.merge_job_skills(required, nice)
    assert len(results) == 1
    docker_skill = results[0]

    assert docker_skill.canonical_name == "Docker"
    # Required thắng
    assert docker_skill.is_required is True
    # Giữ max confidence (0.95 thay vì 0.8 hoặc 1.0)
    assert docker_skill.confidence == 0.95
    assert docker_skill.source == "explicit"


def test_merge_job_skills_empty_input():
    service = SkillService()
    results = service.merge_job_skills([], [])
    assert results == []


def test_merge_job_skills_raw_strings_normalization():
    service = SkillService()
    required = ["python", "fastapi"]
    nice = ["docker"]

    results = service.merge_job_skills(required, nice)
    assert len(results) == 3
    names = {r.canonical_name for r in results}
    assert "Python" in names
    assert "FastAPI" in names
    assert "Docker" in names


# ==============================================================================
# FIXTURES FOR ASYNC DATABASE TESTS
# ==============================================================================

@pytest_asyncio.fixture
async def skill_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session, engine

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_job(skill_test_db):
    session, _ = skill_test_db
    raw_job = RawJob(
        source="test",
        source_url="http://test.com/job/1",
        content_hash="test_hash_1",
        fetch_status=RawJobStatusEnum.FETCHED.value,
    )
    session.add(raw_job)
    await session.flush()

    job = Job(
        raw_job_id=raw_job.id,
        title="Senior Python Engineer",
        normalized_title="Senior Python Engineer",
        company_name="Acme Corp",
        normalized_company="Acme Corp",
        description="We are looking for a Senior Python Engineer with FastAPI and Docker.",
        status=JobStatusEnum.ACTIVE,
    )
    session.add(job)
    await session.flush()
    return job


# ==============================================================================
# 2. INTEGRATION TESTS: Declarative Reconciliation (Idempotent Diffing)
# ==============================================================================

@pytest.mark.asyncio
async def test_sync_job_skills_declarative_reconciliation(skill_test_db, sample_job):
    """
    Kiểm tra chu trình đối soát khai báo (Declarative Reconciliation):
    Lần 1: [Python (req), Docker (nice), Java (nice)]
    Lần 2: [Python (req), Docker (req), Kubernetes (nice)]
    -> Python: giữ nguyên
    -> Docker: chuyển thành is_required=True
    -> Kubernetes: được insert mới
    -> Java: bị xóa sạch khỏi JobSkills
    Lần 3: Gọi lại lần 2 -> Đảm bảo tính Idempotency (không đổi, không duplicate).
    """
    session, _ = skill_test_db
    service = SkillService()
    job_id = sample_job.id

    # --- LẦN 1: Nạp ban đầu ---
    initial_req = [("Python", SkillCategoryEnum.LANGUAGE)]
    initial_nice = [("Docker", SkillCategoryEnum.TOOL), ("Java", SkillCategoryEnum.LANGUAGE)]
    await service.sync_job_skills(session, job_id, initial_req, initial_nice)
    await session.flush()

    # Xác minh DB lần 1
    stmt = select(JobSkill).where(JobSkill.job_id == job_id)
    res = await session.execute(stmt)
    job_skills_1 = res.scalars().all()
    assert len(job_skills_1) == 3

    # Load canonical names
    skill_ids = [js.skill_id for js in job_skills_1]
    res_skills = await session.execute(select(Skill).where(Skill.id.in_(skill_ids)))
    skill_map_1 = {s.id: s.canonical_name for s in res_skills.scalars().all()}

    js_map_1 = {skill_map_1[js.skill_id]: js for js in job_skills_1}
    assert js_map_1["Python"].is_required is True
    assert js_map_1["Docker"].is_required is False
    assert js_map_1["Java"].is_required is False

    # --- LẦN 2: Re-parse với JD mới ---
    updated_req = [("Python", SkillCategoryEnum.LANGUAGE), ("Docker", SkillCategoryEnum.TOOL)]
    updated_nice = [("Kubernetes", SkillCategoryEnum.TOOL)]
    await service.sync_job_skills(session, job_id, updated_req, updated_nice)
    await session.flush()

    # Xác minh DB lần 2
    res_2 = await session.execute(select(JobSkill).where(JobSkill.job_id == job_id))
    job_skills_2 = res_2.scalars().all()
    assert len(job_skills_2) == 3  # Python, Docker, Kubernetes (Java đã bị xóa)

    skill_ids_2 = [js.skill_id for js in job_skills_2]
    res_skills_2 = await session.execute(select(Skill).where(Skill.id.in_(skill_ids_2)))
    skill_map_2 = {s.id: s.canonical_name for s in res_skills_2.scalars().all()}
    js_map_2 = {skill_map_2[js.skill_id]: js for js in job_skills_2}

    # Python: giữ nguyên
    assert js_map_2["Python"].is_required is True
    # Docker: đã được update thành required=True!
    assert js_map_2["Docker"].is_required is True
    # Kubernetes: mới được insert!
    assert js_map_2["Kubernetes"].is_required is False
    # Java: đã biến mất hoàn toàn
    assert "Java" not in js_map_2

    # --- LẦN 3: Kiểm tra Idempotency (Gọi lại đúng payload lần 2) ---
    await service.sync_job_skills(session, job_id, updated_req, updated_nice)
    await session.flush()

    res_3 = await session.execute(select(JobSkill).where(JobSkill.job_id == job_id))
    job_skills_3 = res_3.scalars().all()
    assert len(job_skills_3) == 3

    skill_ids_3 = [js.skill_id for js in job_skills_3]
    res_skills_3 = await session.execute(select(Skill).where(Skill.id.in_(skill_ids_3)))
    skill_map_3 = {s.id: s.canonical_name for s in res_skills_3.scalars().all()}
    js_map_3 = {skill_map_3[js.skill_id]: js for js in job_skills_3}
    assert set(js_map_3.keys()) == {"Python", "Docker", "Kubernetes"}


# ==============================================================================
# 3. PERFORMANCE INVARIANT: Query Count Test (O(1) Queries, Zero N+1)
# ==============================================================================

@pytest.mark.asyncio
async def test_sync_job_skills_query_count_invariant(skill_test_db, sample_job):
    """
    Chứng minh bằng thực nghiệm: Với 20 skills (10 required, 10 nice-to-have),
    hệ thống CHỈ phát sinh tối đa <= 5 câu lệnh SQL qua mạng,
    thay vì 40-60 queries tuần tự như trong kiến trúc cũ!
    """
    session, engine = skill_test_db
    service = SkillService()
    job_id = sample_job.id

    req_10 = [(f"ReqSkill_{i}", SkillCategoryEnum.FRAMEWORK) for i in range(10)]
    nice_10 = [(f"NiceSkill_{i}", SkillCategoryEnum.TOOL) for i in range(10)]

    executed_statements = []

    def statement_listener(conn, cursor, statement, parameters, context, executemany):
        stmt_lower = statement.lower()
        if "skills" in stmt_lower or "job_skills" in stmt_lower:
            executed_statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", statement_listener)

    try:
        await service.sync_job_skills(session, job_id, req_10, nice_10)
        await session.flush()
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", statement_listener)

    # Nếu dính N+1, số lượng statements sẽ là:
    # 20 SELECT skills + 20 INSERT skills + 20 SELECT job_skills + 20 INSERT job_skills = 40-80 queries!
    # Với Bulk O(1), số lượng statements chỉ là:
    # 1. SELECT skills WHERE canonical_name IN (...)
    # 2. INSERT INTO skills ON CONFLICT DO NOTHING (bulk)
    # 3. SELECT skills WHERE canonical_name IN (...) (reload)
    # 4. SELECT job_skills WHERE job_id = ...
    # 5. INSERT INTO job_skills (add_all / bulk)
    # Tổng cộng <= 5 câu lệnh SQL!
    assert len(executed_statements) <= 5, (
        f"Phát hiện N+1 queries! Kỳ vọng <= 5 statements cho 20 skills, "
        f"nhưng thực tế đã bắn {len(executed_statements)} statements:\n"
        + "\n---\n".join(executed_statements)
    )

    # Xác minh tất cả 20 JobSkills đã được lưu thành công
    res = await session.execute(select(JobSkill).where(JobSkill.job_id == job_id))
    assert len(res.scalars().all()) == 20


# ==============================================================================
# 4. CONCURRENCY: Race Condition on Missing Skill Creation
# ==============================================================================

@pytest.mark.asyncio
async def test_concurrent_skill_creation_race_condition(skill_test_db):
    """
    Kiểm tra hai coroutines chạy song song cùng nạp một skill mới tinh chưa có trong DB.
    Đảm bảo dialect-aware upsert (ON CONFLICT DO NOTHING) nuốt sạch xung đột,
    0 IntegrityError thoát ra ngoài, và DB chỉ tồn tại duy nhất 1 bản ghi.
    """
    session, _ = skill_test_db
    repo = SkillRepository()

    concurrent_skill = DesiredJobSkill(
        canonical_name="BrandNewConcurrentLanguage",
        category=SkillCategoryEnum.LANGUAGE,
    )

    # Chạy 2 tác vụ cùng lúc
    task1 = repo.ensure_missing_skills(session, [concurrent_skill])
    task2 = repo.ensure_missing_skills(session, [concurrent_skill])

    res1, res2 = await asyncio.gather(task1, task2)

    assert "BrandNewConcurrentLanguage" in res1
    assert "BrandNewConcurrentLanguage" in res2
    assert res1["BrandNewConcurrentLanguage"].id == res2["BrandNewConcurrentLanguage"].id

    stmt = select(Skill).where(Skill.canonical_name == "BrandNewConcurrentLanguage")
    db_skills = (await session.execute(stmt)).scalars().all()
    assert len(db_skills) == 1
