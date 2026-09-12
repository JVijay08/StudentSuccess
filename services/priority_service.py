from datetime import datetime, timezone

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
    """Return tasks ordered by procrastination risk.

    For each task the procrastination service computes a risk score and the
    plain-language reasons behind it. Results are sorted by score descending,
    then by earliest ``due_at`` on ties. Completed tasks score 0 and therefore
    fall to the end naturally, so no special-case handling is needed.

    Args:
        tasks: iterable of Task objects.
        now: optional timezone-aware datetime used for risk evaluation.

    Returns:
        A list of dicts shaped as
        ``[{"task": task, "score": int, "reasons": list[str]}, ...]``.
        An empty input yields an empty list.
    """
    prioritized = []
    for task in tasks:
        risk = explain_procrastination_risk(task, now=now)
        prioritized.append(
            {
                "task": task,
                "score": risk["score"],
                "reasons": risk["reasons"],
            }
        )

    prioritized.sort(
        key=lambda row: (-row["score"], _as_utc(row["task"].due_at))
    )

    return prioritized
