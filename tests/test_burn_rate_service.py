"""Example-based unit tests for the pure burn_rate_service.

These tests use lightweight SimpleNamespace stand-ins for Task, so the service
is exercised without a Flask app context or database.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services import burn_rate_service


def _task(
    *,
    status="completed",
    started_at=None,
    completed_at=None,
    estimated_minutes=60,
    subject=None,
    task_type=None,
):
    return SimpleNamespace(
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        estimated_minutes=estimated_minutes,
        subject=subject,
        task_type=task_type,
    )


def _utc(hour, minute=0):
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


# --- is_measurable -------------------------------------------------------

def test_is_measurable_true_for_completed_with_both_timestamps():
    task = _task(status="completed", started_at=_utc(10), completed_at=_utc(11))
    assert burn_rate_service.is_measurable(task) is True


def test_is_measurable_false_when_not_completed():
    task = _task(status="in_progress", started_at=_utc(10), completed_at=_utc(11))
    assert burn_rate_service.is_measurable(task) is False


def test_is_measurable_false_when_started_at_missing():
    task = _task(status="completed", started_at=None, completed_at=_utc(11))
    assert burn_rate_service.is_measurable(task) is False


def test_is_measurable_false_when_completed_at_missing():
    task = _task(status="completed", started_at=_utc(10), completed_at=None)
    assert burn_rate_service.is_measurable(task) is False


# --- actual_duration_minutes ---------------------------------------------

def test_actual_duration_known_interval():
    task = _task(started_at=_utc(10), completed_at=_utc(11))
    assert burn_rate_service.actual_duration_minutes(task) == 60.0


def test_actual_duration_naive_timestamps_treated_as_utc():
    aware = _task(started_at=_utc(10), completed_at=_utc(11))
    naive = _task(
        started_at=datetime(2024, 1, 1, 10, 0),
        completed_at=datetime(2024, 1, 1, 11, 0),
    )
    assert burn_rate_service.actual_duration_minutes(naive) == (
        burn_rate_service.actual_duration_minutes(aware)
    )
    assert burn_rate_service.actual_duration_minutes(naive) == 60.0


def test_actual_duration_negative_when_completed_before_started():
    task = _task(started_at=_utc(11), completed_at=_utc(10))
    result = burn_rate_service.actual_duration_minutes(task)
    assert result == -60.0  # signed, no error raised


# --- task_burn_rate ------------------------------------------------------

def test_task_burn_rate_actual_over_estimated():
    task = _task(started_at=_utc(10), completed_at=_utc(12), estimated_minutes=60)
    assert burn_rate_service.task_burn_rate(task) == 2.0  # 120 / 60


def test_task_burn_rate_is_unrounded():
    task = _task(started_at=_utc(10), completed_at=_utc(11, 30), estimated_minutes=60)
    assert burn_rate_service.task_burn_rate(task) == 1.5  # 90 / 60


# --- interpret -----------------------------------------------------------

def test_interpret_accurate_at_one():
    assert burn_rate_service.interpret(1.00) == "estimates are accurate"


def test_interpret_accurate_at_lower_boundary():
    assert burn_rate_service.interpret(0.95) == "estimates are accurate"


def test_interpret_accurate_at_upper_boundary():
    assert burn_rate_service.interpret(1.05) == "estimates are accurate"


def test_interpret_over_estimate():
    assert burn_rate_service.interpret(1.24) == "runs ~24% over"


def test_interpret_early():
    assert burn_rate_service.interpret(0.80) == "finishes ~20% early"


# --- group_burn_rates ----------------------------------------------------

def test_group_burn_rates_omits_group_with_single_eligible_task():
    tasks = [
        _task(started_at=_utc(10), completed_at=_utc(11), subject="Solo"),
    ]
    assert burn_rate_service.group_burn_rates(tasks) == []


def test_group_burn_rates_includes_group_with_two_eligible_tasks():
    # Chemistry: rates 2.0 (120/60) and 1.0 (60/60) -> mean 1.5
    tasks = [
        _task(started_at=_utc(10), completed_at=_utc(12), estimated_minutes=60, subject="Chemistry"),
        _task(started_at=_utc(10), completed_at=_utc(11), estimated_minutes=60, subject="Chemistry"),
    ]
    rows = burn_rate_service.group_burn_rates(tasks)
    assert len(rows) == 1
    row = rows[0]
    assert row["group"] == "Chemistry"
    assert row["rate"] == 1.5
    assert row["label"] == burn_rate_service.interpret(1.5)


def test_group_burn_rates_sorted_rate_descending():
    tasks = [
        # Reading: rates 1.0 and 0.8 -> mean 0.9 (early)
        _task(started_at=_utc(10), completed_at=_utc(11), estimated_minutes=60, subject="Reading"),
        _task(started_at=_utc(10), completed_at=_utc(10, 48), estimated_minutes=60, subject="Reading"),
        # Chemistry: rates 2.0 and 1.0 -> mean 1.5 (over)
        _task(started_at=_utc(10), completed_at=_utc(12), estimated_minutes=60, subject="Chemistry"),
        _task(started_at=_utc(10), completed_at=_utc(11), estimated_minutes=60, subject="Chemistry"),
    ]
    rows = burn_rate_service.group_burn_rates(tasks)
    assert [row["group"] for row in rows] == ["Chemistry", "Reading"]
    assert rows[0]["rate"] >= rows[1]["rate"]


def test_group_burn_rates_excludes_negative_duration_member():
    # Chemistry has 2 members, but one has completed_at < started_at (anomaly).
    # Only 1 eligible remains, so the group is omitted.
    tasks = [
        _task(started_at=_utc(10), completed_at=_utc(11), estimated_minutes=60, subject="Chemistry"),
        _task(started_at=_utc(11), completed_at=_utc(10), estimated_minutes=60, subject="Chemistry"),
    ]
    assert burn_rate_service.group_burn_rates(tasks) == []


def test_group_burn_rates_label_from_unrounded_mean():
    # rates 1.24 and 1.24 -> mean 1.24 -> "runs ~24% over"
    # 74.4 min / 60 = 1.24
    tasks = [
        _task(started_at=_utc(10), completed_at=_utc(10) + timedelta(minutes=74.4), estimated_minutes=60, subject="Chemistry"),
        _task(started_at=_utc(10), completed_at=_utc(10) + timedelta(minutes=74.4), estimated_minutes=60, subject="Chemistry"),
    ]
    rows = burn_rate_service.group_burn_rates(tasks)
    assert rows[0]["label"] == "runs ~24% over"


# --- overall_burn_rate ---------------------------------------------------

def test_overall_burn_rate_none_when_fewer_than_two_eligible():
    tasks = [
        _task(started_at=_utc(10), completed_at=_utc(11), estimated_minutes=60, subject="Chemistry"),
    ]
    assert burn_rate_service.overall_burn_rate(tasks) is None


def test_overall_burn_rate_spans_multiple_groups():
    # Chemistry 2.0, Reading 1.0 -> overall mean 1.5
    tasks = [
        _task(started_at=_utc(10), completed_at=_utc(12), estimated_minutes=60, subject="Chemistry"),
        _task(started_at=_utc(10), completed_at=_utc(11), estimated_minutes=60, subject="Reading"),
    ]
    result = burn_rate_service.overall_burn_rate(tasks)
    assert result is not None
    assert result["rate"] == 1.5
    assert result["label"] == burn_rate_service.interpret(1.5)


def test_overall_burn_rate_excludes_non_positive_duration_tasks():
    # Two anomalies + one valid task -> only 1 eligible -> None
    tasks = [
        _task(started_at=_utc(11), completed_at=_utc(10), estimated_minutes=60, subject="Chemistry"),
        _task(started_at=_utc(10), completed_at=_utc(10), estimated_minutes=60, subject="Reading"),
        _task(started_at=_utc(10), completed_at=_utc(11), estimated_minutes=60, subject="History"),
    ]
    assert burn_rate_service.overall_burn_rate(tasks) is None

# =========================================================================
# Property-based tests (Hypothesis, >= 100 examples each)
#
# Tasks are represented by SimpleNamespace stand-ins exposing the fields the
# service reads (status, started_at, completed_at, estimated_minutes, subject,
# task_type), so the service is exercised without a Flask app context or DB.
# Expected values are derived using the service's own helpers where that keeps
# equality exact (e.g. labels via burn_rate_service.interpret).
# =========================================================================

from hypothesis import given, settings
from hypothesis import strategies as st


# A base UTC-aware instant used to build timestamps from minute offsets.
_BASE_UTC = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)


def _expected_as_utc(value):
    """Replicate the service's _as_utc normalization for expected values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Aware-UTC datetimes spanning a wide but finite range (whole seconds).
