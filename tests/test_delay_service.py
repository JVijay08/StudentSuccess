"""Example-based unit tests for services/delay_service.py.

These tests use lightweight SimpleNamespace stand-ins for Task objects so the
pure delay service can be exercised without a Flask app or database.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from services.delay_service import (
    average_start_delay_by_group,
    format_start_delay,
    group_key,
    start_delay,
)


def _task(
    status="completed",
    subject="Math",
    task_type="homework",
    planned_start_at=None,
    started_at=None,
):
    return SimpleNamespace(
        status=status,
        subject=subject,
        task_type=task_type,
        planned_start_at=planned_start_at,
        started_at=started_at,
    )


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# --- start_delay ---------------------------------------------------------


def test_start_delay_late_is_positive():
    task = _task(
        planned_start_at=_utc(2024, 1, 1, 9, 0),
        started_at=_utc(2024, 1, 1, 11, 30),
    )
    assert start_delay(task) == timedelta(hours=2, minutes=30)


def test_start_delay_early_is_negative():
    task = _task(
        planned_start_at=_utc(2024, 1, 1, 9, 0),
        started_at=_utc(2024, 1, 1, 8, 45),
    )
    assert start_delay(task) == timedelta(minutes=-15)


def test_start_delay_exactly_zero():
    moment = _utc(2024, 1, 1, 9, 0)
    task = _task(planned_start_at=moment, started_at=moment)
    assert start_delay(task) == timedelta(0)


def test_start_delay_none_when_planned_missing():
    task = _task(planned_start_at=None, started_at=_utc(2024, 1, 1, 9, 0))
    assert start_delay(task) is None


def test_start_delay_none_when_started_missing():
    task = _task(planned_start_at=_utc(2024, 1, 1, 9, 0), started_at=None)
    assert start_delay(task) is None


def test_start_delay_handles_naive_datetime():
    # Naive datetimes (as SQLite may return) are treated as UTC and must not crash.
    naive_planned = datetime(2024, 1, 1, 9, 0)
    naive_started = datetime(2024, 1, 1, 10, 0)
    task = _task(planned_start_at=naive_planned, started_at=naive_started)
    assert start_delay(task) == timedelta(hours=1)


# --- group_key -----------------------------------------------------------


def test_group_key_subject_wins():
    task = _task(subject="English", task_type="essay")
    assert group_key(task) == "English"


def test_group_key_falls_back_to_task_type_when_subject_blank():
    task = _task(subject="   ", task_type="essay")
    assert group_key(task) == "essay"


def test_group_key_falls_back_to_task_type_when_subject_none():
    task = _task(subject=None, task_type="essay")
    assert group_key(task) == "essay"


def test_group_key_ungrouped_when_both_blank():
    task = _task(subject="  ", task_type=None)
    assert group_key(task) == "ungrouped"


# --- average_start_delay_by_group ---------------------------------------


def test_average_group_with_two_qualifying_tasks_returns_mean_hours():
    tasks = [
        _task(
            subject="Math",
            planned_start_at=_utc(2024, 1, 1, 9, 0),
            started_at=_utc(2024, 1, 1, 11, 0),  # 2 hr late
        ),
        _task(
            subject="Math",
            planned_start_at=_utc(2024, 1, 2, 9, 0),
            started_at=_utc(2024, 1, 2, 13, 0),  # 4 hr late
        ),
    ]
    averages = average_start_delay_by_group(tasks)
    assert set(averages) == {"Math"}
    assert averages["Math"] == pytest.approx(3.0)


def test_average_group_with_single_qualifying_task_is_omitted():
    tasks = [
        _task(
            subject="Science",
            planned_start_at=_utc(2024, 1, 1, 9, 0),
            started_at=_utc(2024, 1, 1, 10, 0),
        ),
    ]
    assert average_start_delay_by_group(tasks) == {}


def test_average_excludes_non_qualifying_tasks():
    tasks = [
        # Qualifying Math tasks (2) -> included.
        _task(
            subject="Math",
            planned_start_at=_utc(2024, 1, 1, 9, 0),
            started_at=_utc(2024, 1, 1, 10, 0),  # 1 hr
        ),
        _task(
            subject="Math",
            planned_start_at=_utc(2024, 1, 2, 9, 0),
            started_at=_utc(2024, 1, 2, 12, 0),  # 3 hr
        ),
        # Not completed -> excluded even though timestamps present.
        _task(
            status="in_progress",
            subject="Math",
            planned_start_at=_utc(2024, 1, 3, 9, 0),
            started_at=_utc(2024, 1, 3, 20, 0),
        ),
        # Completed but missing started_at -> excluded.
        _task(
            subject="Math",
            planned_start_at=_utc(2024, 1, 4, 9, 0),
            started_at=None,
        ),
    ]
    averages = average_start_delay_by_group(tasks)
    assert averages["Math"] == pytest.approx(2.0)  # mean of 1 and 3 only


def test_average_handles_multiple_groups_independently():
    tasks = [
        _task(
            subject="Math",
            planned_start_at=_utc(2024, 1, 1, 9, 0),
            started_at=_utc(2024, 1, 1, 11, 0),  # 2 hr
        ),
        _task(
            subject="Math",
            planned_start_at=_utc(2024, 1, 2, 9, 0),
            started_at=_utc(2024, 1, 2, 11, 0),  # 2 hr
        ),
        _task(
            subject="English",
            planned_start_at=_utc(2024, 1, 1, 9, 0),
            started_at=_utc(2024, 1, 1, 9, 30),  # 0.5 hr
        ),
        _task(
            subject="English",
            planned_start_at=_utc(2024, 1, 2, 9, 0),
            started_at=_utc(2024, 1, 2, 9, 30),  # 0.5 hr
        ),
    ]
    averages = average_start_delay_by_group(tasks)
    assert averages["Math"] == pytest.approx(2.0)
    assert averages["English"] == pytest.approx(0.5)


# --- format_start_delay --------------------------------------------------


def test_format_on_time_near_zero():
    assert format_start_delay(timedelta(seconds=5)) == "On time"


def test_format_minutes_late():
    assert format_start_delay(timedelta(minutes=25)) == "25 min late"


def test_format_hours_early():
    assert format_start_delay(timedelta(hours=-2, minutes=-30)) == "2.5 hr early"


def test_format_none_is_no_start_data():
    assert format_start_delay(None) == "no start data"

# ==========================================================================
# Property-based tests (Hypothesis) — Task 7.1
# ==========================================================================

from hypothesis import given, strategies as st


# A bounded seconds range keeps the timedeltas realistic while still spanning
# early/on-time/late and both minute- and hour-magnitude regions.
_SECONDS = st.integers(min_value=-10_000_000, max_value=10_000_000)

# Zero tolerance mirrored from the service (< 30s magnitude reads "On time").
_TOLERANCE_SECONDS = 30


# Feature: history-driven-suggestions, Property 6: Delay formatting reflects correct sign and units
@given(st.one_of(st.none(), _SECONDS.map(lambda s: timedelta(seconds=s))))
def test_format_start_delay_sign_units(delay):
    result = format_start_delay(delay)

    if delay is None:
        assert result == "no start data"
        return

    total = delay.total_seconds()
    magnitude = abs(total)

    if magnitude < _TOLERANCE_SECONDS:
        assert result == "On time"
        return

    # Sign: positive => late, negative => early.
    if total > 0:
        assert result.endswith("late")
    else:
        assert result.endswith("early")

    # Unit: "hr" when magnitude >= 60 minutes, otherwise "min".
    if magnitude >= 3600:
        assert " hr " in result
    else:
        assert " min " in result


# Feature: history-driven-suggestions, Property 9: Average start delay uses only qualifying tasks
@given(
    st.lists(
        st.fixed_dictionaries(
            {
                # Mix completed / not-completed tasks.
                "status": st.sampled_from(
                    ["completed", "not_started", "in_progress"]
                ),
                # Whether both timestamps are present (qualifying requires both).
                "has_planned": st.booleans(),
                "has_started": st.booleans(),
                # started = planned + this many minutes (deterministic).
                "delay_minutes": st.integers(min_value=-600, max_value=600),
            }
        ),
        min_size=0,
        max_size=15,
    )
)
def test_average_qualifying_only(specs):
    # Fixed group + fixed planned start keeps the arithmetic deterministic; the
    # only varying inputs are status, timestamp presence, and the delay.
    planned = _utc(2024, 1, 1, 9, 0)

    tasks = []
    expected_hours = []
    for spec in specs:
        planned_start = planned if spec["has_planned"] else None
        started = (
            planned + timedelta(minutes=spec["delay_minutes"])
            if spec["has_started"]
            else None
        )
        task = _task(
            status=spec["status"],
            subject="Math",
            planned_start_at=planned_start,
            started_at=started,
        )
        tasks.append(task)
        # Qualifying == completed AND both timestamps present.
        if (
            spec["status"] == "completed"
            and planned_start is not None
            and started is not None
        ):
            expected_hours.append(spec["delay_minutes"] / 60.0)

    averages = average_start_delay_by_group(tasks)

    if len(expected_hours) < 2:  # MINIMUM_SAMPLE
        # Below the sample threshold: the group must be absent entirely.
        assert "Math" not in averages
        assert averages == {}
    else:
        assert set(averages) == {"Math"}
        assert averages["Math"] == pytest.approx(
            sum(expected_hours) / len(expected_hours)
        )
