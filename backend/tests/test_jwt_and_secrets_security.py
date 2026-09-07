import uuid
import time
import os
import pytest
import jwt
from datetime import datetime, timedelta, timezone

from app.core.config import Settings, settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_access_token,
    decode_refresh_token,
    hash_token,
)


def test_create_and_decode_access_token_valid():
    """Kiểm tra tạo và giải mã access token chuẩn RFC 7519."""
    user_id = uuid.uuid4()
    token = create_access_token({"sub": str(user_id), "email": "test@example.com"})
    
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload
    # Token lifespan must be approximately 30 minutes
    assert payload["exp"] - payload["iat"] == 30 * 60


def test_create_and_decode_refresh_token_valid():
    """Kiểm tra tạo và giải mã refresh token chuẩn RFC 7519."""
    user_id = uuid.uuid4()
    family_id = uuid.uuid4()
    token = create_refresh_token(
        {"sub": str(user_id), "email": "test@example.com"},
        family_id=str(family_id),
    )
    
    payload = decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert payload["family_id"] == str(family_id)
    assert "jti" in payload
    # Token lifespan must be approximately 30 days
    assert payload["exp"] - payload["iat"] == 30 * 24 * 3600


def test_token_type_separation():
    """Access token không thể giải mã như refresh token và ngược lại."""
    user_id = uuid.uuid4()
    access_tok = create_access_token({"sub": str(user_id)})
    refresh_tok = create_refresh_token({"sub": str(user_id)})

    # Access token used as refresh -> None
    assert decode_refresh_token(access_tok) is None
    with pytest.raises(jwt.InvalidTokenError, match="Invalid token type"):
        decode_token(access_tok, expected_type="refresh")

    # Refresh token used as access -> None
    assert decode_access_token(refresh_tok) is None
    with pytest.raises(jwt.InvalidTokenError, match="Invalid token type"):
        decode_token(refresh_tok, expected_type="access")


def test_expired_token_rejected():
    """Token hết hạn phải bị từ chối bằng ExpiredSignatureError."""
    user_id = uuid.uuid4()
    token = create_access_token(
        {"sub": str(user_id)},
        expires_delta=timedelta(seconds=-10),  # In the past
    )
    assert decode_access_token(token) is None
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, expected_type="access")


def test_tampered_payload_rejected():
    """Token bị chỉnh sửa nội dung payload phải bị từ chối."""
    user_id = uuid.uuid4()
    token = create_access_token({"sub": str(user_id)})
    parts = token.split(".")
    
    # Tamper with the payload part
    tampered_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"
    assert decode_access_token(tampered_token) is None
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tampered_token)


def test_tampered_signature_rejected():
    """Token bị sửa đổi chữ ký phải bị từ chối."""
    user_id = uuid.uuid4()
    token = create_access_token({"sub": str(user_id)})
    parts = token.split(".")
    
    # Làm sai lệch ký tự đầu của signature
    first_char = "B" if parts[2][0] != "B" else "C"
    tampered_token = f"{parts[0]}.{parts[1]}.{first_char}{parts[2][1:]}"
    assert decode_access_token(tampered_token) is None
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tampered_token)



def test_wrong_secret_key_rejected():
    """Token ký bằng secret key khác phải bị từ chối."""
    user_id = uuid.uuid4()
    attacker_secret = "attacker_secret_key_that_is_32_characters_long_123"
    fake_token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": int(time.time()),
            "exp": int(time.time() + 1800),
        },
        attacker_secret,
        algorithm="HS256",
    )
    assert decode_access_token(fake_token) is None
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(fake_token)


def test_algorithm_confusion_attack_none_rejected():
    """Tấn công giả mạo header alg: none phải bị từ chối triệt để."""
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time() + 1800),
    }
    # Forge token with alg=none
    forged_token = jwt.encode(payload, key="", algorithm="none")
    assert decode_access_token(forged_token) is None
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(forged_token)


def test_wrong_algorithm_rejected():
    """Ký bằng thuật toán ngoài whitelist (ví dụ HS512) phải bị từ chối."""
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time() + 1800),
    }
    # Sign with HS512 instead of HS256
    token_hs512 = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS512")
    assert decode_access_token(token_hs512) is None
    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_token(token_hs512)


