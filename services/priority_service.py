from datetime import datetime, timezone

from services.task_policy import ranking_key, tier
from services.procrastination_service import explain_procrastination_risk


def _as_utc(value):
    """Normalize a datetime to timezone-aware UTC for a safe sort comparison.

    Mirrors the pattern in ``procrastination_service`` so naive values stored
    in the database do not break ordering against timezone-aware values.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_prioritized_tasks(tasks, now=None):
    """Return tasks ordered by work-status / urgency tier, then explained risk.

    For each task the procrastination service computes a risk score and the
    plain-language reasons behind it. Within each tier, score descends, then deadline, planned start, and stable
    ID/title break ties. Completed tasks occupy a separate final tier.

    Args:
        tasks: iterable of Task objects.
        now: optional timezone-aware datetime used for risk evaluation.

    Returns:
        A list of dicts shaped as
        ``[{"task": task, "score": int, "reasons": list[str]}, ...]``.
        An empty input yields an empty list.
    """
    now = now or datetime.now(timezone.utc)
    prioritized = []
    for task in tasks:
        risk = explain_procrastination_risk(task, now=now)
        prioritized.append(
            {
                "task": task,
                "tier": tier(task, now),
                "score": risk["score"],
                "reasons": risk["reasons"],
                "factors": risk.get("factors", []),
            }
        )

    prioritized.sort(
        key=lambda row: ranking_key(row, now)
    )

    return prioritized
