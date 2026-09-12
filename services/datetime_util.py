"""Datetime helpers for converting user-entered Eastern local times to UTC.

Kept pure and side-effect free so routes stay thin and the logic is testable.
Uses only the Python 3.9+ standard library (``zoneinfo``); no new packages.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")


def to_utc(datetime_local_str: str) -> datetime:
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
        parsed = parsed.replace(tzinfo=EASTERN)
    return parsed.astimezone(timezone.utc)
