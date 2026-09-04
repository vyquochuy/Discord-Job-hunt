import os
import time
import logging
import traceback
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.database import check_db_health
from app.api.v1.api import api_router

# Thiết lập logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend")


async def ensure_admin_superuser():
    """Tự động kiểm tra và khởi tạo tài khoản Superuser cấu hình khi khởi động ứng dụng."""
    try:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.core.security import get_password_hash
        from app.models.user import User
        from app.models.candidate import Candidate
        import uuid

        admin_email = settings.ADMIN_EMAIL.lower().strip()
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.email == admin_email)
            result = await session.execute(stmt)
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                admin_user = User(
                    id=uuid.uuid4(),
                    email=admin_email,
                    hashed_password=get_password_hash(settings.ADMIN_INITIAL_PASSWORD),
                    full_name="Vy Quoc Huy",
                    is_active=True,
                    is_superuser=True,
                )
                session.add(admin_user)
                await session.flush()
                logger.info(f"Initialized Superuser account: {admin_email}")
            else:
                if not admin_user.is_superuser:
                    admin_user.is_superuser = True
                    logger.info(f"Updated {admin_email} to Superuser status.")

            cand_stmt = select(Candidate).where((Candidate.user_id == admin_user.id) | (Candidate.user_id.is_(None))).order_by(Candidate.created_at.asc()).limit(1)
            cand_res = await session.execute(cand_stmt)
            candidate = cand_res.scalar_one_or_none()
            if candidate:
                if not candidate.user_id:
                    candidate.user_id = admin_user.id
            else:
                new_cand = Candidate(
                    id=uuid.uuid4(),
                    user_id=admin_user.id,
                    full_name=admin_user.full_name,
                    email=admin_user.email,
                )
                session.add(new_cand)

            await session.commit()
    except Exception as e:
        logger.warning(f"Note: ensure_admin_superuser skipped (Database may not be ready yet): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời khởi động và tắt ứng dụng."""
    logger.info(f"Starting {settings.PROJECT_NAME} (v{settings.VERSION})...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    await ensure_admin_superuser()
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API và AI Orchestrator cho hệ thống AI Job Hunter Agent.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Gắn limiter vào app state và đăng ký handler lỗi vượt hạn mức
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Cấu hình CORS Whitelisting an toàn
cors_origins = [
    origin.strip()
    for origin in settings.ALLOWED_CORS_ORIGINS.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tìm thư mục frontend (hỗ trợ cả môi trường Local lẫn Docker volume /frontend)
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if not frontend_dir.exists():
    frontend_dir = Path("/frontend")
if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
    if (frontend_dir / "css").exists():
        app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    if (frontend_dir / "js").exists():
        app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")


@app.get("/env.js", include_in_schema=False)
async def serve_env_js():
    """Phục vụ file cấu hình môi trường runtime frontend nếu tồn tại."""
    env_file = frontend_dir / "env.js"
    if env_file.exists():
        return FileResponse(str(env_file), media_type="application/javascript")
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "env.js not found"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Bắt và ghi log toàn bộ lỗi không mong muốn, trả về JSON an toàn thay vì phơi bày lỗi 500 ẩn."""
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}\n{error_trace}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error. Please contact system administrator."},
    )



@app.get("/", tags=["system"])
async def root(request: Request):
    """Serve Web Application chính hoặc JSON info nếu request header là application/json thuần túy."""
    index_file = frontend_dir / "index.html"
    accept_header = request.headers.get("accept", "")
    
    # Nếu request client chỉ định yêu cầu JSON (API client / curl)
    if "application/json" in accept_header and "text/html" not in accept_header:
        return {
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "health": "/health",
            "web_app": "/static/index.html" if index_file.exists() else None,
        }
    
    # Trình duyệt (Accept: text/html,...) hoặc truy cập mặc định -> Trả về Web App UI
    if index_file.exists():
        return FileResponse(str(index_file))
        
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "web_app": None,
    }


@app.get("/health", tags=["system"])
async def health_check():
    """
    Endpoint kiểm tra toàn diện sức khỏe hệ thống:
    - Trạng thái FastAPI Backend
    - Trạng thái kết nối PostgreSQL Database
    - Trạng thái kết nối Redis Queue/Cache
    """
    db_healthy = await check_db_health()

    redis_healthy = False
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        redis_healthy = await r.ping()
        await r.aclose()
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        redis_healthy = False

    is_overall_healthy = db_healthy and redis_healthy
    http_status = status.HTTP_200_OK if is_overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    response_data = {
        "status": "healthy" if is_overall_healthy else "degraded",
        "timestamp": time.time(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {
            "api": "healthy",
            "database": "connected" if db_healthy else "disconnected",
            "redis": "connected" if redis_healthy else "disconnected",
        }
    }

    return JSONResponse(status_code=http_status, content=response_data)


# Gắn router API v1
app.include_router(api_router, prefix="/api/v1")


FRONTEND_ROUTES = {
    "dashboard",
    "jobs",
    "recommendations",
    "resume",
    "applications",
    "profile",
    "system",
}


@app.get("/{view_name}", tags=["frontend"])
async def serve_spa_view(view_name: str, request: Request):
    """Phục vụ file index.html cho các route SPA frontend (dashboard, jobs, recommendations, resume, applications, profile, system)."""
    if view_name.lower() in FRONTEND_ROUTES:
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": f"Route '/{view_name}' not found."}
    )

