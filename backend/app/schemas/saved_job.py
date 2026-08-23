import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.job import JobResponse


class SavedJobCreate(BaseModel):
    notes: Optional[str] = None


class SavedJobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    notes: Optional[str] = None
    created_at: datetime
    job: Optional[JobResponse] = None

    model_config = {"from_attributes": True}
