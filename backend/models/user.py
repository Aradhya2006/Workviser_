from pydantic import BaseModel
from typing import Optional

# base model:
# Pydantic's base class
# Gives us automatic data validation
# If someone sends wrong data type = it auto rejects it

# UserCreate:
# Used when someone registers
# Defines exactly what fields are required
# role must be one of: manager, employee, expert
# domain is Optional — only experts need it
# Optional[str] = None means → not required, defaults to None

# UserResponse:
# Used when we send user data back to frontend
# Never includes password — security rule
# Has gamification fields: points, rating, sessions_completed



class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str                     
    domain: Optional[str] = None  

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    domain: Optional[str] = None
    points: int = 0
    rating: float = 0.0
    sessions_completed: int = 0
    is_available: bool = True