_aware_datetimes = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2050, 1, 1),
    timezones=st.just(timezone.utc),
)


# --- 6.1 Primitive property tests ----------------------------------------

# Feature: estimate-accuracy, Property 1: Measurable-Task predicate correctness
@settings(max_examples=200)
@given(
    status=st.sampled_from(["not_started", "in_progress", "completed"]),
    started_at=st.none() | _aware_datetimes,
    completed_at=st.none() | _aware_datetimes,
)
def test_is_measurable_iff(status, started_at, completed_at):
    task = _task(status=status, started_at=started_at, completed_at=completed_at)
    expected = (
        status == "completed"
        and started_at is not None
        and completed_at is not None
    )
    assert burn_rate_service.is_measurable(task) is expected


# Feature: estimate-accuracy, Property 2: Actual_Duration is UTC-normalized signed minutes
@settings(max_examples=200)
@given(
    started=_aware_datetimes,
    completed=_aware_datetimes,
    strip_started=st.booleans(),
    strip_completed=st.booleans(),
)
def test_actual_duration_signed_minutes(started, completed, strip_started, strip_completed):
    started_at = started.replace(tzinfo=None) if strip_started else started
    completed_at = completed.replace(tzinfo=None) if strip_completed else completed
    task = _task(started_at=started_at, completed_at=completed_at)

    # No exception even when completed precedes started (signed result).
    result = burn_rate_service.actual_duration_minutes(task)

    expected = (
        _expected_as_utc(completed_at) - _expected_as_utc(started_at)
    ).total_seconds() / 60.0
    assert result == expected


