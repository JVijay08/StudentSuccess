"""Pure history-driven suggestion logic layered on top of the existing scorer.

This module is intentionally pure: it performs no database writes and persists
no derived values. It composes ``priority_service`` (which itself composes
``procrastination_service.explain_procrastination_risk``) without modifying
either — the History_Bonus is a small additive integer laid on top of the
existing Risk_Score. It is importable without a Flask app context.
"""

from datetime import timedelta

from services import delay_service, priority_service


def history_bonus(task, averages_by_group):
    """Return the History_Bonus (an int in ``{0, 1, 2}``) for a task.

    Rules, applied only when the task's group is present in
    ``averages_by_group`` (i.e. the group met ``MINIMUM_SAMPLE``):

        avg <= 1h        -> 0   (includes zero/negative averages)
        1h < avg <= 4h   -> 1
        avg > 4h         -> 2

    Returns 0 when the task is completed, or when its group is absent from
    ``averages_by_group`` (below the minimum sample). Never negative.
    """
    if task.status == "completed":
        return 0

    group = delay_service.group_key(task)
    if group not in averages_by_group:
        return 0

    avg = averages_by_group[group]
    if avg <= 1:
        return 0
    if avg <= 4:
        return 1
    return 2


def bonus_reason(task, averages_by_group):
    """Return a plain-language reason for the History_Bonus, or ``None``.

    Names the group and the rounded average, e.g.
    ``"you start Math tasks about 3 hr late on average"``. Returns ``None``
    whenever the bonus would be 0 (no group history, below sample, or
    ``avg <= 1h``).
    """
    if history_bonus(task, averages_by_group) == 0:
        return None

    group = delay_service.group_key(task)
    avg = averages_by_group[group]
    return f"you start {group} tasks about {round(avg)} hr late on average"


def get_suggested_tasks(tasks, now=None):
    """Combined ranking layered on ``priority_service``.

    Steps:
      1. Compute per-group averages from the completed tasks within ``tasks``
         (``delay_service`` filters to qualifying completed tasks internally).
      2. Obtain base rows from ``priority_service.get_prioritized_tasks`` for the
         active (non-completed) tasks — ``explain_procrastination_risk`` is
         left untouched.
      3. For each base row, add the per-task History_Bonus to the base score
         and append the bonus reason (when present) to a COPY of the base
         reasons — the priority_service output is never mutated in place.
      4. Re-sort by combined score DESC, then earliest ``due_at`` ASC on ties.

    Returns a list of dicts shaped as
    ``[{"task", "score" (combined), "base_score", "bonus", "reasons"}, ...]``.
    """
    averages = delay_service.average_start_delay_by_group(tasks)

    active = [task for task in tasks if task.status != "completed"]
    base_rows = priority_service.get_prioritized_tasks(active, now=now)

    rows = []
    for base_row in base_rows:
        task = base_row["task"]
        bonus = history_bonus(task, averages)
        combined = base_row["score"] + bonus
        reasons = list(base_row["reasons"])
        reason = bonus_reason(task, averages)
        if reason:
            reasons.append(reason)
        rows.append(
            {
                "task": task,
                "score": combined,
                "base_score": base_row["score"],
                "bonus": bonus,
                "reasons": reasons,
            }
        )

    rows.sort(
        key=lambda row: (-row["score"], delay_service._as_utc(row["task"].due_at))
    )
    return rows


def realism_warning(cleaned_task_like, averages_by_group):
    """Return a non-blocking realism warning string, or ``None``.

    ``cleaned_task_like`` is duck-typed and must expose ``planned_start_at``,
    ``due_at``, ``estimated_minutes``, ``subject`` and ``task_type``.

      - Returns ``None`` if ``planned_start_at`` is missing.
      - Returns ``None`` if the task's group is absent from
        ``averages_by_group`` (below the minimum sample).
      - Otherwise projects a finish time of
        ``planned_start_at + avg_delay + estimated_minutes`` and returns a
        warning naming the group and rounded average when that projected finish
        is later than ``due_at``; ``None`` when there is enough time.

    All datetimes are normalized to UTC before comparison.
    """
    if cleaned_task_like.planned_start_at is None:
        return None

    group = delay_service.group_key(cleaned_task_like)
    if group not in averages_by_group:
        return None

    avg = averages_by_group[group]
    projected_finish = (
        delay_service._as_utc(cleaned_task_like.planned_start_at)
        + timedelta(hours=avg)
        + timedelta(minutes=cleaned_task_like.estimated_minutes)
    )
    if projected_finish > delay_service._as_utc(cleaned_task_like.due_at):
        return (
            f"Based on how you usually start {group} tasks "
            f"(~{round(avg)} hr late), this may be cutting it close."
        )
    return None
