from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    domain: str
    priority: int = 3                # 1=Critical, 2=High, 3=Medium, 4=Low, 5=Very Low
    expected_time: int               # in minutes
    assigned_to: str

    @validator("priority")
    def priority_must_be_valid(cls, v):
        if v not in [1, 2, 3, 4, 5]:
            raise ValueError("Priority must be between 1 and 5")
        return v

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    domain: str
    priority: int                    # stored as number now
    priority_label: Optional[str]    # "Critical", "High" etc — for display
    expected_time: int
    assigned_to: str
    manager_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_stuck: bool = False
    created_at: datetime

# TaskCreate:
# Manager fills this when creating a task
# title : name of the task e.g. "Fix API bug"
# domain : "backend", "frontend", "devops"
# priority : defaults to "medium" if not given
# expected_time : in minutes e.g. 60
# assigned_to : the employee's MongoDB user ID