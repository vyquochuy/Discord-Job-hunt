import logging
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, WorkModeEnum
from app.services.deduplication.dedup_service import dedup_service
from app.services.normalization.job_normalizer import job_normalizer

logger = logging.getLogger("test.dedup")


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_exact_dedup_match(db_session: AsyncSession):
    """Kiểm tra Dedup Tầng 1: Exact Hash Signature."""
    logger.info("=== [TEST] Deduplication Tier 1 - EXACT HASH SIGNATURE ===")
    
    # 1. Tạo 1 job ban đầu trong DB
    raw = RawJob(
        id=uuid.uuid4(),
        source="itviec",
        source_url="https://itviec.com/job-1",
        content_hash="hash-1",
    )
    db_session.add(raw)
    await db_session.flush()

    sig = job_normalizer.compute_dedup_signature("FPT Software", "Senior Python Developer", "Ho Chi Minh City")
    logger.info(f"  Generated Dedup Signature: {sig}")
    
    job = Job(
        id=uuid.uuid4(),
        raw_job_id=raw.id,
        title="Senior Python Developer",
        normalized_title="Senior Python Developer",
        company_name="FPT Software",
        normalized_company="FPT Software",
        location="Ho Chi Minh City",
        normalized_location="Ho Chi Minh City",
        work_mode=WorkModeEnum.ONSITE,
        level=JobLevelEnum.SENIOR,
        description="Test description",
        dedup_signature=sig,
        status=JobStatusEnum.ACTIVE,
    )
    db_session.add(job)
    await db_session.commit()
    logger.info(f"  Inserted existing Job ID: {job.id} into database")

    # 2. Kiểm tra job mới với cùng signature
    res = await dedup_service.check_duplicate(
        db=db_session,
        dedup_signature=sig,
        normalized_company="FPT Software",
        normalized_title="Senior Python Developer",
        normalized_location="Ho Chi Minh City",
        job_level="SENIOR",
    )
    logger.info(f"  Dedup Check Result: is_duplicate={res.is_duplicate}, strategy={res.strategy}, confidence={res.confidence_score}, reason='{res.reason}'")
    assert res.is_duplicate is True
    assert res.strategy == "EXACT"
    assert res.duplicate_job_id == str(job.id)


@pytest.mark.asyncio
async def test_fuzzy_dedup_match(db_session: AsyncSession):
    """Kiểm tra Dedup Tầng 2: RapidFuzz khi title hoặc company hơi khác biệt nhỏ."""
    logger.info("=== [TEST] Deduplication Tier 2 - FUZZY STRING MATCHING ===")
    
    raw = RawJob(
        id=uuid.uuid4(),
        source="remotive",
        source_url="https://remotive.com/job-2",
        content_hash="hash-2",
    )
    db_session.add(raw)
    await db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        raw_job_id=raw.id,
        title="Senior Backend Developer (Python)",
        normalized_title="Senior Backend Developer (Python)",
        company_name="VNG Corporation",
        normalized_company="VNG Corporation",
        location="Ho Chi Minh City",
        normalized_location="Ho Chi Minh City",
        work_mode=WorkModeEnum.HYBRID,
        level=JobLevelEnum.SENIOR,
        description="Test",
        dedup_signature="different_sig",
        status=JobStatusEnum.ACTIVE,
    )
    db_session.add(job)
    await db_session.commit()
    logger.info(f"  Inserted Job: '{job.title}' at '{job.company_name}'")

    # Job mới: "Senior Backend Engineer (Python)" tại "VNG Corp"
    candidate_title = "Senior Backend Engineer (Python)"
    candidate_company = "VNG Corp"
    logger.info(f"  Checking incoming Job: '{candidate_title}' at '{candidate_company}'...")

    res = await dedup_service.check_duplicate(
        db=db_session,
        dedup_signature="new_sig",
        normalized_company=candidate_company,
        normalized_title=candidate_title,
        normalized_location="Ho Chi Minh City",
        job_level="SENIOR",
    )
    logger.info(f"  Dedup Check Result: is_duplicate={res.is_duplicate}, strategy={res.strategy}, confidence={res.confidence_score:.2f}, reason='{res.reason}'")
    assert res.is_duplicate is True
    assert res.strategy == "FUZZY"
    assert res.confidence_score >= 0.85


@pytest.mark.asyncio
async def test_dedup_differentiates_levels(db_session: AsyncSession):
    """Kiểm tra Dedup không gộp các job khác cấp bậc (Junior vs Senior)."""
    logger.info("=== [TEST] Deduplication Level Distinction (Junior vs Senior) ===")
    
    raw = RawJob(
        id=uuid.uuid4(),
        source="itviec",
        source_url="https://itviec.com/job-3",
        content_hash="hash-3",
    )
    db_session.add(raw)
    await db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        raw_job_id=raw.id,
        title="Junior Backend Developer",
        normalized_title="Junior Backend Developer",
        company_name="Tiki",
        normalized_company="Tiki",
        location="Ho Chi Minh City",
        normalized_location="Ho Chi Minh City",
        work_mode=WorkModeEnum.ONSITE,
        level=JobLevelEnum.JUNIOR,
        description="Junior",
        dedup_signature="sig_junior",
        status=JobStatusEnum.ACTIVE,
    )
    db_session.add(job)
    await db_session.commit()
    logger.info(f"  Existing Job in DB: Level={job.level.value}, Title='{job.title}'")

    # Job mới là Senior tại cùng công ty
    candidate_title = "Senior Backend Developer"
    candidate_level = "SENIOR"
    logger.info(f"  Testing incoming Job with different level: Level={candidate_level}, Title='{candidate_title}'")

    res = await dedup_service.check_duplicate(
        db=db_session,
        dedup_signature="sig_senior",
        normalized_company="Tiki",
        normalized_title=candidate_title,
        normalized_location="Ho Chi Minh City",
        job_level=candidate_level,
    )
    logger.info(f"  Dedup Check Result: is_duplicate={res.is_duplicate} (Correctly rejected duplicate due to level difference)")
    assert res.is_duplicate is False
