from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from bson import ObjectId
from database import users_collection
from models.user import UserCreate
from auth import (
    hash_password,
    verify_password,
    create_token,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Auth"])

# ─── Helper ───────────────────────────────────────────

def format_user(user: dict) -> dict:
    """Convert MongoDB document to clean response"""
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "domain": user.get("domain"),
        "points": user.get("points", 0),
        "rating": user.get("rating", 0.0),
        "sessions_completed": user.get("sessions_completed", 0),
        "is_available": user.get("is_available", True)
    }

# ─── Register ─────────────────────────────────────────

@router.post("/register")
async def register(req: UserCreate):

    # Check duplicate email
    existing = await users_collection.find_one({"email": req.email})
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered"
        )

    # Validate role
    if req.role not in ["manager", "employee", "expert"]:
        raise HTTPException(
            status_code=400, 
            detail="Role must be manager, employee or expert"
        )

    # Build document to save in MongoDB
    user_doc = {
        "name": req.name,
        "email": req.email,
        "password_hash": hash_password(req.password),
        "role": req.role,
        "domain": req.domain if req.role == "expert" else None,
        "is_available": True,
        "active_sessions": 0,
        "points": 0,
        "rating": 0.0,
        "total_ratings": 0,
        "sessions_completed": 0,
        "created_at": datetime.utcnow()
    }

    # Save to MongoDB
    result = await users_collection.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    # Create JWT token
    token = create_token({
        "user_id": str(result.inserted_id),
        "role": req.role
    })

    return {
        "message": "Account created successfully",
        "token": token,
        "user": format_user(user_doc)
    }

# ─── Login ────────────────────────────────────────────

@router.post("/login")
async def login(req: dict):
    email = req.get("email")
    password = req.get("password")

    # Find user by email
    user = await users_collection.find_one({"email": email})

    # Check password
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=401, 
            detail="Invalid email or password"
        )

    # Create token
    token = create_token({
        "user_id": str(user["_id"]),
        "role": user["role"]
    })

    return {
        "message": "Login successful",
        "token": token,
        "user": format_user(user)
    }

# ─── Get Current User ─────────────────────────────────

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return format_user(current_user)

# ─── Get All Employees (Manager only) ─────────────────

@router.get("/employees")
async def get_all_employees(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "manager":
        raise HTTPException(
            status_code=403, 
            detail="Only managers can view employees"
        )

    employees = []
    async for emp in users_collection.find({"role": "employee"}):
        employees.append(format_user(emp))

    return employees

# ─── Get All Experts (Manager only) ───────────────────

@router.get("/experts")
async def get_all_experts(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "manager":
        raise HTTPException(
            status_code=403, 
            detail="Only managers can view experts"
        )

    experts = []
    async for exp in users_collection.find({"role": "expert"}):
        experts.append(format_user(exp))

    return experts


### Explanation:

# router = APIRouter(prefix="/auth")
#  All routes here become /auth/something
#  /register → /auth/register
#  /login → /auth/login

# format_user()
#  MongoDB uses _id as ObjectId type — not a string
#  Frontend needs a clean string id
#  This converts it and removes sensitive fields like password_hash

# /register flow:
# 
# 1. Check email not already used
# 2. Validate role is one of 3 valid values
# 3. Hash password before saving
# 4. Save full document to MongoDB
# 5. Create JWT token
# 6. Return token + clean user object
# 

# /login flow:
# 
# 1. Find user by email
# 2. Verify password using bcrypt
# 3. Create new JWT token
# 4. Return token + user info