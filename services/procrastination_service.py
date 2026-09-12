from datetime import datetime, timezone


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def explain_procrastination_risk(task, now=None):
    now = _as_utc(now or datetime.now(timezone.utc))

    if task.status == "completed":
        return {
            "level": "LOW",
            "score": 0,
            "reasons": ["task is already completed"],
        }

    score = 0
    reasons = []
    due_at = _as_utc(task.due_at)
    hours_until_due = (due_at - now).total_seconds() / 3600

    if task.started_at is None:
        score += 2
        reasons.append("assignment has not been started")

    if hours_until_due < 0:
        score += 4
        reasons.append("deadline has passed")
    elif hours_until_due <= 24:
        score += 3
        reasons.append("due in 24 hours or less")
    elif hours_until_due <= 48:
        score += 2
        reasons.append("due in 48 hours or less")
    elif hours_until_due <= 168:
        score += 1
        reasons.append("due within one week")

    if task.estimated_minutes >= 120:
        score += 2
        reasons.append(
            f"estimated workload is {task.estimated_minutes} minutes"
        )
    elif task.estimated_minutes >= 60:
        score += 1
        reasons.append(
            f"estimated workload is {task.estimated_minutes} minutes"
        )

    if task.difficulty == "high":
        score += 1
        reasons.append("difficulty is high")

    if task.interest_level == "low":
        score += 1
        reasons.append("interest level is low")

    if score >= 7:
        level = "HIGH"
    elif score >= 4:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not reasons:
        reasons.append("no current risk signals")

    return {"level": level, "score": score, "reasons": reasons}


def calculate_procrastination_risk(task, now=None):
    return explain_procrastination_risk(task, now=now)["level"]
