import uuid
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.candidate import Candidate
from app.repositories.candidate import CandidateRepository
from app.schemas.candidate import CandidateUpdate
from app.services.parser import CandidateProfileParser


# In-memory SQLite async engine fixture
@pytest_asyncio.fixture
async def async_session():
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
    """Kiểm tra parser đọc chính xác thư mục context/ thực tế của dự án."""
    context_dir = Path(__file__).resolve().parent.parent.parent / "context"
    assert context_dir.exists(), f"Context directory {context_dir} does not exist"

    merged = CandidateProfileParser.load_and_merge_context(context_dir)

    # 1. Kiểm tra thông tin cá nhân
    assert merged["candidate"]["name"] == "Vy Quoc Huy"
    assert "System Intern" in merged["candidate"].get("headline", "")
    assert merged["candidate"]["email"] == "vyquochuy305@gmail.com"
    assert "github.com/vyquochuy" in merged["candidate"]["github"]

    # 2. Kiểm tra học vấn
    assert len(merged["education"]) >= 1
    edu = merged["education"][0]
    assert "University of Science" in edu["institution"]
    assert edu["gpa"] == "3.15/4.0"

    # 3. Kiểm tra kỹ năng
    skills = merged["skills"]
    assert "Python" in skills.get("programming", [])
    assert "TypeScript" in skills.get("programming", [])
    assert "Cloudflare Workers" in skills.get("tools_databases", []) or "Cloudflare D1" in skills.get("tools_databases", [])

    # 4. Kiểm tra dự án & evidence
    projects = merged["projects"]
    assert len(projects) >= 2
    project_names = [p["name"] for p in projects]
    assert any("VYVYCHAT" in name for name in project_names)
    assert any("Account Manager" in name for name in project_names)

    # Kiểm tra evidence trong dự án VYVYCHAT
    vyvychat = next(p for p in projects if "VYVYCHAT" in p["name"])
    assert len(vyvychat.get("evidence", [])) >= 2


@pytest.mark.asyncio
async def test_repository_sync_and_get_profile(async_session: AsyncSession):
    """Kiểm tra CandidateRepository đồng bộ dữ liệu vào DB và truy vấn ra kèm eager loading."""
    context_dir = Path(__file__).resolve().parent.parent.parent / "context"
    merged = CandidateProfileParser.load_and_merge_context(context_dir)

    # 1. Đồng bộ dữ liệu
    candidate = await CandidateRepository.sync_from_parsed_context(
        async_session, merged
    )
    assert candidate.id is not None
    assert candidate.full_name == "Vy Quoc Huy"
    assert len(candidate.skills) > 0
    assert len(candidate.projects) >= 2

    # 2. Truy vấn lại qua get_profile
    retrieved = await CandidateRepository.get_profile(async_session)
    assert retrieved is not None
    assert retrieved.id == candidate.id
    assert retrieved.full_name == "Vy Quoc Huy"
    assert len(retrieved.skills) == len(candidate.skills)
    assert len(retrieved.projects) == len(candidate.projects)

    # 3. Cập nhật một số trường
    update_data = CandidateUpdate(headline="Lead SRE & DevOps Intern")
    updated = await CandidateRepository.update_profile_fields(
        async_session, candidate.id, update_data
    )
    assert updated is not None
    assert updated.headline == "Lead SRE & DevOps Intern"
