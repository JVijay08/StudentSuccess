"""Example-based unit tests for the pure ``services.recurrence_service``.

These tests use ``types.SimpleNamespace`` stand-ins for session tasks so the
service is exercised in complete isolation (no DB, no Flask app context).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from services.datetime_util import EASTERN
from services import recurrence_service


UTC = timezone.utc


def _eastern_instant(year, month, day, hour, minute=0):
    """Build a real UTC instant from an Eastern wall-clock datetime."""
    local = datetime(year, month, day, hour, minute, tzinfo=EASTERN)
    return local.astimezone(UTC)


def _make_session(**overrides):
    """A SimpleNamespace session-task stand-in with sensible defaults."""
    base = {
        "title": "SAT Math tutoring",
        "subject": "Math",
        "task_type": "Tutoring",
        "estimated_minutes": 60,
        "difficulty": "high",
        "interest_level": "low",
        "recurrence_rule": "weekly",
        "due_at": _eastern_instant(2024, 3, 8, 18),
        "planned_start_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# advance — day-based rules across a DST boundary (spring forward 2024-03-10)
# ---------------------------------------------------------------------------

def test_advance_weekly_preserves_eastern_time_across_dst():
    # 2024-03-08 18:00 Eastern (EST, UTC-5) -> +7 days = 2024-03-15 (EDT, UTC-4)
    start = _eastern_instant(2024, 3, 8, 18)
    result = recurrence_service.advance(start, "weekly")
    local = result.astimezone(EASTERN)
    assert (local.year, local.month, local.day) == (2024, 3, 15)
    assert (local.hour, local.minute) == (18, 0)


def test_advance_daily_preserves_eastern_time_across_dst():
    # 2024-03-09 18:00 Eastern (EST) -> +1 day crosses spring-forward to 03-10 (EDT)
    start = _eastern_instant(2024, 3, 9, 18)
    result = recurrence_service.advance(start, "daily")
    local = result.astimezone(EASTERN)
    assert (local.year, local.month, local.day) == (2024, 3, 10)
    assert (local.hour, local.minute) == (18, 0)


def test_advance_biweekly_preserves_eastern_time_across_dst():
    # 2024-03-08 18:00 Eastern (EST) -> +14 days = 2024-03-22 (EDT)
    start = _eastern_instant(2024, 3, 8, 18)
    result = recurrence_service.advance(start, "biweekly")
    local = result.astimezone(EASTERN)
    assert (local.year, local.month, local.day) == (2024, 3, 22)
    assert (local.hour, local.minute) == (18, 0)


# ---------------------------------------------------------------------------
# advance — monthly clamping and year rollover
# ---------------------------------------------------------------------------

def test_advance_monthly_jan31_to_feb28_non_leap():
    start = _eastern_instant(2023, 1, 31, 9)
    result = recurrence_service.advance(start, "monthly")
    local = result.astimezone(EASTERN)
    assert (local.year, local.month, local.day) == (2023, 2, 28)
    assert (local.hour, local.minute) == (9, 0)


def test_advance_monthly_jan31_to_feb29_leap():
    start = _eastern_instant(2024, 1, 31, 9)
    result = recurrence_service.advance(start, "monthly")
    local = result.astimezone(EASTERN)
    assert (local.year, local.month, local.day) == (2024, 2, 29)
    assert (local.hour, local.minute) == (9, 0)


def test_advance_monthly_december_rolls_over_year():
    start = _eastern_instant(2024, 12, 15, 14)
    result = recurrence_service.advance(start, "monthly")
    local = result.astimezone(EASTERN)
    assert (local.year, local.month, local.day) == (2025, 1, 15)
    assert (local.hour, local.minute) == (14, 0)


# ---------------------------------------------------------------------------
# advance — invalid rules
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_rule", ["yearly", "", "WEEKLY"])
def test_advance_rejects_invalid_rules(bad_rule):
    start = _eastern_instant(2024, 3, 8, 18)
    with pytest.raises(ValueError):
        recurrence_service.advance(start, bad_rule)


# ---------------------------------------------------------------------------
# next_occurrence_fields
# ---------------------------------------------------------------------------

def test_next_occurrence_fields_advances_planned_start_when_present():
    session = _make_session(
        recurrence_rule="weekly",
        due_at=_eastern_instant(2024, 3, 8, 18),
        planned_start_at=_eastern_instant(2024, 3, 8, 16),
    )
    fields = recurrence_service.next_occurrence_fields(session)

    assert fields["due_at"] == recurrence_service.advance(session.due_at, "weekly")
    assert fields["planned_start_at"] == recurrence_service.advance(
        session.planned_start_at, "weekly"
    )
    # planned advanced to the following week, same local time-of-day
    planned_local = fields["planned_start_at"].astimezone(EASTERN)
    assert (planned_local.month, planned_local.day, planned_local.hour) == (3, 15, 16)


def test_next_occurrence_fields_leaves_planned_start_none_when_absent():
    session = _make_session(planned_start_at=None)
    fields = recurrence_service.next_occurrence_fields(session)
    assert fields["planned_start_at"] is None


def test_next_occurrence_fields_resets_lifecycle_and_copies_identity():
    session = _make_session()
    fields = recurrence_service.next_occurrence_fields(session)

    assert fields["status"] == "not_started"
    assert fields["started_at"] is None
    assert fields["completed_at"] is None

    assert fields["recurrence_rule"] == session.recurrence_rule
    assert fields["title"] == session.title
    assert fields["subject"] == session.subject
    assert fields["task_type"] == session.task_type
    assert fields["estimated_minutes"] == session.estimated_minutes
    assert fields["difficulty"] == session.difficulty
    assert fields["interest_level"] == session.interest_level


# ---------------------------------------------------------------------------
# prep_task_fields
# ---------------------------------------------------------------------------

def test_prep_task_fields_due_at_is_lead_time_before_session():
    session = _make_session(due_at=_eastern_instant(2024, 3, 8, 18))
    fields = recurrence_service.prep_task_fields(session)
    assert fields["due_at"] == session.due_at - timedelta(hours=24)


def test_prep_task_fields_title_prefix_and_defaults():
    session = _make_session(title="Algebra review")
    fields = recurrence_service.prep_task_fields(session)

    assert fields["title"].startswith("Prep: ")
    assert fields["title"] == "Prep: Algebra review"
    assert fields["recurrence_rule"] is None
    assert fields["estimated_minutes"] == 30
    assert fields["difficulty"] == "medium"
    assert fields["interest_level"] == "medium"
    assert fields["task_type"] == "Lesson prep"
    assert fields["planned_start_at"] is None
    assert fields["status"] == "not_started"
    assert fields["started_at"] is None
    assert fields["completed_at"] is None


def test_prep_task_fields_title_truncated_to_160_chars():
    long_title = "X" * 200
    session = _make_session(title=long_title)
    fields = recurrence_service.prep_task_fields(session)

    assert len(fields["title"]) <= 160
    assert fields["title"] == f"Prep: {long_title}"[:160]


def test_prep_task_fields_respects_custom_lead_time():
    session = _make_session(due_at=_eastern_instant(2024, 3, 8, 18))
    fields = recurrence_service.prep_task_fields(session, lead_time=timedelta(hours=2))
    assert fields["due_at"] == session.due_at - timedelta(hours=2)

# ===========================================================================
# Regression test — naive datetimes are treated as UTC (SQLite-naive-read fix)
# ===========================================================================

def test_advance_treats_naive_as_utc():
    """A naive datetime must be treated as a real UTC instant, not system-local.

    SQLite can return naive datetimes on read; ``_as_utc`` normalizes them by
    attaching UTC rather than assuming the machine's local zone. This guards
    that regression: the naive and tz-aware-UTC forms of the same instant must
    advance to the identical tz-aware UTC result.
    """
    # datetime(2024, 3, 8, 23, 0) means 2024-03-08 23:00 UTC, but carries no tzinfo.
    naive = datetime(2024, 3, 8, 23, 0)
    aware = datetime(2024, 3, 8, 23, 0, tzinfo=UTC)

    naive_result = recurrence_service.advance(naive, "weekly")
    aware_result = recurrence_service.advance(aware, "weekly")

    # Both produce a tz-aware UTC datetime...
    assert naive_result.tzinfo is not None
    assert naive_result.utcoffset() == timedelta(0)
    assert aware_result.tzinfo is not None
    assert aware_result.utcoffset() == timedelta(0)
    # ...and they represent the SAME instant (naive interpreted as UTC).
    assert naive_result == aware_result


# ===========================================================================
# Property-based tests (Hypothesis, >=100 iterations each)
# ===========================================================================

from calendar import monthrange  # noqa: E402

from hypothesis import given, settings, strategies as st  # noqa: E402

from services.recurrence_service import (  # noqa: E402
    advance,
    next_occurrence_fields,
    prep_task_fields,
    ALLOWED_RULES,
    _as_utc,
    DEFAULT_LEAD_TIME,
)


# A tz-aware UTC datetime spanning many years (and thus many DST weeks). We drop
# microseconds so local time-of-day comparisons stay exact.
_utc_datetimes = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
).map(lambda d: d.replace(tzinfo=timezone.utc, microsecond=0))


_DAY_STEPS = {"daily": 1, "weekly": 7, "biweekly": 14}


# Feature: recurring-sessions, Property 1: Day-based advance preserves Eastern local time-of-day
@settings(max_examples=200)
@given(dt=_utc_datetimes, rule=st.sampled_from(["daily", "weekly", "biweekly"]))
def test_property_day_based_advance_preserves_eastern_local_time(dt, rule):
    result = advance(dt, rule)

    # Result is tz-aware UTC.
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)

    local_in = dt.astimezone(EASTERN)
    local_out = result.astimezone(EASTERN)

    # Local date is exactly 1 / 7 / 14 days after the input's local date.
    expected_date = (local_in + timedelta(days=_DAY_STEPS[rule])).date()
    assert local_out.date() == expected_date

    # Local time-of-day is preserved across DST.
    assert (local_out.hour, local_out.minute) == (local_in.hour, local_in.minute)


# Feature: recurring-sessions, Property 2: Monthly advance preserves or clamps day-of-month
@settings(max_examples=200)
@given(dt=_utc_datetimes)
def test_property_monthly_advance_preserves_or_clamps_day(dt):
    result = advance(dt, "monthly")

    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)

    local_in = dt.astimezone(EASTERN)
    local_out = result.astimezone(EASTERN)

    # Target month is the next calendar month, handling Dec -> Jan rollover.
    if local_in.month == 12:
        expected_year, expected_month = local_in.year + 1, 1
    else:
        expected_year, expected_month = local_in.year, local_in.month + 1

    assert (local_out.year, local_out.month) == (expected_year, expected_month)

    # Day is clamped to the last valid day of the target month.
    last_day = monthrange(expected_year, expected_month)[1]
    expected_day = min(local_in.day, last_day)
    assert local_out.day == expected_day

    # Local time-of-day preserved.
    assert (local_out.hour, local_out.minute) == (local_in.hour, local_in.minute)


# Feature: recurring-sessions, Property 3: Advance rejects invalid rules
@settings(max_examples=200)
@given(rule=st.text().filter(lambda s: s not in ALLOWED_RULES))
def test_property_advance_rejects_invalid_rules(rule):
    fixed_dt = datetime(2024, 3, 8, 18, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        advance(fixed_dt, rule)


def _session_strategy(planned_optional=True):
    """Hypothesis strategy building a SimpleNamespace session-task stand-in."""
    difficulties = st.sampled_from(["low", "medium", "high"])
    interests = st.sampled_from(["low", "medium", "high"])
    planned_strategy = (
        st.one_of(st.none(), _utc_datetimes) if planned_optional else st.none()
    )
    return st.builds(
        SimpleNamespace,
        title=st.text(min_size=0, max_size=160),
        subject=st.text(min_size=0, max_size=80),
        task_type=st.text(min_size=0, max_size=40),
        estimated_minutes=st.integers(min_value=1, max_value=1440),
        difficulty=difficulties,
        interest_level=interests,
        recurrence_rule=st.sampled_from(sorted(ALLOWED_RULES)),
        due_at=_utc_datetimes,
        planned_start_at=planned_strategy,
    )


# Feature: recurring-sessions, Property 4: Next-occurrence fields advance datetimes and reset lifecycle
@settings(max_examples=200)
@given(session=_session_strategy())
def test_property_next_occurrence_fields(session):
    fields = next_occurrence_fields(session)
    rule = session.recurrence_rule

    assert fields["due_at"] == advance(session.due_at, rule)
    if session.planned_start_at is not None:
        assert fields["planned_start_at"] == advance(session.planned_start_at, rule)
    else:
        assert fields["planned_start_at"] is None

    # Lifecycle reset.
    assert fields["status"] == "not_started"
    assert fields["started_at"] is None
    assert fields["completed_at"] is None

    # recurrence_rule copied forward and identity attrs copied unchanged.
    assert fields["recurrence_rule"] == rule
    assert fields["title"] == session.title
    assert fields["subject"] == session.subject
    assert fields["task_type"] == session.task_type
    assert fields["estimated_minutes"] == session.estimated_minutes
    assert fields["difficulty"] == session.difficulty
    assert fields["interest_level"] == session.interest_level


# Feature: recurring-sessions, Property 5: Prep-task fields are correct, valid, and non-recurring
@settings(max_examples=200)
@given(
    session=_session_strategy(),
    lead_minutes=st.integers(min_value=0, max_value=7 * 24 * 60),
)
def test_property_prep_task_fields(session, lead_minutes):
    lead_time = timedelta(minutes=lead_minutes)
    fields = prep_task_fields(session, lead_time=lead_time)

    # due_at is lead_time before the (UTC-normalized) session due_at.
    assert fields["due_at"] == _as_utc(session.due_at) - lead_time

    # Title is the "Prep: " prefix, truncated to <=160.
    expected_title = ("Prep: " + session.title)[:160]
    assert fields["title"] == expected_title
    assert len(fields["title"]) <= 160

    # Non-recurring and valid defaults satisfying Task validation.
    assert fields["recurrence_rule"] is None
    assert 1 <= fields["estimated_minutes"] <= 1440
    assert fields["estimated_minutes"] == 30
    assert fields["difficulty"] == "medium"
    assert fields["interest_level"] == "medium"
    assert fields["task_type"] == "Lesson prep"
