from fastapi import APIRouter
from app.api.v1.endpoints import profile, jobs

api_router = APIRouter()

# Phase 1: Candidate Profile Router
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])

# Các router con của các phase sau sẽ được include tiếp tục:
# api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
# api_router.include_router(applications.router, prefix="/applications", tags=["applications"])

# Phase 2: Job Collection Router
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])


@api_router.get("/info", tags=["system"])
async def get_system_info():
    """Thông tin cơ bản về API v1."""
    return {
        "status": "online",
        "version": "v1",
        "message": "AI Job Hunter API v1 is active and ready."
    }