# Feature: estimate-accuracy, Property 3: Per-task Burn_Rate equals actual over estimated
@settings(max_examples=200)
@given(
    started=_aware_datetimes,
    completed=_aware_datetimes,
    estimated_minutes=st.integers(min_value=1, max_value=1440),
)
def test_task_burn_rate_ratio(started, completed, estimated_minutes):
    task = _task(
        started_at=started,
        completed_at=completed,
        estimated_minutes=estimated_minutes,
    )
    # Exact float equality: same computation performed both sides.
    expected = burn_rate_service.actual_duration_minutes(task) / estimated_minutes
    assert burn_rate_service.task_burn_rate(task) == expected


# Feature: estimate-accuracy, Property 4: interpret band and percentage phrasing
@settings(max_examples=300)
@given(rate=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))
def test_interpret_band_and_labels(rate):
    label = burn_rate_service.interpret(rate)
    if 0.95 <= rate <= 1.05:
        assert label == "estimates are accurate"
    elif rate > 1.05:
        assert label == f"runs ~{round((rate - 1) * 100)}% over"
    else:
        assert label == f"finishes ~{round((1 - rate) * 100)}% early"
    # The label never exposes the raw ratio value as a number.
    assert str(rate) not in label


# --- 6.2 Aggregation and purity property tests ---------------------------

# Descriptor for building a task: a group label, an estimate, actual-minute
# offset (can be negative/zero/positive), and a status that is mostly completed.
_group_labels = st.sampled_from(["Chemistry", "Reading", "Math", None, "", "essay"])
_task_descriptors = st.lists(
    st.fixed_dictionaries(
        {
            "group": _group_labels,
            "estimated_minutes": st.integers(min_value=1, max_value=1440),
            "actual_minutes": st.floats(
                min_value=-500.0, max_value=500.0, allow_nan=False, allow_infinity=False
            ),
            "status": st.sampled_from(
                ["completed", "completed", "completed", "in_progress", "not_started"]
            ),
            "drop_started": st.booleans(),
            "drop_completed": st.booleans(),
        }
    ),
    max_size=25,
)


