"""Small, timezone-aware schedule changes; deadlines are never moved implicitly."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from services.datetime_util import to_utc


def planned_time(form, timezone_name, now=None):
    now = now or datetime.now(timezone.utc)
    choice = form.get('schedule_choice', 'custom')
    if choice == 'clear':
        return None
    if choice == 'hour':
        return now + timedelta(hours=1)
    if choice in {'tomorrow', 'next_week'}:
        local = now.astimezone(ZoneInfo(timezone_name))
        date = local.date() + timedelta(days=1 if choice == 'tomorrow' else 7)
        return to_utc(f'{date.isoformat()}T09:00', timezone_name)
    if choice != 'custom':
        raise ValueError('Choose a valid schedule option.')
    raw = form.get('planned_start_at', '').strip()
    if not raw:
        raise ValueError('Enter a new planned start date and time to reschedule.')
    try:
        result = to_utc(raw, timezone_name)
        # Reject nonexistent local clock times during a daylight-saving jump.
        entered = datetime.fromisoformat(raw)
        if entered.tzinfo is None and result.astimezone(ZoneInfo(timezone_name)).replace(tzinfo=None) != entered:
            raise ValueError
    except ValueError:
        raise ValueError('Enter a valid planned start date and time.') from None
    if result <= now:
        raise ValueError('Pick a planned start in the future.')
    return result
