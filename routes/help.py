from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from bson import ObjectId
from database import (
    help_requests_collection,
    tasks_collection,
    users_collection
)
from auth import get_current_user
from logic.priority_engine import calculate_priority_score
from logic.expert_matcher import (
    find_best_expert,
    mark_expert_busy,
    mark_expert_free
)
from logic.stuck_detection import get_time_spent_minutes
from logic.emotion_detector import predict_emotions
from logic.claude_briefing import generate_expert_briefing

router = APIRouter(prefix="/help", tags=["Help"])


def format_help_request(req: dict) -> dict:
    return {
        "id": str(req["_id"]),
        "task_id": req["task_id"],
        "employee_id": req["employee_id"],
        "employee_name": req.get("employee_name", ""),
        "expert_id": req.get("expert_id"),
        "expert_name": req.get("expert_name"),
        "task_title": req.get("task_title", ""),
        "task_domain": req.get("task_domain", ""),
        "task_priority": req.get("task_priority", 3),
        "employee_text": req.get("employee_text"),
        "detected_emotions": req.get("detected_emotions", {}),
        "claude_briefing": req.get("claude_briefing"),
        "priority_score": req.get("priority_score", 0.0),
        "time_spent": req.get("time_spent", 0.0),
        "status": req["status"],
        "created_at": req["created_at"].isoformat(),
        "accepted_at": req["accepted_at"].isoformat() if req.get("accepted_at") else None,
        "resolved_at": req["resolved_at"].isoformat() if req.get("resolved_at") else None,
    }


# REQUEST HELP (Employee)

@router.post("/request")
async def request_help(
    req: dict,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Only employees can request help"
        )

    task_id = req.get("task_id")
    employee_text = req.get("employee_text", "")

    if not task_id:
        raise HTTPException(
            status_code=400,
            detail="task_id is required"
        )

    # Get the task
    try:
        task = await tasks_collection.find_one({
            "_id": ObjectId(task_id)
        })
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["assigned_to"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=403,
            detail="This task is not assigned to you"
        )

    # Calculate time spent
    time_spent = 0.0
    if task.get("started_at"):
        time_spent = get_time_spent_minutes(task["started_at"])

    # Run emotion detection on employee text
    detected_emotions = {}
    if employee_text:
        detected_emotions = predict_emotions(employee_text)

    # Calculate priority score
    priority_score = calculate_priority_score(
        task_priority=task.get("priority", 3),
        time_spent_minutes=time_spent,
        detected_emotions=detected_emotions
    )

    # Find best expert
    expert = await find_best_expert(task.get("domain", ""))
    expert_id = str(expert["_id"]) if expert else None
    expert_name = expert["name"] if expert else None

    # Generate Groq AI briefing for expert
    claude_briefing = None
    if expert:
        claude_briefing = generate_expert_briefing(
            task_title=task["title"],
            task_domain=task.get("domain", ""),
            task_priority=task.get("priority", 3),
            time_spent=time_spent,
            employee_text=employee_text,
            detected_emotions=detected_emotions
        )

    # Build help request document
    help_doc = {
        "task_id": task_id,
        "task_title": task["title"],
        "task_domain": task.get("domain", ""),
        "task_priority": task.get("priority", 3),
        "employee_id": str(current_user["_id"]),
        "employee_name": current_user["name"],
        "expert_id": expert_id,
        "expert_name": expert_name,
        "employee_text": employee_text,
        "detected_emotions": detected_emotions,
        "claude_briefing": claude_briefing,
        "priority_score": priority_score,
        "time_spent": time_spent,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "accepted_at": None,
        "resolved_at": None
    }

    result = await help_requests_collection.insert_one(help_doc)
    help_doc["_id"] = result.inserted_id

    # Mark task as stuck
    await tasks_collection.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"is_stuck": True}}
    )

    return {
        "message": "Help request created",
        "help_request": format_help_request(help_doc),
        "expert_assigned": expert_name if expert_name else "No expert available right now"
    }


# GET HELP QUEUE (Expert)

@router.get("/queue")
async def get_help_queue(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "expert":
        raise HTTPException(
            status_code=403,
            detail="Only experts can view the queue"
        )

    requests = []
    async for req in help_requests_collection.find({
        "status": "pending",
        "expert_id": str(current_user["_id"])
    }):
        requests.append(format_help_request(req))

    requests.sort(key=lambda x: x["priority_score"], reverse=True)

    return {
        "total": len(requests),
        "queue": requests
    }


# ACCEPT HELP (Expert)

@router.post("/{request_id}/accept")
async def accept_help(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "expert":
        raise HTTPException(
            status_code=403,
            detail="Only experts can accept help requests"
        )

    try:
        help_req = await help_requests_collection.find_one({
            "_id": ObjectId(request_id)
        })
    except:
        raise HTTPException(status_code=400, detail="Invalid request ID")

    if not help_req:
        raise HTTPException(status_code=404, detail="Help request not found")

    if help_req["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Request is already {help_req['status']}"
        )

    await help_requests_collection.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": "accepted",
            "expert_id": str(current_user["_id"]),
            "expert_name": current_user["name"],
            "accepted_at": datetime.utcnow()
        }}
    )

    await mark_expert_busy(str(current_user["_id"]))

    updated = await help_requests_collection.find_one({
        "_id": ObjectId(request_id)
    })

    return {
        "message": "Help request accepted",
        "help_request": format_help_request(updated)
    }


# RESOLVE HELP (Expert)

@router.post("/{request_id}/resolve")
async def resolve_help(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "expert":
        raise HTTPException(
            status_code=403,
            detail="Only experts can resolve help requests"
        )

    try:
        help_req = await help_requests_collection.find_one({
            "_id": ObjectId(request_id)
        })
    except:
        raise HTTPException(status_code=400, detail="Invalid request ID")

    if not help_req:
        raise HTTPException(status_code=404, detail="Help request not found")

    if help_req["status"] != "accepted":
        raise HTTPException(
            status_code=400,
            detail="Request must be accepted before resolving"
        )

    await help_requests_collection.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": "resolved",
            "resolved_at": datetime.utcnow()
        }}
    )

    await mark_expert_free(str(current_user["_id"]))

    await tasks_collection.update_one(
        {"_id": ObjectId(help_req["task_id"])},
        {"$set": {"is_stuck": False}}
    )

    updated = await help_requests_collection.find_one({
        "_id": ObjectId(request_id)
    })

    return {
        "message": "Help request resolved",
        "help_request": format_help_request(updated)
    }


# GET MY HELP REQUESTS (Employee)

@router.get("/my-requests")
async def get_my_requests(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Only employees can view their requests"
        )

    requests = []
    async for req in help_requests_collection.find({
        "employee_id": str(current_user["_id"])
    }):
        requests.append(format_help_request(req))

    requests.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "total": len(requests),
        "requests": requests
    }


# GET SINGLE HELP REQUEST

@router.get("/{request_id}")
async def get_help_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        help_req = await help_requests_collection.find_one({
            "_id": ObjectId(request_id)
        })
    except:
        raise HTTPException(status_code=400, detail="Invalid request ID")

    if not help_req:
        raise HTTPException(status_code=404, detail="Help request not found")

    return format_help_request(help_req)