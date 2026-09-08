import os
import time
import logging
import traceback
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
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


# Observability: Lọc bớt access log định kỳ của /health khi trả về 200 OK để tránh làm tràn log trên Render Free
class HealthAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if " 200 " in msg or " 200" in msg:
            if '"GET /health ' in msg or '"HEAD /health ' in msg or " /health " in msg:
                return False
        return True


logging.getLogger("uvicorn.access").addFilter(HealthAccessFilter())


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
            # 1. Xóa hoàn toàn tài khoản mặc định admin@example.com nếu tồn tại trong Database
            if admin_email != "admin@example.com":
                from sqlalchemy import delete
                old_admin_res = await session.execute(select(User).where(User.email == "admin@example.com"))
                old_admin = old_admin_res.scalar_one_or_none()
                if old_admin:
                    await session.execute(delete(Candidate).where(Candidate.user_id == old_admin.id))
                    await session.execute(delete(User).where(User.id == old_admin.id))
                    logger.info("Purged deprecated default 'admin@example.com' account from database.")

            # 2. Khởi tạo hoặc cập nhật tài khoản Admin theo cấu hình
            stmt = select(User).where(User.email == admin_email)
            result = await session.execute(stmt)
            admin_user = result.scalar_one_or_none()

            admin_name = getattr(settings, "ADMIN_NAME", "Quoc Huy")
            if not admin_user:
                if settings.ADMIN_INITIAL_PASSWORD:
                    admin_user = User(
                        id=uuid.uuid4(),
                        email=admin_email,
                        hashed_password=get_password_hash(settings.ADMIN_INITIAL_PASSWORD),
                        full_name=admin_name,
                        is_active=True,
                        is_superuser=True,
                    )
                    session.add(admin_user)
                    await session.flush()
                    logger.info(f"Initialized Superuser account: {admin_email}")
                else:
                    logger.info(f"Superuser account '{admin_email}' not created yet. Provide ADMIN_INITIAL_PASSWORD env var or insert directly via SQL.")
                    return
            else:
                admin_user.is_superuser = True
                # NOTE: Không overwrite password mỗi lần restart!
                # Chỉ set password lần đầu tạo user. Sau đó password được quản lý qua API.
                # Nếu muốn reset password, dùng ADMIN_FORCE_RESET_PASSWORD=true env var.
                if settings.ADMIN_INITIAL_PASSWORD and os.getenv("ADMIN_FORCE_RESET_PASSWORD", "").lower() == "true":
                    admin_user.hashed_password = get_password_hash(settings.ADMIN_INITIAL_PASSWORD)
                    logger.info(f"Force-reset password for Superuser: {admin_email}")
                else:
                    logger.info(f"Updated Superuser status for: {admin_email} (password unchanged)")

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
    if origin.strip() and origin.strip() != "*"
]

# Whitelist các domain cục bộ và domain Vercel cụ thể
default_allowed = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
for origin in default_allowed:
    if origin not in cors_origins:
        cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Cho phép tất cả subdomain an toàn thuộc về vercel.app (production & preview deployments)
    allow_origin_regex=r"^https://[a-zA-Z0-9_-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Internal-Secret", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Disposition", "Content-Length"],
    max_age=86400,  # Cache kết quả Preflight OPTIONS 24 giờ để giảm request tải server
)


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if (
        path.startswith("/js/")
        or path.startswith("/css/")
        or path.startswith("/static/")
        or path.endswith(".js")
        or path.endswith(".html")
        or path == "/"
    ):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


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



@app.api_route("/", methods=["GET", "HEAD"], tags=["system"])
async def root(request: Request):
    """Serve Web Application chính hoặc JSON info nếu request header là application/json thuần túy."""
    if request.method == "HEAD":
        return Response(status_code=status.HTTP_200_OK)

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
            "ready": "/health/ready",
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
        "ready": "/health/ready",
        "web_app": None,
    }


@app.api_route("/health", methods=["GET", "HEAD"], tags=["system"])
async def liveness_health_check(request: Request):
    """
    Lightweight Liveness probe:
    - Trả về HTTP 200 khi tiến trình FastAPI backend đang hoạt động.
    - TUYỆT ĐỐI KHÔNG truy vấn PostgreSQL, Redis hoặc gọi external APIs.
    - Phục vụ Render liveness healthcheck và phát hiện cold-start từ frontend.
    """
    if request.method == "HEAD":
        return Response(status_code=status.HTTP_200_OK)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "service": "job-hunt-backend",
        }
    )


@app.api_route("/health/ready", methods=["GET", "HEAD"], tags=["system"])
async def readiness_health_check(request: Request):
    """
    Readiness probe:
    - Xác nhận core dependencies (PostgreSQL database) đã sẵn sàng phục vụ lưu lượng.
    - Thực thi truy vấn tối thiểu SELECT 1 thông qua connection pool async hiện có.
    - Trả về HTTP 200 khi sẵn sàng, HTTP 503 Service Unavailable khi mất kết nối DB.
    - An toàn bảo mật: Tuyệt đối KHÔNG rò rỉ chuỗi kết nối, credentials hay stack traces.
    """
    db_healthy = await check_db_health()

    if not db_healthy:
        if request.method == "HEAD":
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "unavailable",
            }
        )

    if request.method == "HEAD":
        return Response(status_code=status.HTTP_200_OK)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ready",
            "database": "ok",
        }
    )


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

