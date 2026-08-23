from fastapi import APIRouter
from app.api.v1.endpoints import auth, profile, jobs, matches, resumes, applications

api_router = APIRouter()

# Web Authentication Router
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Phase 1: Candidate Profile Router
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])

# Phase 2: Job Collection Router
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

# Phase 3: Job Intelligence & Matching Router
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])

# Phase 4: Resume Tailoring & Application Automation Router
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])


@api_router.get("/info", tags=["system"])
async def get_system_info():
    """Thông tin cơ bản về API v1."""
    return {
        "status": "online",
        "version": "v1",
        "message": "AI Job Hunter API v1 is active and ready."
    }

