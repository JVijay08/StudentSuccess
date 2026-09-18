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

    factors = priority_factors(task, now)
    score = sum(factor["points"] for factor in factors)
    reasons = [factor["reason"] for factor in factors]

    if score >= 7:
        level = "HIGH"
    elif score >= 4:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not reasons:
        reasons.append("no current risk signals")

    return {"level": level, "score": score, "reasons": reasons, "factors": factors}


def calculate_procrastination_risk(task, now=None):
    return explain_procrastination_risk(task, now=now)["level"]


def priority_factors(task, now):
    """The single source of point contributions used for scoring and explanations."""
    if task.status == "completed":
        return []
    factors = []
    def add(key, label, points, reason, short):
        factors.append(dict(key=key, label=label, points=points, reason=reason, short=short))
    hours = (_as_utc(task.due_at) - _as_utc(now)).total_seconds() / 3600
    if task.started_at is None:
        add("start", "Not started", 2, "assignment has not been started", "not started yet")
    if hours < 0:
        add("deadline", "Deadline", 4, "deadline has passed", "the deadline has passed")
    elif hours <= 24:
        add("deadline", "Deadline", 3, "due in 24 hours or less", "due within 24 hours")
    elif hours <= 48:
        add("deadline", "Deadline", 2, "due in 48 hours or less", "due within 48 hours")
    elif hours <= 168:
        add("deadline", "Deadline", 1, "due within one week", "due within a week")
    if task.estimated_minutes >= 60:
        add("effort", "Estimated duration", 2 if task.estimated_minutes >= 120 else 1,
            f"estimated workload is {task.estimated_minutes} minutes", f"you estimated {task.estimated_minutes} minutes")
    if task.difficulty == "high":
        add("challenge", "Your challenge rating", 1, "you rated this task as challenging", "you rated it challenging")
    if task.interest_level == "low":
        add("interest", "Your interest rating", 1, "you rated your interest in this task as low", "you rated your interest low")
    return factors
