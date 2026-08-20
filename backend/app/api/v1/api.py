from fastapi import APIRouter

api_router = APIRouter()

# Các router con của Phase 1, Phase 2, Phase 3... sẽ được include vào đây:
# api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
# api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
# api_router.include_router(applications.router, prefix="/applications", tags=["applications"])


@api_router.get("/info", tags=["system"])
async def get_system_info():
    """Thông tin cơ bản về API v1."""
    return {
        "status": "online",
        "version": "v1",
        "message": "AI Job Hunter API v1 is active and ready."
    }
