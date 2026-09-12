"""Example-based unit tests for services/suggestion_service.py."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services import delay_service, priority_service
from services.suggestion_service import (
    bonus_reason,
    get_suggested_tasks,
    history_bonus,
    realism_warning,
)


def _task(
    *,
    status="not_started",
    subject=None,
    task_type=None,
    due_at=None,
    estimated_minutes=30,
    difficulty="low",
    interest_level="high",
    planned_start_at=None,
    started_at=None,
    completed_at=None,
):
    """Build a duck-typed task stand-in with all attributes suggestion_service
    and its collaborators read."""
    if due_at is None:
        due_at = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        status=status,
        subject=subject,
        task_type=task_type,
        due_at=due_at,
        estimated_minutes=estimated_minutes,
        difficulty=difficulty,
        interest_level=interest_level,
        planned_start_at=planned_start_at,
        started_at=started_at,
        completed_at=completed_at,
    )


# ---------------------------------------------------------------------------
# history_bonus thresholds
# ---------------------------------------------------------------------------

def test_history_bonus_zero_when_avg_at_or_below_one_hour():
    task = _task(subject="Math")
    assert history_bonus(task, {"Math": 1.0}) == 0
    assert history_bonus(task, {"Math": 0.0}) == 0
    assert history_bonus(task, {"Math": -3.0}) == 0


def test_history_bonus_one_when_avg_between_one_and_four_hours():
    task = _task(subject="Math")
    assert history_bonus(task, {"Math": 1.01}) == 1
    assert history_bonus(task, {"Math": 3.0}) == 1
    assert history_bonus(task, {"Math": 4.0}) == 1


def test_history_bonus_two_when_avg_above_four_hours():
    task = _task(subject="Math")
    assert history_bonus(task, {"Math": 4.01}) == 2
    assert history_bonus(task, {"Math": 10.0}) == 2


def test_history_bonus_zero_when_group_absent():
    task = _task(subject="Math")
    assert history_bonus(task, {"English": 5.0}) == 0
    assert history_bonus(task, {}) == 0


def test_history_bonus_zero_for_completed_task():
    task = _task(subject="Math", status="completed")
    assert history_bonus(task, {"Math": 5.0}) == 0


# ---------------------------------------------------------------------------
# bonus_reason
# ---------------------------------------------------------------------------

def test_bonus_reason_names_group_and_rounded_average():
    task = _task(subject="Math")
    reason = bonus_reason(task, {"Math": 3.4})
    assert reason == "you start Math tasks about 3 hr late on average"


def test_bonus_reason_rounds_average_to_nearest_hour():
    task = _task(subject="History")
    reason = bonus_reason(task, {"History": 4.6})
    assert reason == "you start History tasks about 5 hr late on average"


def test_bonus_reason_none_when_bonus_zero_below_or_at_threshold():
    task = _task(subject="Math")
    assert bonus_reason(task, {"Math": 1.0}) is None


def test_bonus_reason_none_when_group_absent():
    task = _task(subject="Math")
    assert bonus_reason(task, {}) is None


# ---------------------------------------------------------------------------
# get_suggested_tasks
# ---------------------------------------------------------------------------

def _late_math_history(planned=None):
    """Two completed Math tasks each started 3 hours late -> avg 3.0 hr."""
    if planned is None:
        planned = datetime(2024, 5, 1, 8, 0, tzinfo=timezone.utc)
    make = lambda: _task(
        subject="Math", status="completed",
        planned_start_at=planned,
        started_at=planned + timedelta(hours=3),
        completed_at=planned + timedelta(hours=5),
    )
    return [make(), make()]


def test_get_suggested_tasks_preserves_base_score_and_adds_bonus():
    # A Math task due in ~10 hours: not started (+2), due <=24h (+3) => base 5.
    now = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    active = _task(
        subject="Math",
        status="not_started",
        due_at=now + timedelta(hours=10),
    )
    tasks = _late_math_history() + [active]  # history yields avg 3.0 -> bonus 1

    rows = get_suggested_tasks(tasks, now=now)

    assert len(rows) == 1  # only the active task is ranked
    row = rows[0]
    # base_score equals what priority_service reports for the same active set.
    base = priority_service.get_prioritized_tasks([active], now=now)[0]
    assert row["base_score"] == base["score"]
    assert row["bonus"] == 1
    assert row["score"] == row["base_score"] + row["bonus"]


def test_get_suggested_tasks_appends_bonus_reason_and_keeps_base_reasons():
    now = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    active = _task(
        subject="Math",
        status="not_started",
        due_at=now + timedelta(hours=10),
    )
    tasks = _late_math_history() + [active]
    base_reasons = priority_service.get_prioritized_tasks([active], now=now)[0][
        "reasons"
    ]

    rows = get_suggested_tasks(tasks, now=now)
    reasons = rows[0]["reasons"]

    # All base reasons still present.
    for base_reason in base_reasons:
        assert base_reason in reasons
    # The base reasons never contain the bonus reason on their own.
    bonus_text = "you start Math tasks about 3 hr late on average"
    assert bonus_text not in base_reasons
    # Bonus reason appended at the end.
    assert reasons[-1] == bonus_text


def test_get_suggested_tasks_does_not_mutate_priority_service_output():
    now = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    task = _task(
        subject="Math",
        status="not_started",
        due_at=now + timedelta(hours=10),
    )
    original = priority_service.get_prioritized_tasks([task], now=now)
    original_len = len(original[0]["reasons"])

    get_suggested_tasks([task], now=now)

    # Re-fetch base reasons; the earlier suggestion call must not have mutated
    # any shared reasons list.
    refetched = priority_service.get_prioritized_tasks([task], now=now)
    assert len(refetched[0]["reasons"]) == original_len


def test_get_suggested_tasks_completed_task_excluded_from_ranking():
    now = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    completed = _task(subject="Math", status="completed")
    active = _task(subject="Math", status="not_started",
                   due_at=now + timedelta(hours=10))

    rows = get_suggested_tasks([completed, active], now=now)

    # Completed task is not ranked (priority_service only receives active).
    ranked_tasks = [row["task"] for row in rows]
    assert active in ranked_tasks
    assert completed not in ranked_tasks


def test_get_suggested_tasks_sorted_by_combined_score_desc():
    now = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    # High base + bonus.
    high = _task(subject="Math", status="not_started",
                 due_at=now + timedelta(hours=10), estimated_minutes=120)
    # Low base, no bonus (group absent).
    low = _task(subject="Art", status="not_started",
                due_at=now + timedelta(days=30))

    rows = get_suggested_tasks([high, low], now=now)
    scores = [row["score"] for row in rows]
    assert scores == sorted(scores, reverse=True)
    assert rows[0]["task"] is high


def test_get_suggested_tasks_tie_broken_by_earlier_due_at():
    now = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    # Two identical-scoring tasks (same signals) with different deadlines, no
    # history so no bonus differentiates them.
    earlier = _task(subject="Math", status="not_started",
                    due_at=now + timedelta(hours=5))
    later = _task(subject="Science", status="not_started",
                  due_at=now + timedelta(hours=10))

    rows = get_suggested_tasks([later, earlier], now=now)

    assert rows[0]["score"] == rows[1]["score"]
    assert rows[0]["task"] is earlier
    assert rows[1]["task"] is later


def test_get_suggested_tasks_end_to_end_with_real_delay_service():
    """Feed real completed tasks so delay_service produces the averages."""
    now = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    planned = datetime(2024, 5, 1, 8, 0, tzinfo=timezone.utc)

    # Two completed Math tasks each started 3 hours late -> avg 3.0 hr -> bonus 1.
    c1 = _task(
        subject="Math", status="completed",
        planned_start_at=planned,
        started_at=planned + timedelta(hours=3),
        completed_at=planned + timedelta(hours=5),
    )
    c2 = _task(
        subject="Math", status="completed",
        planned_start_at=planned,
        started_at=planned + timedelta(hours=3),
        completed_at=planned + timedelta(hours=5),
    )
    active = _task(subject="Math", status="not_started",
                   due_at=now + timedelta(hours=10))

    averages = delay_service.average_start_delay_by_group([c1, c2, active])
    assert averages["Math"] == 3.0

    rows = get_suggested_tasks([c1, c2, active], now=now)
    active_row = next(row for row in rows if row["task"] is active)
    assert active_row["bonus"] == 1
    assert active_row["reasons"][-1] == (
        "you start Math tasks about 3 hr late on average"
    )


# ---------------------------------------------------------------------------
# realism_warning
# ---------------------------------------------------------------------------

def test_realism_warning_tight_deadline_returns_warning():
    planned = datetime(2024, 6, 1, 8, 0, tzinfo=timezone.utc)
    # avg 5 hr late + 120 min estimate => finishes ~7 hr after planned start.
    task = _task(
        subject="Math",
        planned_start_at=planned,
        due_at=planned + timedelta(hours=3),
        estimated_minutes=120,
    )
    warning = realism_warning(task, {"Math": 5.0})
    assert warning is not None
    assert "Math" in warning
    assert "5 hr late" in warning


def test_realism_warning_comfortable_deadline_returns_none():
    planned = datetime(2024, 6, 1, 8, 0, tzinfo=timezone.utc)
    task = _task(
        subject="Math",
        planned_start_at=planned,
        due_at=planned + timedelta(hours=24),
        estimated_minutes=30,
    )
    assert realism_warning(task, {"Math": 2.0}) is None


def test_realism_warning_none_without_planned_start():
    task = _task(
        subject="Math",
        planned_start_at=None,
        due_at=datetime(2024, 6, 1, 8, 0, tzinfo=timezone.utc),
        estimated_minutes=120,
    )
    assert realism_warning(task, {"Math": 5.0}) is None


def test_realism_warning_none_when_group_below_sample():
    planned = datetime(2024, 6, 1, 8, 0, tzinfo=timezone.utc)
    task = _task(
        subject="Math",
        planned_start_at=planned,
        due_at=planned + timedelta(minutes=1),
        estimated_minutes=120,
    )
    # Group absent from averages => below sample => no warning.
    assert realism_warning(task, {}) is None

# ==========================================================================
# Property-based tests (Hypothesis) — Task 7.2
# ==========================================================================

import pytest
from hypothesis import given, strategies as st

from services.procrastination_service import explain_procrastination_risk

# Fixed reference "now" so ordering/scoring is deterministic across examples.
_NOW = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Reusable strategies
# ---------------------------------------------------------------------------

# due_at spread across "already overdue" through "weeks away" so every
# procrastination signal band is exercised.
_due_offset_minutes = st.integers(min_value=-2880, max_value=40320)

# A small, reusable group namespace so history can actually attach to tasks.
_group_names = st.sampled_from(["Math", "English", "Science", "Art", "History"])


def _active_task_strategy():
    """Hypothesis strategy for an ACTIVE (non-completed) duck-typed task."""
    return st.builds(
        lambda subject, offset, est, diff, interest, started: _task(
            status="in_progress" if started else "not_started",
            subject=subject,
            due_at=_NOW + timedelta(minutes=offset),
            estimated_minutes=est,
            difficulty=diff,
            interest_level=interest,
            started_at=(_NOW - timedelta(hours=1)) if started else None,
        ),
        subject=_group_names,
        offset=_due_offset_minutes,
        est=st.integers(min_value=1, max_value=1440),
        diff=st.sampled_from(["low", "medium", "high"]),
        interest=st.sampled_from(["low", "medium", "high"]),
        started=st.booleans(),
    )


def _averages_strategy():
    """Random averages_by_group mapping over the known group names (hours)."""
    return st.dictionaries(
        keys=_group_names,
        values=st.floats(
            min_value=-5, max_value=50, allow_nan=False, allow_infinity=False
        ),
        max_size=5,
    )


# Feature: history-driven-suggestions, Property 1: History_Bonus additive/bounded/non-negative
@given(task=_active_task_strategy(), averages=_averages_strategy())
def test_bonus_additive_bounded(task, averages):
    rows = get_suggested_tasks([task], now=_NOW)
    assert len(rows) == 1
    row = rows[0]
    assert row["bonus"] in {0, 1, 2}
    assert row["bonus"] >= 0
    assert row["score"] == row["base_score"] + row["bonus"]


# Feature: history-driven-suggestions, Property 2: base_score equals explain_procrastination_risk score
@given(task=_active_task_strategy(), averages=_averages_strategy())
def test_base_score_matches_risk(task, averages):
    rows = get_suggested_tasks([task], now=_NOW)
    expected = explain_procrastination_risk(task, now=_NOW)["score"]
    assert rows[0]["base_score"] == expected
    # Base reasons are a subset of the row's reasons.
    base_reasons = explain_procrastination_risk(task, now=_NOW)["reasons"]
    for reason in base_reasons:
        assert reason in rows[0]["reasons"]


# Feature: history-driven-suggestions, Property 3: History_Bonus threshold correctness
@given(
    avg=st.floats(
        min_value=-5, max_value=50, allow_nan=False, allow_infinity=False
    )
)
def test_bonus_threshold_correct(avg):
    task = _task(subject="Math", status="not_started")
    bonus = history_bonus(task, {"Math": avg})
    if avg <= 1:
        assert bonus == 0
    elif avg <= 4:
        assert bonus == 1
    else:
        assert bonus == 2


# Feature: history-driven-suggestions, Property 4: Suggested-task sort invariant
@given(tasks=st.lists(_active_task_strategy(), min_size=0, max_size=12))
def test_suggested_sort_invariant(tasks):
    rows = get_suggested_tasks(tasks, now=_NOW)
    for earlier, later in zip(rows, rows[1:]):
        # Non-increasing combined score.
        assert earlier["score"] >= later["score"]
        # Ties broken by earlier due_at first.
        if earlier["score"] == later["score"]:
            e_due = delay_service._as_utc(earlier["task"].due_at)
            l_due = delay_service._as_utc(later["task"].due_at)
            assert e_due <= l_due


# Feature: history-driven-suggestions, Property 5: Realism warning iff
@given(
    planned_offset=st.integers(min_value=-1440, max_value=1440),
    due_offset=st.integers(min_value=-1440, max_value=4320),
    estimate=st.integers(min_value=1, max_value=1440),
    avg=st.floats(
        min_value=-5, max_value=50, allow_nan=False, allow_infinity=False
    ),
    group_present=st.booleans(),
    has_planned=st.booleans(),
)
def test_realism_warning_boundary(
    planned_offset, due_offset, estimate, avg, group_present, has_planned
):
    base = datetime(2024, 6, 1, 8, 0, tzinfo=timezone.utc)
    planned = base + timedelta(minutes=planned_offset) if has_planned else None
    due = base + timedelta(minutes=due_offset)
    task = _task(
        subject="Math",
        planned_start_at=planned,
        due_at=due,
        estimated_minutes=estimate,
    )
    averages = {"Math": avg} if group_present else {}

    result = realism_warning(task, averages)

    # Reconstruct the iff condition independently.
    should_warn = False
    if has_planned and group_present:
        projected = (
            delay_service._as_utc(planned)
            + timedelta(hours=avg)
            + timedelta(minutes=estimate)
        )
        should_warn = projected > delay_service._as_utc(due)

    if should_warn:
        assert result is not None
    else:
        assert result is None


# Feature: history-driven-suggestions, Property 7: Min-sample fallback equals priority_service ordering
@given(
    st.lists(
        st.fixed_dictionaries(
            {
                "offset": _due_offset_minutes,
                "est": st.integers(min_value=1, max_value=1440),
                "diff": st.sampled_from(["low", "medium", "high"]),
                "interest": st.sampled_from(["low", "medium", "high"]),
            }
        ),
        min_size=0,
        max_size=10,
    )
)
def test_fallback_matches_priority(specs):
    # Give each active task a UNIQUE group so no group can reach MINIMUM_SAMPLE
    # (2) qualifying completed tasks. Add at most one completed qualifying task
    # per group, guaranteeing every group stays below the sample threshold.
    active = []
    completed = []
    for index, spec in enumerate(specs):
        group = f"grp-{index}"
        active_task = _task(
            subject=group,
            status="not_started",
            due_at=_NOW + timedelta(minutes=spec["offset"]),
            estimated_minutes=spec["est"],
            difficulty=spec["diff"],
            interest_level=spec["interest"],
        )
        active.append(active_task)
        planned = _NOW - timedelta(days=1)
        completed.append(
            _task(
                subject=group,
                status="completed",
                planned_start_at=planned,
                started_at=planned + timedelta(hours=3),
                completed_at=planned + timedelta(hours=5),
            )
        )

    all_tasks = active + completed
    rows = get_suggested_tasks(all_tasks, now=_NOW)

    # No bonus anywhere (every group below sample).
    assert all(row["bonus"] == 0 for row in rows)

    # Order matches priority_service on the same active tasks.
    base_rows = priority_service.get_prioritized_tasks(active, now=_NOW)
    assert [row["task"] for row in rows] == [b["task"] for b in base_rows]


# Feature: history-driven-suggestions, Property 8: Completed tasks no bonus
@given(averages=_averages_strategy())
def test_completed_no_bonus(averages):
    task = _task(subject="Math", status="completed")
    assert history_bonus(task, averages) == 0
