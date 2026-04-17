from datetime import datetime


def calculate_priority_score(
    task_priority: int,
    time_spent_minutes: float,
    detected_emotions: dict
) -> float:
    """
    Calculates a priority score for a help request.
    Higher score = more urgent = comes first in queue.

    Formula:
        priority_weight  → based on task priority (1-5)
        time_weight      → based on minutes stuck
        emotion_weight   → based on detected emotions
    """

    # Priority weight — lower number = higher urgency
    # Priority 1 (Critical) = 100 points
    # Priority 5 (Very Low) = 20 points
    priority_weight = (6 - task_priority) * 20

    # Time weight — more time stuck = more urgent
    # Every minute stuck adds 0.5 points
    time_weight = time_spent_minutes * 0.5

    # Emotion weight — certain emotions add urgency
    emotion_weight = 0
    emotion_scores = {
        "needassistance": 30,
        "giveup": 25,
        "stressed": 15,
        "confused": 10,
        "exhausted": 10,
        "annoyed": 5
    }

    for emotion, boost in emotion_scores.items():
        if detected_emotions.get(emotion, 0) > 0.5:
            emotion_weight += boost

    # Final score
    final_score = priority_weight + time_weight + emotion_weight

    return round(final_score, 2)


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


# Weight of priority

# Task priority 1 (Critical) → (6-1) x 20 = 100 points
# Task priority 2 (High)     → (6-2) x 20 = 80 points
# Task priority 3 (Medium)   → (6-3) x 20 = 60 points
# Task priority 4 (Low)      → (6-4) x 20 = 40 points
# Task priority 5 (Very Low) → (6-5) x 20 = 20 points

#Time weight

# Stuck 10 mins  → 5 points
# Stuck 30 mins  → 15 points
# Stuck 60 mins  → 30 points

# Emotion weight

# needassistance detected → +30 points
# giveup detected        → +25 points
# stressed detected      → +15 points