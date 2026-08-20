import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời khởi động và tắt ứng dụng."""
    logger.info(f"Starting {settings.PROJECT_NAME} (v{settings.VERSION})...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API và AI Orchestrator cho hệ thống AI Job Hunter Agent.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
async def root():
    """Endpoint gốc chào mừng."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health"
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