def test_missing_required_claims_rejected():
    """Token thiếu bất kỳ claim bắt buộc nào (jti, type, iat, exp, sub) đều bị từ chối."""
    user_id = uuid.uuid4()
    # Missing jti
    payload_no_jti = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(time.time()),
        "exp": int(time.time() + 1800),
    }
    token = jwt.encode(payload_no_jti, settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_token(token)


def test_invalid_sub_uuid_rejected():
    """Claim sub không phải UUID hợp lệ phải bị từ chối."""
    with pytest.raises(ValueError, match="Invalid UUID for 'sub' claim"):
        create_access_token({"sub": "not-a-valid-uuid"})

    # If forged directly:
    payload = {
        "sub": "not-a-valid-uuid",
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time() + 1800),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError, match="Token subject .* is not a valid UUID"):
        decode_token(token)


def test_hash_token():
    """Kiểm tra hash SHA-256 của token là 64 ký tự hex và tất định."""
    raw_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.abc"
    h1 = hash_token(raw_token)
    h2 = hash_token(raw_token)
    assert len(h1) == 64
    assert h1 == h2
    assert h1 != hash_token(raw_token + "x")


def test_production_secret_fail_fast():
    """Trong môi trường production, default hoặc secret ngắn phải ném ValueError."""
    os.environ["ENVIRONMENT"] = "production"
    try:
        # Default secret must fail
        with pytest.raises(ValueError, match="Production security violation"):
            Settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="job_hunter_platform_secret_key_web_2026_flexible_auth",
            )

        # Short secret (< 32 chars) must fail
        with pytest.raises(ValueError, match="Production security violation"):
            Settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="too_short_secret",
            )

        # Insecure internal secret must fail
        with pytest.raises(ValueError, match="Production security violation"):
            Settings(
                ENVIRONMENT="production",
                INTERNAL_API_SECRET="change_me_to_a_secure_random_string_32_chars",
            )

        # Valid strong secrets must succeed
        valid_settings = Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a" * 32,
            INTERNAL_API_SECRET="b" * 32,
        )
        assert valid_settings.JWT_SECRET_KEY == "a" * 32
    finally:
        os.environ["ENVIRONMENT"] = "development"


# ==============================================================================
# Integration Tests: Refresh Token Rotation, Grace Period, Reuse Attack & Isolation
# ==============================================================================

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, update
from app.core.database import Base, get_db
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth_service import AuthService


@pytest_asyncio.fixture
async def sec_test_client():
    """Tạo TestClient với database SQLite in-memory cho test bảo mật."""
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
async def test_refresh_token_rotation_and_grace_period_flow(sec_test_client):
    """
    Kiểm tra toàn bộ chu trình Rotation:
    1. Đăng ký -> nhận access_token (30m) & refresh_token (30d)
    2. Refresh lần 1 -> nhận cặp token mới RT2
    3. Gửi lại RT1 trong Grace Period (<= 15s) -> trả lại đúng RT2, không tạo nhánh mới
    4. Xác minh hash lưu trong DB, không lưu plaintext
    """
    client, session_factory = sec_test_client

    # 1. Đăng ký
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice_rtr@example.com",
            "password": "Password123!",
            "full_name": "Alice RTR",
        },
    )
    assert reg_resp.status_code == 201
    data1 = reg_resp.json()
    rt1 = data1["refresh_token"]
    at1 = data1["access_token"]
    assert rt1 is not None
    assert at1 is not None

    # Xác minh DB lưu token hash, không lưu plaintext
    async with session_factory() as session:
        tokens_in_db = (await session.execute(select(RefreshToken))).scalars().all()
        assert len(tokens_in_db) == 1
        assert tokens_in_db[0].token_hash == hash_token(rt1)
        assert tokens_in_db[0].token_hash != rt1  # Không plaintext!
        family_id = tokens_in_db[0].family_id

    # 2. Refresh lần 1 (Rotate RT1 -> RT2)
    ref_resp1 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rt1},
    )
    assert ref_resp1.status_code == 200
    data2 = ref_resp1.json()
    rt2 = data2["refresh_token"]
    at2 = data2["access_token"]
    assert rt2 != rt1
    assert at2 != at1

    # Kiểm tra DB sau rotate
    async with session_factory() as session:
        tokens_in_db = (await session.execute(select(RefreshToken).order_by(RefreshToken.created_at.asc()))).scalars().all()
        assert len(tokens_in_db) == 2
        # RT1 đã bị revoked và có replaced_by_jti trỏ tới RT2
        assert tokens_in_db[0].revoked_at is not None
        assert tokens_in_db[0].replaced_by_jti == tokens_in_db[1].jti
        # RT2 thuộc cùng family_id
        assert tokens_in_db[1].family_id == family_id
        assert tokens_in_db[1].revoked_at is None

    # 3. Invariant 3: Gửi lại RT1 trong vòng 15 giây (Grace Period)
    grace_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rt1},
    )
    assert grace_resp.status_code == 200
    grace_data = grace_resp.json()
    # Phải trả lại cùng RT2 jti (không tạo token nhánh mới RT3)
    p_grace = decode_refresh_token(grace_data["refresh_token"])
    p_rt2 = decode_refresh_token(rt2)
    assert p_grace["jti"] == p_rt2["jti"]
    assert p_grace["family_id"] == p_rt2["family_id"]

    # Kiểm tra số lượng token trong DB vẫn là 2 (không bị rẽ nhánh)
    async with session_factory() as session:
        tokens_count = len((await session.execute(select(RefreshToken))).scalars().all())
        assert tokens_count == 2


