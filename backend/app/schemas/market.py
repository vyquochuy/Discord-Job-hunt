from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

MarketStatus = Literal["ok", "insufficient", "empty", "unavailable"]


class MarketAnalyticsResponse(BaseModel):
    """Legacy shape kept for backward compatibility with the old Market page."""

    total_active_jobs: int
    total_expired_jobs: int
    sources: List[dict]
    top_skills: List[dict]
    salary: dict


class MarketMeta(BaseModel):
    generated_at: str
    filters: Dict[str, Any]
    total_jobs: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    status: MarketStatus
    notes: List[str] = Field(default_factory=list)


class FilterOption(BaseModel):
    value: str
    label: str
    jobs: int


class MarketFilterCatalogResponse(BaseModel):
    date_range: Dict[str, Optional[str]]
    levels: List[FilterOption]
    categories: List[FilterOption]
    locations: List[FilterOption]
    regions: List[FilterOption]
    sources: List[FilterOption]
    work_modes: List[FilterOption]
    skills: List[FilterOption]
    total_jobs: int
    generated_at: str


class TrendPoint(BaseModel):
    bucket: str
    label: str
    jobs: int


class OverviewResponse(BaseModel):
    meta: MarketMeta
    totals: Dict[str, int]
    recent: Dict[str, Any]
    distributions: Dict[str, List[Dict[str, Any]]]
    data_quality: Dict[str, Any]
    sparkline: List[TrendPoint]


class HiringTrendsResponse(BaseModel):
    meta: MarketMeta
    series: List[TrendPoint]
    stacked: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    categories: List[Dict[str, Any]]
    levels: List[Dict[str, Any]]
    work_modes: List[Dict[str, Any]]
    summary: Dict[str, Any]
    caveats: List[str]


class SalaryResponse(BaseModel):
    meta: MarketMeta
    coverage: Dict[str, Any]
    native: List[Dict[str, Any]]
    normalized_vnd: Dict[str, Any]
    by_level: List[Dict[str, Any]]
    by_category: List[Dict[str, Any]]
    by_region: List[Dict[str, Any]]
    by_source: List[Dict[str, Any]]
    histogram: List[Dict[str, Any]]
    top_companies: List[Dict[str, Any]]
    notes: List[str]


class SkillsResponse(BaseModel):
    meta: MarketMeta
    jobs_with_skills: int
    unique_skills: int
    top_skills: List[Dict[str, Any]]
    by_category: List[Dict[str, Any]]
    cooccurrence: List[Dict[str, Any]]
    by_level: List[Dict[str, Any]]
    emerging: Dict[str, Any]


class RolesResponse(BaseModel):
    meta: MarketMeta
    top_titles: List[Dict[str, Any]]
    by_category: List[Dict[str, Any]]
    role_families: List[Dict[str, Any]]
    title_level_matrix: List[Dict[str, Any]]
    emerging: Dict[str, Any]


class GeographyResponse(BaseModel):
    meta: MarketMeta
    regions: List[Dict[str, Any]]
    cities: List[Dict[str, Any]]
    by_category: List[Dict[str, Any]]
    remote_share: Dict[str, Any]
    salary_by_region: List[Dict[str, Any]]


class EmployersResponse(BaseModel):
    meta: MarketMeta
    top_employers: List[Dict[str, Any]]
    concentration: Dict[str, Any]
    by_category: List[Dict[str, Any]]
    new_entrants: List[Dict[str, Any]]


class InsightsResponse(BaseModel):
    meta: MarketMeta
    disclaimer: str
    insights: List[Dict[str, Any]]
    methodology: List[str]
    data_quality: Dict[str, Any]
