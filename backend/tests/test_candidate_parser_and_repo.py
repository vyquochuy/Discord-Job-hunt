import logging
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.services.parser import CandidateProfileParser

logger = logging.getLogger("test.candidate_repo")


@pytest_asyncio.fixture
async def async_session():
    """Tạo AsyncSession sử dụng in-memory SQLite để cô lập dữ liệu kiểm thử."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_parser_load_and_merge_actual_context():
    """Kiểm tra parser đọc chính xác các file context thật trong workspace."""
    logger.info("=== [TEST] Candidate Context Parser (YAML + Markdown + TeX) ===")
    context_dir = CandidateService.get_default_context_dir()

    if not context_dir.exists():
        pytest.skip(f"Context directory {context_dir} not found")

    merged = CandidateProfileParser.load_and_merge_context(context_dir)
    logger.info(f"  Merged Candidate Profile: Name='{merged['candidate'].get('name')}', Email='{merged['candidate'].get('email')}'")
    logger.info(f"  Target Roles: {merged.get('target_roles')}")
    logger.info(f"  Projects Parsed: {len(merged.get('projects', []))}")
    logger.info(f"  Skills Groups: {list(merged.get('skills', {}).keys())}")

    assert merged["candidate"]["name"] == "Vy Quoc Huy"
    assert merged["candidate"]["email"] == "vyquochuy305@gmail.com"
    assert len(merged["projects"]) >= 2
    assert len(merged["skills"]) > 0


@pytest.mark.asyncio
async def test_repository_sync_and_get_profile(async_session: AsyncSession):
    """Kiểm tra quá trình đồng bộ (Sync) và truy vấn hồ sơ ứng viên qua Service & Repository."""
    logger.info("=== [TEST] Candidate Service Sync & Get Profile Lifecycle ===")
    context_dir = CandidateService.get_default_context_dir()

    if not context_dir.exists():
        pytest.skip(f"Context directory {context_dir} not found")

    # 1. Đồng bộ lần đầu qua CandidateService
    logger.info("  1. Executing Sync from context directory...")
    sync_resp = await CandidateService.sync_profile_from_context(async_session, context_dir)
    assert sync_resp.success is True
    assert sync_resp.full_name == "Vy Quoc Huy"
    logger.info(f"  Sync Response: Success={sync_resp.success}, Candidate='{sync_resp.full_name}', SkillsCount={sync_resp.skills_count}")

    # 2. Truy vấn lại qua CandidateRepository
    fetched = await CandidateRepository.get_profile(async_session)
    assert fetched is not None
    assert fetched.full_name == "Vy Quoc Huy"
    logger.info(f"  2. Fetched Profile from DB: Full Name='{fetched.full_name}', Skills={len(fetched.skills)}, Projects={len(fetched.projects)}")

    # 3. Đồng bộ lại (Idempotency) -> không tạo duplicate candidate
    logger.info("  3. Executing Idempotent Re-Sync...")
    sync_resp_2 = await CandidateService.sync_profile_from_context(async_session, context_dir)
    assert sync_resp_2.success is True
    assert sync_resp_2.candidate_id == sync_resp.candidate_id
    logger.info(f"  Idempotency Verified: Candidate ID {sync_resp_2.candidate_id} matched previous ID.")