@pytest.mark.asyncio
async def test_refresh_token_reuse_attack_revokes_entire_family(sec_test_client):
    """
    Kiểm tra cơ chế phát hiện tấn công tái sử dụng (Reuse Attack):
    Khi RT1 bị dùng lại sau khi Grace Period đã hết (hoặc giả lập > 15s)
    -> Hệ thống thu hồi toàn bộ token trong Token Family, ép user logout.
    """
    client, session_factory = sec_test_client

    # 1. Đăng ký
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob_victim@example.com",
            "password": "Password123!",
            "full_name": "Bob Victim",
        },
    )
    rt1 = reg_resp.json()["refresh_token"]

    # 2. Xoay vòng RT1 -> RT2
    ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rt1},
    )
    rt2 = ref_resp.json()["refresh_token"]

    # 3. Giả lập thời gian trôi qua 30 giây (vượt quá Grace Period 15s) trên RT1
    async with session_factory() as session:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(rt1))
            .values(revoked_at=datetime.now(timezone.utc) - timedelta(seconds=30))
        )
        await session.execute(stmt)
        await session.commit()

    # 4. Attacker cố tình dùng lại RT1 -> Kích hoạt Reuse Detection
    attack_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rt1},
    )
    assert attack_resp.status_code == 401
    assert "Security violation" in attack_resp.json()["detail"]

    # 5. Xác minh toàn bộ token trong family bị thu hồi, kể cả RT2 hợp lệ của nạn nhân
    async with session_factory() as session:
        tokens = (await session.execute(select(RefreshToken))).scalars().all()
        for t in tokens:
            assert t.revoked_at is not None  # Toàn bộ đã bị revoke!

    # 6. Bob thử dùng RT2 -> Bị từ chối luôn (buộc phải đăng nhập lại)
    bob_retry = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rt2},
    )
    assert bob_retry.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_token(sec_test_client):
    """Kiểm tra logout thu hồi refresh token."""
    client, session_factory = sec_test_client

    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "carol_logout@example.com",
            "password": "Password123!",
            "full_name": "Carol Logout",
        },
    )
    rt = reg_resp.json()["refresh_token"]
    at = reg_resp.json()["access_token"]

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {at}"},
        json={"refresh_token": rt},
    )
    assert logout_resp.status_code == 200

    # Sau logout, cố tình refresh bằng RT -> bị từ chối
    # Chỉnh revoked_at về trước 20s để tránh grace-period
    async with session_factory() as session:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(rt))
            .values(revoked_at=datetime.now(timezone.utc) - timedelta(seconds=20), replaced_by_jti=None)
        )
        await session.commit()

    ref_fail = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rt},
    )
    assert ref_fail.status_code == 401

