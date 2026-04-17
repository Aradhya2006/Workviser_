from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from bson import ObjectId
from database import tasks_collection, users_collection
from models.task import TaskCreate
from auth import get_current_user
from logic.stuck_detection import get_stuck_info

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# ─── Priority label helper ─────────────────────────────

def get_priority_label(priority: int) -> str:
    labels = {
        1: "Critical",
        2: "High",
        3: "Medium",
        4: "Low",
        5: "Very Low"
    }
    return labels.get(priority, "Medium")

def get_priority_color(priority: int) -> str:
    colors = {
        1: "#FF4444",
        2: "#FF8C00",
        3: "#FFD700",
        4: "#32CD32",
        5: "#A9A9A9"
    }
    return colors.get(priority, "#FFD700")

# ─── Format task helper ────────────────────────────────

def format_task(task: dict) -> dict:
    """Convert MongoDB task document to clean response"""
    task_id = str(task["_id"])
    priority = task.get("priority", 3)

    formatted = {
        "id": task_id,
        "title": task["title"],
        "description": task.get("description"),
        "domain": task["domain"],
        "priority": priority,
        "priority_label": get_priority_label(priority),
        "priority_color": get_priority_color(priority),
        "expected_time": task["expected_time"],
        "assigned_to": task["assigned_to"],
        "assigned_to_name": task.get("assigned_to_name", ""),
        "manager_id": task["manager_id"],
        "status": task["status"],
        "is_stuck": task.get("is_stuck", False),
        "stuck_triggered": task.get("stuck_triggered", False),
        "created_at": task["created_at"].isoformat(),
        "started_at": task["started_at"].isoformat() if task.get("started_at") else None,
        "completed_at": task["completed_at"].isoformat() if task.get("completed_at") else None,
    }

    # Add live timer info if task is in progress
    if task.get("started_at") and task["status"] == "in_progress":
        stuck_info = get_stuck_info(task["started_at"], task["expected_time"])
        formatted["timer"] = stuck_info

    return formatted

# ─── CREATE TASK (Manager only) ───────────────────────

@router.post("/create")
async def create_task(
    req: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    # Only managers can create tasks
    if current_user["role"] != "manager":
        raise HTTPException(
            status_code=403,
            detail="Only managers can create tasks"
        )

    # Check employee exists
    try:
        employee = await users_collection.find_one({
            "_id": ObjectId(req.assigned_to),
            "role": "employee"
        })
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid employee ID"
        )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    # Build task document
    task_doc = {
        "title": req.title,
        "description": req.description,
        "domain": req.domain,
        "priority": req.priority,
        "expected_time": req.expected_time,
        "assigned_to": req.assigned_to,
        "assigned_to_name": employee["name"],
        "manager_id": str(current_user["_id"]),
        "manager_name": current_user["name"],
        "status": "pending",
        "is_stuck": False,
        "stuck_triggered": False,
        "started_at": None,
        "completed_at": None,
        "created_at": datetime.utcnow()
    }

    result = await tasks_collection.insert_one(task_doc)
    task_doc["_id"] = result.inserted_id

    return {
        "message": "Task created successfully",
        "task": format_task(task_doc)
    }

# ─── GET MY TASKS (Employee) ──────────────────────────

@router.get("/my-tasks")
async def get_my_tasks(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Only employees can view their tasks"
        )

    tasks = []
    async for task in tasks_collection.find({
        "assigned_to": str(current_user["_id"])
    }):
        tasks.append(format_task(task))

    return {
        "total": len(tasks),
        "tasks": tasks
    }

# ─── START TASK (Employee) ────────────────────────────

@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Only employees can start tasks"
        )

    # Find the task
    try:
        task = await tasks_collection.find_one({
            "_id": ObjectId(task_id)
        })
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check task belongs to this employee
    if task["assigned_to"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=403,
            detail="This task is not assigned to you"
        )

    # Check task is not already started
    if task["status"] == "in_progress":
        raise HTTPException(
            status_code=400,
            detail="Task already in progress"
        )

    if task["status"] == "completed":
        raise HTTPException(
            status_code=400,
            detail="Task already completed"
        )

    # Start the task
    await tasks_collection.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {
            "status": "in_progress",
            "started_at": datetime.utcnow()
        }}
    )

    # Fetch updated task
    updated_task = await tasks_collection.find_one({
        "_id": ObjectId(task_id)
    })

    return {
        "message": "Task started successfully",
        "task": format_task(updated_task)
    }

# ─── CHECK STUCK STATUS (Employee) ───────────────────

@router.get("/{task_id}/stuck-check")
async def check_stuck(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Frontend calls this every 30 seconds to check
    if the employee is stuck
    """
    try:
        task = await tasks_collection.find_one({
            "_id": ObjectId(task_id)
        })
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "in_progress":
        return {"is_stuck": False, "message": "Task not in progress"}

    if not task.get("started_at"):
        return {"is_stuck": False, "message": "Task not started"}

    # Get full stuck analysis
    info = get_stuck_info(task["started_at"], task["expected_time"])

    # If stuck and popup not shown yet → mark it
    if info["is_stuck"] and not task.get("stuck_triggered"):
        await tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "is_stuck": True,
                "stuck_triggered": True
            }}
        )

    return info

# ─── COMPLETE TASK (Employee) ─────────────────────────

@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Only employees can complete tasks"
        )

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

    if task["status"] == "completed":
        raise HTTPException(
            status_code=400,
            detail="Task already completed"
        )

    await tasks_collection.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }}
    )

    updated_task = await tasks_collection.find_one({
        "_id": ObjectId(task_id)
    })

    return {
        "message": "Task completed successfully",
        "task": format_task(updated_task)
    }

# ─── GET ALL TASKS (Manager) ──────────────────────────

@router.get("/all")
async def get_all_tasks(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "manager":
        raise HTTPException(
            status_code=403,
            detail="Only managers can view all tasks"
        )

    tasks = []
    async for task in tasks_collection.find(
        {"manager_id": str(current_user["_id"])}
    ):
        tasks.append(format_task(task))

    # Sort by priority number (1=Critical first)
    tasks.sort(key=lambda x: x["priority"])

    return {
        "total": len(tasks),
        "tasks": tasks
    }

# ─── GET SINGLE TASK ──────────────────────────────────

@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        task = await tasks_collection.find_one({
            "_id": ObjectId(task_id)
        })
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return format_task(task)