def _build_task(descriptor):
    """Build a SimpleNamespace task from a descriptor.

    The group label is placed on ``subject`` (group_key precedence uses subject
    first; None/"" falls through to task_type, here None, then "ungrouped").
    started_at is fixed; completed_at is offset by actual_minutes. A descriptor
    may drop either timestamp to exercise non-measurable cases.
    """
    started_at = None if descriptor["drop_started"] else _BASE_UTC
    if descriptor["drop_completed"]:
        completed_at = None
    else:
        completed_at = _BASE_UTC + timedelta(minutes=descriptor["actual_minutes"])
    return _task(
        status=descriptor["status"],
        started_at=started_at,
        completed_at=completed_at,
        estimated_minutes=descriptor["estimated_minutes"],
        subject=descriptor["group"],
    )


def _eligible_rate_by_group(tasks):
    """Expected {group_key: [rates]} over eligible tasks, using the service."""
    rates_by_group = {}
    for task in tasks:
        if not burn_rate_service.is_measurable(task):
            continue
        if not burn_rate_service.actual_duration_minutes(task) > 0:
            continue
        key = burn_rate_service.group_key(task)
        rates_by_group.setdefault(key, []).append(burn_rate_service.task_burn_rate(task))
    return rates_by_group


# Feature: estimate-accuracy, Property 5: Group_Burn_Rate aggregation, Minimum_Sample gating, ordering, and anomaly exclusion
@settings(max_examples=150)
@given(descriptors=_task_descriptors)
def test_group_burn_rates_aggregation(descriptors):
    tasks = [_build_task(d) for d in descriptors]
    rows = burn_rate_service.group_burn_rates(tasks)

    rates_by_group = _eligible_rate_by_group(tasks)
    expected_groups = {
        key: rates
        for key, rates in rates_by_group.items()
        if len(rates) >= burn_rate_service.MINIMUM_SAMPLE
    }

    # Only groups meeting Minimum_Sample appear; no group below sample appears.
    assert {row["group"] for row in rows} == set(expected_groups)

    for row in rows:
        rates = expected_groups[row["group"]]
        expected_mean = sum(rates) / len(rates)
        assert row["rate"] == round(expected_mean, 2)
        assert row["label"] == burn_rate_service.interpret(expected_mean)

    # Rows sorted by rate in non-increasing (descending) order.
    row_rates = [row["rate"] for row in rows]
    assert row_rates == sorted(row_rates, reverse=True)

    # Anomaly (actual_duration <= 0) members never contribute: every eligible
    # rate used came from a strictly-positive-duration task (verified by build).


# Feature: estimate-accuracy, Property 6: Overall_Burn_Rate over all eligible measurable tasks
@settings(max_examples=150)
@given(descriptors=_task_descriptors)
def test_overall_burn_rate_mean_or_none(descriptors):
    tasks = [_build_task(d) for d in descriptors]
    result = burn_rate_service.overall_burn_rate(tasks)

    eligible_rates = []
    for rates in _eligible_rate_by_group(tasks).values():
        eligible_rates.extend(rates)

    if len(eligible_rates) < burn_rate_service.MINIMUM_SAMPLE:
        assert result is None
    else:
        expected_mean = sum(eligible_rates) / len(eligible_rates)
        assert result == {
            "rate": round(expected_mean, 2),
            "label": burn_rate_service.interpret(expected_mean),
        }


# Feature: estimate-accuracy, Property 7: Purity - no DB writes, inputs unchanged, no persistence
@settings(max_examples=150)
@given(descriptors=_task_descriptors)
def test_burn_rate_service_pure(descriptors):
    tasks = [_build_task(d) for d in descriptors]

    # Snapshot every attribute the service reads.
    snapshots = [
        (
            task.status,
            task.started_at,
            task.completed_at,
            task.estimated_minutes,
            task.subject,
            task.task_type,
        )
        for task in tasks
    ]

    for task in tasks:
        burn_rate_service.is_measurable(task)
        if task.started_at is not None and task.completed_at is not None:
            burn_rate_service.actual_duration_minutes(task)
            if task.estimated_minutes and task.estimated_minutes > 0:
                burn_rate_service.task_burn_rate(task)
    burn_rate_service.group_burn_rates(tasks)
    burn_rate_service.overall_burn_rate(tasks)

    # No input task field was mutated by any call.
    for task, snapshot in zip(tasks, snapshots):
        assert (
            task.status,
            task.started_at,
            task.completed_at,
            task.estimated_minutes,
            task.subject,
            task.task_type,
        ) == snapshot
