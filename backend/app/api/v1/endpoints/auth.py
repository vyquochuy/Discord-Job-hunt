import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.candidate import Candidate
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Đăng ký tài khoản người dùng mới trên Web App.
    Tự động liên kết hoặc tạo hồ sơ Ứng viên 1–1 (CandidateProfile).
    """
    # 1. Kiểm tra email đã tồn tại chưa
    stmt = select(User).where(User.email == payload.email.lower().strip())
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được đăng ký trong hệ thống",
        )

    # 2. Tạo User
    user = User(
        id=uuid.uuid4(),
        email=payload.email.lower().strip(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # 3. Tạo hoặc gán Candidate Profile 1–1 (User 1-1 Candidate)
    cand_stmt = select(Candidate).where(Candidate.user_id.is_(None)).order_by(Candidate.created_at.asc()).limit(1)
    cand_res = await db.execute(cand_stmt)
    unassigned_cand = cand_res.scalar_one_or_none()

    if unassigned_cand:
        unassigned_cand.user_id = user.id
        candidate_id = unassigned_cand.id
    else:
        new_cand = Candidate(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
        )
        db.add(new_cand)
        await db.flush()
        candidate_id = new_cand.id

    await db.commit()
    await db.refresh(user)

    # 4. Phát hành Token
    token = create_access_token({"sub": str(user.id), "email": user.email})

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        candidate_id=candidate_id,
        created_at=user.created_at,
    )

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        user=user_resp,
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Đăng nhập tài khoản người dùng Web App.
    """
    stmt = (
        select(User)
        .options(selectinload(User.candidate))
        .where(User.email == payload.email.lower().strip())
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa",
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})
    candidate_id = user.candidate.id if user.candidate else None

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        candidate_id=candidate_id,
        created_at=user.created_at,
    )

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        user=user_resp,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Lấy thông tin người dùng đang đăng nhập hiện tại.
    """
    stmt = (
        select(User)
        .options(selectinload(User.candidate))
        .where(User.id == current_user.id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one()

    candidate_id = user.candidate.id if user.candidate else None

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        candidate_id=candidate_id,
        created_at=user.created_at,
    )
