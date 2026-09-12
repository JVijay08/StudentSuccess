"""Example-based unit tests for services/nudge_service.py.

These tests use lightweight SimpleNamespace stand-ins for Task objects so the
pure nudge service can be exercised without a Flask app or database.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services.nudge_service import format_overdue_amount, overdue_to_start


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _task(
    planned_start_at=None,
    started_at=None,
    status="not_started",
    due_at=None,
):
    if due_at is None:
        due_at = _utc(2024, 1, 10, 12, 0)
    return SimpleNamespace(
        planned_start_at=planned_start_at,
        started_at=started_at,
        status=status,
        due_at=due_at,
    )


# A single fixed reference instant used across include/exclude tests.
NOW = _utc(2024, 1, 5, 12, 0)


# --- overdue_to_start: include / exclude ---------------------------------


def test_includes_past_unstarted_not_completed_task():
    task = _task(
        planned_start_at=_utc(2024, 1, 5, 9, 0),
        started_at=None,
        status="not_started",
    )
    rows = overdue_to_start([task], now=NOW)
    assert [row["task"] for row in rows] == [task]


def test_includes_in_progress_task_since_not_completed():
    # status != "completed" is the rule, so in_progress (with no started_at
    # recorded) still counts as overdue-to-start.
    task = _task(
        planned_start_at=_utc(2024, 1, 5, 9, 0),
        started_at=None,
        status="in_progress",
    )
    rows = overdue_to_start([task], now=NOW)
    assert [row["task"] for row in rows] == [task]


def test_excludes_task_with_null_planned_start():
    task = _task(planned_start_at=None, started_at=None, status="not_started")
    assert overdue_to_start([task], now=NOW) == []


def test_excludes_task_with_non_null_started_at():
    task = _task(
        planned_start_at=_utc(2024, 1, 5, 9, 0),
        started_at=_utc(2024, 1, 5, 10, 0),
        status="in_progress",
    )
    assert overdue_to_start([task], now=NOW) == []


def test_excludes_completed_task():
    task = _task(
        planned_start_at=_utc(2024, 1, 5, 9, 0),
        started_at=None,
        status="completed",
    )
    assert overdue_to_start([task], now=NOW) == []


def test_excludes_task_whose_planned_start_equals_now():
    # Strict boundary: planned_start_at == now must be excluded.
    task = _task(planned_start_at=NOW, started_at=None, status="not_started")
    assert overdue_to_start([task], now=NOW) == []


def test_includes_task_planned_one_second_before_now():
    task = _task(
        planned_start_at=NOW - timedelta(seconds=1),
        started_at=None,
        status="not_started",
    )
    rows = overdue_to_start([task], now=NOW)
    assert [row["task"] for row in rows] == [task]


# --- overdue_amount ------------------------------------------------------


def test_overdue_amount_equals_now_minus_planned_start():
    task = _task(planned_start_at=_utc(2024, 1, 5, 9, 30), status="not_started")
    rows = overdue_to_start([task], now=NOW)
    assert rows[0]["overdue_amount"] == timedelta(hours=2, minutes=30)


def test_overdue_amount_handles_naive_planned_start_as_utc():
    # Naive datetime (as SQLite may return) is treated as UTC.
    naive_planned = datetime(2024, 1, 5, 9, 0)  # no tzinfo
    task = _task(planned_start_at=naive_planned, status="not_started")
    rows = overdue_to_start([task], now=NOW)
    assert rows[0]["overdue_amount"] == timedelta(hours=3)


# --- ordering ------------------------------------------------------------


def test_orders_most_overdue_first():
    least = _task(planned_start_at=_utc(2024, 1, 5, 11, 0))  # 1 hr overdue
    most = _task(planned_start_at=_utc(2024, 1, 5, 6, 0))  # 6 hr overdue
    middle = _task(planned_start_at=_utc(2024, 1, 5, 9, 0))  # 3 hr overdue

    rows = overdue_to_start([least, most, middle], now=NOW)
    assert [row["task"] for row in rows] == [most, middle, least]


def test_equal_overdue_amount_breaks_tie_by_earlier_due_at():
    planned = _utc(2024, 1, 5, 9, 0)  # both 3 hr overdue
    earlier_due = _task(planned_start_at=planned, due_at=_utc(2024, 1, 8, 12, 0))
    later_due = _task(planned_start_at=planned, due_at=_utc(2024, 1, 20, 12, 0))

    # Provide later_due first to prove ordering is by due_at, not input order.
    rows = overdue_to_start([later_due, earlier_due], now=NOW)
    assert [row["task"] for row in rows] == [earlier_due, later_due]


# --- format_overdue_amount ----------------------------------------------


def test_format_hours_uses_one_decimal():
    assert format_overdue_amount(timedelta(hours=3)) == "planned 3.0 hr ago"


def test_format_minutes_rounds_to_whole():
    assert format_overdue_amount(timedelta(minutes=25)) == "planned 25 min ago"


def test_format_boundary_exactly_60_minutes_uses_hours():
    assert format_overdue_amount(timedelta(minutes=60)) == "planned 1.0 hr ago"


def test_format_boundary_59_minutes_uses_minutes():
    assert format_overdue_amount(timedelta(minutes=59)) == "planned 59 min ago"


# =========================================================================
# Property-based tests (Hypothesis) — Task 6.1
# Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9,
#            1.10, 2.4, 5.6
# =========================================================================

from hypothesis import given, settings
from hypothesis import strategies as st

from services.nudge_service import _as_utc

# Fixed reference instant reused across the property tests for determinism.
PROP_NOW = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)

# Statuses the model uses; "completed" must be excluded by the predicate.
_STATUSES = ("not_started", "in_progress", "completed")


def _offset_datetime(offset_seconds):
    """A UTC datetime PROP_NOW + offset (None passes through)."""
    if offset_seconds is None:
        return None
    return PROP_NOW + timedelta(seconds=offset_seconds)


# Strategy: a single task with planned_start_at that may be None or an offset
# (negative/zero/positive) relative to PROP_NOW, started_at None or a datetime,
# and a sampled status.
_planned_offsets = st.one_of(
    st.none(),
    st.integers(min_value=-100000, max_value=100000),
)
_started_offsets = st.one_of(
    st.none(),
    st.integers(min_value=-100000, max_value=100000),
)


@settings(max_examples=200)
@given(
    planned_offset=_planned_offsets,
    started_offset=_started_offsets,
    status=st.sampled_from(_STATUSES),
    due_offset=st.integers(min_value=-200000, max_value=200000),
)
def test_overdue_predicate_iff(planned_offset, started_offset, status, due_offset):
    # Feature: overdue-start-nudge, Property 1: Overdue predicate correctness
    planned = _offset_datetime(planned_offset)
    started = _offset_datetime(started_offset)
    task = _task(
        planned_start_at=planned,
        started_at=started,
        status=status,
        due_at=PROP_NOW + timedelta(seconds=due_offset),
    )

    rows = overdue_to_start([task], now=PROP_NOW)
    is_included = task in [row["task"] for row in rows]

    expected = (
        planned is not None
        and _as_utc(planned) < PROP_NOW  # STRICT: offset 0 excluded
        and started is None
        and status != "completed"
    )
    assert is_included == expected


@settings(max_examples=200)
@given(
    # planned strictly in the past guarantees the task IS overdue when it is
    # unstarted and not completed.
    planned_offset=st.integers(min_value=-100000, max_value=-1),
    status=st.sampled_from(("not_started", "in_progress")),
    due_offset=st.integers(min_value=-200000, max_value=200000),
)
def test_overdue_amount_positive(planned_offset, status, due_offset):
    # Feature: overdue-start-nudge, Property 2: Overdue_Amount correctness
    planned = _offset_datetime(planned_offset)
    task = _task(
        planned_start_at=planned,
        started_at=None,
        status=status,
        due_at=PROP_NOW + timedelta(seconds=due_offset),
    )

    rows = overdue_to_start([task], now=PROP_NOW)
    assert len(rows) == 1
    row = rows[0]
    assert row["overdue_amount"] == PROP_NOW - _as_utc(planned)
    assert row["overdue_amount"] > timedelta(0)


# A single task descriptor for building lists in the ordering / purity tests.
_task_descriptor = st.fixed_dictionaries(
    {
        "planned_offset": _planned_offsets,
        "started_offset": _started_offsets,
        "status": st.sampled_from(_STATUSES),
        "due_offset": st.integers(min_value=-200000, max_value=200000),
    }
)


def _build_task(descriptor):
    return _task(
        planned_start_at=_offset_datetime(descriptor["planned_offset"]),
        started_at=_offset_datetime(descriptor["started_offset"]),
        status=descriptor["status"],
        due_at=PROP_NOW + timedelta(seconds=descriptor["due_offset"]),
    )


@settings(max_examples=200)
@given(descriptors=st.lists(_task_descriptor, min_size=0, max_size=12))
def test_overdue_sort_invariant(descriptors):
    # Feature: overdue-start-nudge, Property 3: Ordering invariant
    tasks = [_build_task(d) for d in descriptors]
    rows = overdue_to_start(tasks, now=PROP_NOW)

    for earlier, later in zip(rows, rows[1:]):
        # overdue_amount is non-increasing.
        assert earlier["overdue_amount"] >= later["overdue_amount"]
        # equal overdue_amount -> earlier due_at first.
        if earlier["overdue_amount"] == later["overdue_amount"]:
            assert _as_utc(earlier["task"].due_at) <= _as_utc(later["task"].due_at)


@settings(max_examples=200)
@given(descriptors=st.lists(_task_descriptor, min_size=0, max_size=12))
def test_overdue_service_pure(descriptors):
    # Feature: overdue-start-nudge, Property 4: Detection is a pure read
    tasks = [_build_task(d) for d in descriptors]

    # Snapshot every attribute the service reads before the call.
    snapshots = [
        (
            t,
            t.planned_start_at,
            t.started_at,
            t.status,
            t.due_at,
        )
        for t in tasks
    ]

    rows = overdue_to_start(tasks, now=PROP_NOW)

    # No input attribute changed.
    for task, planned, started, status, due in snapshots:
        assert task.planned_start_at == planned
        assert task.started_at == started
        assert task.status == status
        assert task.due_at == due

    # The returned rows reference the SAME task objects, not copies.
    returned_ids = {id(row["task"]) for row in rows}
    input_ids = {id(t) for t in tasks}
    assert returned_ids <= input_ids


@settings(max_examples=200)
@given(seconds=st.integers(min_value=0, max_value=10_000_000))
def test_format_overdue_amount_units(seconds):
    # Feature: overdue-start-nudge, Property 5: format_overdue_amount units and phrasing
    result = format_overdue_amount(timedelta(seconds=seconds))

    assert result.startswith("planned ")

    if seconds >= 3600:
        assert result.endswith(" hr ago")
        expected_number = round(seconds / 3600.0, 1)
        assert result == f"planned {expected_number} hr ago"
    else:
        assert result.endswith(" min ago")
        expected_number = round(seconds / 60.0)
        assert result == f"planned {expected_number} min ago"
