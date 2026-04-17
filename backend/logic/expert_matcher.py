from database import users_collection


async def find_best_expert(domain: str) -> dict | None:
    """
    Finds the best available expert for a given domain.

    Selection criteria:
    1. Must be an expert
    2. Must match the domain
    3. Must be available
    4. Among available experts, pick the one with:
       - Fewest active sessions (least busy)
       - Highest rating (most reliable)
    """

    candidates = []

    async for expert in users_collection.find({
        "role": "expert",
        "domain": domain,
        "is_available": True
    }):
        candidates.append(expert)

    if not candidates:
        # Try finding any available expert regardless of domain
        async for expert in users_collection.find({
            "role": "expert",
            "is_available": True
        }):
            candidates.append(expert)

    if not candidates:
        return None

    # Sort by: fewest active sessions first, then highest rating
    candidates.sort(
        key=lambda x: (
            x.get("active_sessions", 0),
            -x.get("rating", 0.0)
        )
    )

    return candidates[0]


async def mark_expert_busy(expert_id: str):
    """Increment expert active session count"""
    from bson import ObjectId
    await users_collection.update_one(
        {"_id": ObjectId(expert_id)},
        {"$inc": {"active_sessions": 1}}
    )


async def mark_expert_free(expert_id: str):
    """Decrement expert active session count"""
    from bson import ObjectId
    expert = await users_collection.find_one(
        {"_id": ObjectId(expert_id)}
    )

    if expert:
        new_sessions = max(0, expert.get("active_sessions", 1) - 1)
        is_available = True

        await users_collection.update_one(
            {"_id": ObjectId(expert_id)},
            {"$set": {
                "active_sessions": new_sessions,
                "is_available": is_available
            }}
        )


# find_best_expert()

# First looks for expert with matching domain
# If no domain match → falls back to any available expert
# Sorts by active_sessions first — least busy expert gets picked
# Then by rating — higher rated expert preferred if equal load

# mark_expert_busy()

# Called when expert accepts a session
# Increments active_sessions counter
# $inc → MongoDB increment operator

# mark_expert_free()

# Called when session is resolved
# Decrements active_sessions
# max(0, ...) → prevents going below 0