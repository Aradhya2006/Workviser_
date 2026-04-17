from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class HelpRequestCreate(BaseModel):
    task_id: str
    employee_text: Optional[str] = None

class HelpRequestResponse(BaseModel):
    id: str
    task_id: str
    employee_id: str
    expert_id: Optional[str] = None
    employee_text: Optional[str] = None
    detected_emotions: Optional[Dict[str, float]] = None
    claude_briefing: Optional[Dict] = None
    priority_score: float = 0.0
    time_spent: float = 0.0
    status: str
    created_at: datetime
    accepted_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None




# HelpRequestCreate — employee sends this when clicking "I need help"

# task_id : which task they are stuck on
# employee_text : what they typed, feeds into emotion model

# Example: "I cant figure out why this keeps returning 500"



# HelpRequestResponse — full object returned to frontend

# detected_emotions : your ML model output

# Dict[str, float] means : {"stressed": 0.91, "confused": 0.76}


# claude_briefing : Claude's smart summary for expert

# Dict means flexible JSON : has summary, causes, steps


# priority_score : calculated number, higher = more urgent
# time_spent : minutes employee was stuck
# status flow : "pending" -> "accepted" -> "resolved"
# accepted_at : when expert accepted
# resolved_at : when problem was solved