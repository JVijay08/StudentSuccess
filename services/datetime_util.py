"""Datetime helpers for converting user-entered Eastern local times to UTC.

Kept pure and side-effect free so routes stay thin and the logic is testable.
Uses only the Python 3.9+ standard library (``zoneinfo``); no new packages.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")


def to_utc(datetime_local_str: str, timezone_name: str = "America/New_York") -> datetime:
    """Convert an Eastern-local ISO datetime string to a UTC-aware datetime.

    The value is parsed with :func:`datetime.fromisoformat`. Naive inputs are
    interpreted as Eastern time via ``replace(tzinfo=EASTERN)``, which lets
    ``zoneinfo`` resolve the correct DST offset (and fold) automatically. Inputs
    that already carry timezone information are preserved as real instants.

    Args:
        datetime_local_str: An ISO 8601 datetime string (e.g. ``"2027-01-15T18:00"``).

    Returns:
        A timezone-aware ``datetime`` in UTC.

    Raises:
        ValueError: If the string cannot be parsed as an ISO datetime.
    """
    parsed = datetime.fromisoformat(datetime_local_str)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed.astimezone(timezone.utc)


def format_local(
    value,
    timezone_name="America/New_York",
    time_format="12-hour",
    date_format="month-first",
    relative_dates=False,
    include_time=True,
):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    zone = ZoneInfo(timezone_name)
    local_value = value.astimezone(zone)
    if relative_dates:
        today = datetime.now(timezone.utc).astimezone(zone).date()
        relative = {0: "Today", 1: "Tomorrow", -1: "Yesterday"}.get(
            (local_value.date() - today).days
        )
        if relative:
            if not include_time:
                return relative
            clock = local_value.strftime(
                "%H:%M" if time_format == "24-hour" else "%I:%M %p"
            )
            return f"{relative}, {clock}"
    date_pattern = {
        "month-first": "%b %d, %Y",
        "day-first": "%d %b %Y",
        "year-first": "%Y-%m-%d",
    }.get(date_format, "%b %d, %Y")
    if include_time:
        date_pattern += ", %H:%M" if time_format == "24-hour" else ", %I:%M %p"
    return local_value.strftime(date_pattern)
