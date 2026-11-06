from typing import List
from pydantic import BaseModel


class MarketAnalyticsResponse(BaseModel):
    total_active_jobs: int
    total_expired_jobs: int
    sources: List[dict]
    top_skills: List[dict]
    salary: dict
