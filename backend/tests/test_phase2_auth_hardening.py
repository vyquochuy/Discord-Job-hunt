import pytest
import pytest_asyncio
import uuid
import jwt
from datetime import timedelta, datetime
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi import status

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.user import User

@pytest_asyncio.fixture
async def test_env():
    """Thiết lập môi trường in-memory SQLite biệt lập với client HTTP."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_expired_jwt_token(test_env):
    client, session_maker = test_env
    
    # Create a user
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="expired@example.com",
        hashed_password="hashed",
        full_name="Expired User"
    )
    async with session_maker() as session:
        session.add(user)
        await session.commit()

    # Create an expired token manually
    to_encode = {"sub": str(user_id), "type": "access"}
    expire = datetime.utcnow() - timedelta(minutes=1)
    iat = datetime.utcnow() - timedelta(minutes=2)
    to_encode.update({"exp": expire, "iat": iat, "jti": str(uuid.uuid4())})
    expired_token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_invalid_jwt_token(test_env):
    client, _ = test_env
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_internal_service_masquerade(test_env):
    client, session_maker = test_env
    
    # Setup multiple users
    user1 = User(id=uuid.uuid4(), email="admin1@example.com", hashed_password="pw", full_name="User 1")
    user2 = User(id=uuid.uuid4(), email="user2@example.com", hashed_password="pw", full_name="User 2")
    
    async with session_maker() as session:
        session.add_all([user1, user2])
        await session.commit()

    # Use internal secret to access an endpoint that uses get_authenticated_user_or_internal
    response = await client.get(
        "/api/v1/profile",
        headers={"X-Internal-Secret": settings.INTERNAL_API_SECRET}
    )
    
    if response.status_code == 200:
        data = response.json()
        # Should not masquerade as admin1@example.com (the first user created)
        assert data["email"] != "admin1@example.com", "Service masquerading as User 1 detected!"
        # Should return a dedicated system service principal
        # The exact response depends on how /profile handles the system user, 
        # but we just want to ensure it doesn't return the first user's profile.
        pass
    elif response.status_code in (401, 403, 404):
        # Also acceptable if internal secret is handled completely separately 
        # or if the profile for the system user doesn't exist (404).
        pass
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")
