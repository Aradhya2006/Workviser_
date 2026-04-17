from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from bson import ObjectId
from database import (
    ratings_collection,
    help_requests_collection,
    users_collection
)
from auth import get_current_user

router = APIRouter(prefix="/ratings", tags=["Ratings"])


# SUBMIT RATING (Employee)

@router.post("/submit")
async def submit_rating(
    req: dict,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Only employees can submit ratings"
        )

    help_request_id = req.get("help_request_id")
    stars = req.get("stars")
    comment = req.get("comment", "")

    # Validate inputs
    if not help_request_id:
        raise HTTPException(
            status_code=400,
            detail="help_request_id is required"
        )

    if not stars or float(stars) < 1 or float(stars) > 5:
        raise HTTPException(
            status_code=400,
            detail="Stars must be between 1 and 5"
        )

    # Get help request
    try:
        help_req = await help_requests_collection.find_one({
            "_id": ObjectId(help_request_id)
        })
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid help request ID"
        )

    if not help_req:
        raise HTTPException(
            status_code=404,
            detail="Help request not found"
        )

    # Must be resolved before rating
    if help_req["status"] != "resolved":
        raise HTTPException(
            status_code=400,
            detail="Can only rate resolved help sessions"
        )

    # Must be the employee who requested help
    if help_req["employee_id"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=403,
            detail="You can only rate your own help sessions"
        )

    # Check if already rated
    existing_rating = await ratings_collection.find_one({
        "help_request_id": help_request_id,
        "employee_id": str(current_user["_id"])
    })

    if existing_rating:
        raise HTTPException(
            status_code=400,
            detail="You have already rated this session"
        )

    # Save rating
    rating_doc = {
        "help_request_id": help_request_id,
        "employee_id": str(current_user["_id"]),
        "employee_name": current_user["name"],
        "expert_id": help_req["expert_id"],
        "stars": float(stars),
        "comment": comment,
        "created_at": datetime.utcnow()
    }

    await ratings_collection.insert_one(rating_doc)

    # Update expert points and rating
    await update_expert_stats(help_req["expert_id"], float(stars))

    return {
        "message": "Rating submitted successfully",
        "stars": float(stars),
        "comment": comment,
        "expert_id": help_req["expert_id"]
    }


async def update_expert_stats(expert_id: str, new_stars: float):
    """
    Updates expert points and average rating after a new rating.

    Points system:
        5 stars = 50 points
        4 stars = 40 points
        3 stars = 30 points
        2 stars = 20 points
        1 star  = 10 points
    """
    expert = await users_collection.find_one({
        "_id": ObjectId(expert_id)
    })

    if not expert:
        return

    # Calculate points earned
    points_earned = int(new_stars) * 10

    # Calculate new average rating
    total_ratings = expert.get("total_ratings", 0) + 1
    old_rating = expert.get("rating", 0.0)
    new_avg_rating = round(
        ((old_rating * (total_ratings - 1)) + new_stars) / total_ratings,
        2
    )

    # Update expert
    await users_collection.update_one(
        {"_id": ObjectId(expert_id)},
        {"$set": {
            "rating": new_avg_rating,
            "total_ratings": total_ratings
        },
        "$inc": {
            "points": points_earned,
            "sessions_completed": 1
        }}
    )


# GET LEADERBOARD

@router.get("/leaderboard")
async def get_leaderboard(
    current_user: dict = Depends(get_current_user)
):
    experts = []

    async for expert in users_collection.find({"role": "expert"}):
        experts.append({
            "id": str(expert["_id"]),
            "name": expert["name"],
            "domain": expert.get("domain", ""),
            "points": expert.get("points", 0),
            "rating": expert.get("rating", 0.0),
            "total_ratings": expert.get("total_ratings", 0),
            "sessions_completed": expert.get("sessions_completed", 0),
            "is_available": expert.get("is_available", True)
        })

    # Sort by points first, then by rating
    experts.sort(
        key=lambda x: (x["points"], x["rating"]),
        reverse=True
    )

    # Add rank number
    for i, expert in enumerate(experts):
        expert["rank"] = i + 1

    return {
        "total_experts": len(experts),
        "leaderboard": experts
    }


# GET MY RATINGS (Expert)

@router.get("/my-ratings")
async def get_my_ratings(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "expert":
        raise HTTPException(
            status_code=403,
            detail="Only experts can view their ratings"
        )

    ratings = []
    async for rating in ratings_collection.find({
        "expert_id": str(current_user["_id"])
    }):
        ratings.append({
            "id": str(rating["_id"]),
            "help_request_id": rating["help_request_id"],
            "employee_name": rating.get("employee_name", ""),
            "stars": rating["stars"],
            "comment": rating.get("comment", ""),
            "created_at": rating["created_at"].isoformat()
        })

    ratings.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "total": len(ratings),
        "ratings": ratings
    }