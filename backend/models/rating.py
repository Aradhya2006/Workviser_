from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class RatingCreate(BaseModel):
    help_request_id: str
    stars: float
    comment: Optional[str] = None

    @validator("stars")
    def stars_must_be_valid(cls, v):
        if v < 1.0 or v > 5.0:
            raise ValueError("Stars must be between 1 and 5")
        return v

class RatingResponse(BaseModel):
    id: str
    help_request_id: str
    employee_id: str
    expert_id: str
    stars: float
    comment: Optional[str]
    created_at: datetime

# RatingCreate — employee submits after session ends

# help_request_id : which session they are rating
# stars : 1.0 to 5.0
# @validator("stars") : auto rejects anything outside 1-5
# comment : optional written feedback

# RatingResponse — full rating returned

# Includes both employee_id and expert_id
# Leaderboard uses expert_id to add points to correct expert