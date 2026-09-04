import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.limiter import limiter
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
@limiter.limit("3/minute")
async def register_user(
    request: Request,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Đăng ký tài khoản người dùng mới trên Web App.
    Tự động liên kết hoặc tạo hồ sơ Ứng viên 1–1 (CandidateProfile).
    """
    # 1. Kiểm tra email đã tồn tại chưa
    email_clean = payload.email.lower().strip()
    stmt = select(User).where(User.email == email_clean)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được đăng ký trong hệ thống",
        )

    # 2. Xác định quyền Superuser (tài khoản đầu tiên hoặc email quản trị cấu hình)
    from sqlalchemy import func
    from app.core.config import settings

    count_stmt = select(func.count(User.id))
    user_count = (await db.execute(count_stmt)).scalar() or 0
    is_admin = (email_clean == settings.ADMIN_EMAIL.lower().strip()) or (user_count == 0)

    # 3. Tạo User
    user = User(
        id=uuid.uuid4(),
        email=email_clean,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        is_active=True,
        is_superuser=is_admin,
    )
    db.add(user)
    await db.flush()

    # 4. Tạo hoặc gán Candidate Profile 1–1 (User 1-1 Candidate)
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
@limiter.limit("5/minute")
async def login_user(
    request: Request,
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Đăng nhập tài khoản người dùng Web App.
    """
    email_clean = payload.email.lower().strip()
    stmt = (
        select(User)
        .options(selectinload(User.candidate))
        .where(User.email == email_clean)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    from app.core.config import settings

    # Tự động bootstrap tài khoản Superuser nếu dùng thông tin quản trị cấu hình mà tài khoản chưa có trong DB
    if not user and email_clean == settings.ADMIN_EMAIL.lower().strip() and payload.password == settings.ADMIN_INITIAL_PASSWORD:
        user = User(
            id=uuid.uuid4(),
            email=email_clean,
            hashed_password=get_password_hash(payload.password),
            full_name="Vy Quoc Huy",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        await db.flush()

        cand_stmt = select(Candidate).where(Candidate.user_id.is_(None)).order_by(Candidate.created_at.asc()).limit(1)
        cand_res = await db.execute(cand_stmt)
        cand = cand_res.scalar_one_or_none()
        if cand:
            cand.user_id = user.id
        else:
            cand = Candidate(id=uuid.uuid4(), user_id=user.id, full_name=user.full_name, email=user.email)
            db.add(cand)
            await db.flush()
        await db.commit()
        # Nạp lại kèm candidate
        stmt_reload = select(User).options(selectinload(User.candidate)).where(User.id == user.id)
        user = (await db.execute(stmt_reload)).scalar_one()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Đảm bảo tài khoản admin cấu hình luôn duy trì quyền superuser
    if email_clean == settings.ADMIN_EMAIL.lower().strip() and not user.is_superuser:
        user.is_superuser = True
        await db.commit()

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
