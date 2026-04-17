from datetime import datetime


def get_time_spent_minutes(started_at: datetime) -> float:
    now = datetime.utcnow()
    diff = now - started_at
    minutes = diff.total_seconds() / 60
    return round(minutes, 2)


def is_stuck(started_at: datetime, expected_time: int) -> bool:
    time_spent = get_time_spent_minutes(started_at)
    threshold = expected_time * 1.25
    return time_spent >= threshold


def get_stuck_info(started_at: datetime, expected_time: int) -> dict:
    time_spent = get_time_spent_minutes(started_at)
    threshold = expected_time * 1.25
    percentage = round((time_spent / expected_time) * 100, 1)

    return {
        "time_spent_minutes": time_spent,
        "expected_minutes": expected_time,
        "threshold_minutes": threshold,
        "percentage_used": percentage,
        "is_stuck": time_spent >= threshold,
        "should_warn": time_spent >= (expected_time * 1.0)
    }


# get_time_spent_minutes()

# Takes started_at datetime
# Subtracts from current time
# Returns minutes as decimal e.g. 47.3


# is_stuck()

# Core detection logic
# threshold = expected_time * 1.25
# If expected is 60 mins → threshold is 75 mins
# Returns True or False


# get_stuck_info()

# Returns full picture for frontend
# percentage_used → shows employee how far they are
# should_warn → warns at 100% (before stuck trigger at 125%)
# Frontend uses this to turn timer amber at 100%, red at 125%