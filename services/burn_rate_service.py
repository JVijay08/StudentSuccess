"""Pure estimate-accuracy (burn-rate) computation.

Performs no database writes and persists no derived value. Actual_Duration,
Burn_Rate, Group_Burn_Rate, and Overall_Burn_Rate are computed on the fly from
existing Task fields. Importable without a Flask app context.
"""

from datetime import datetime, timezone

from services import delay_service

# Reuse the established grouping precedence and sample threshold so they cannot
# drift from delay_service. delay_service is NOT modified.
group_key = delay_service.group_key                 # subject | task_type | "ungrouped"
MINIMUM_SAMPLE = delay_service.MINIMUM_SAMPLE        # == 2

# Closed tolerance band: within [0.95, 1.05] estimates are "accurate".
TOLERANCE_LOW = 0.95
TOLERANCE_HIGH = 1.05


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC.

    Naive values (SQLite returns naive datetimes on read) are treated as UTC.
    Byte-for-byte identical in behavior to ``delay_service._as_utc``;
    re-declared locally to avoid depending on another module's private helper.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_measurable(task) -> bool:
    """True iff the task has usable actual-time data.

    Requires ``status == "completed"`` AND ``started_at is not None`` AND
    ``completed_at is not None``. Reads only existing fields; persists nothing.
    """
    return (
        task.status == "completed"
        and task.started_at is not None
        and task.completed_at is not None
    )


def actual_duration_minutes(task) -> float:
    """Signed elapsed minutes: ``_as_utc(completed_at) - _as_utc(started_at)``.

    Both timestamps normalized to UTC before subtraction (naive treated as
    UTC). SIGNED: a ``completed_at`` earlier than ``started_at`` yields a
    negative value; this function does not raise and leaves interpretation to
    callers (Requirement 2.5). Never calls ``datetime.utcnow()``. Computed on
    the fly.
    """
    recorded = getattr(task, "actual_minutes", None)
    if recorded is not None:
        return float(recorded)
    delta = _as_utc(task.completed_at) - _as_utc(task.started_at)
    return delta.total_seconds() / 60.0


def task_burn_rate(task) -> float:
    """Per-task Burn_Rate: ``actual_duration_minutes(task) / estimated_minutes``.

    ``estimated_minutes`` is a validated positive integer (1-1440), so the
    denominator is always positive. Returned unrounded (Requirement 3.3).
    """
    return actual_duration_minutes(task) / task.estimated_minutes


def interpret(rate: float) -> str:
    """Plain-language label for a burn rate (unrounded rate expected).

    - ``TOLERANCE_LOW <= rate <= TOLERANCE_HIGH`` -> "estimates are accurate"
    - ``rate > TOLERANCE_HIGH`` -> ``f"runs ~{round((rate - 1) * 100)}% over"``
    - ``rate < TOLERANCE_LOW``  -> ``f"finishes ~{round((1 - rate) * 100)}% early"``

    Never exposes the raw ratio in the label text (Requirement 5.5).
    """
    if TOLERANCE_LOW <= rate <= TOLERANCE_HIGH:
        return "estimates are accurate"
    if rate > TOLERANCE_HIGH:
        return f"runs ~{round((rate - 1) * 100)}% over"
    return f"finishes ~{round((1 - rate) * 100)}% early"


def _is_eligible(task) -> bool:
    """A task contributes to display aggregates.

    Eligible = Measurable_Task whose ``actual_duration_minutes`` is strictly
    greater than 0. Negative or zero durations are data anomalies excluded from
    display aggregates while remaining measurable and signed at the primitive
    level.
    """
    return is_measurable(task) and actual_duration_minutes(task) > 0


def group_burn_rates(tasks) -> "list[dict]":
    """Per-Group mean burn rate for Groups meeting Minimum_Sample.

    Considers only eligible tasks (``is_measurable`` AND
    ``actual_duration_minutes > 0``). Groups the eligible tasks by
    ``group_key(task)``; for each Group with at least ``MINIMUM_SAMPLE``
    eligible tasks, computes the arithmetic mean of the members' per-task burn
    rates.

    Returns rows ``{"group": str, "rate": round(mean, 2),
    "label": interpret(unrounded_mean)}``. The label is derived from the
    UNROUNDED mean. Rows are sorted by ``rate`` DESCENDING (largest
    over-estimate first). Groups below ``MINIMUM_SAMPLE`` are omitted. Performs
    no DB writes and does not mutate inputs.
    """
    rates_by_group: "dict[str, list[float]]" = {}
    for task in tasks:
        if not _is_eligible(task):
            continue
        rates_by_group.setdefault(group_key(task), []).append(task_burn_rate(task))

    rows: "list[dict]" = []
    for key, rates in rates_by_group.items():
        if len(rates) < MINIMUM_SAMPLE:
            continue
        mean = sum(rates) / len(rates)
        rows.append({"group": key, "rate": round(mean, 2), "label": interpret(mean)})

    rows.sort(key=lambda row: row["rate"], reverse=True)
    return rows


def overall_burn_rate(tasks) -> "dict | None":
    """Overall mean burn rate across ALL eligible Measurable_Tasks.

    Eligible = Measurable_Task with ``actual_duration_minutes > 0``, regardless
    of Group. When the eligible count is ``>= MINIMUM_SAMPLE``, returns
    ``{"rate": round(mean, 2), "label": interpret(unrounded_mean)}``; otherwise
    returns ``None`` (absence signals insufficient data). Performs no DB writes
    and does not mutate inputs.
    """
    rates = [task_burn_rate(task) for task in tasks if _is_eligible(task)]
    if len(rates) < MINIMUM_SAMPLE:
        return None
    mean = sum(rates) / len(rates)
    return {"rate": round(mean, 2), "label": interpret(mean)}
