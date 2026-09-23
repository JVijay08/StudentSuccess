"""Bounded iCalendar VEVENT import. Recurrence is previewed as one occurrence."""
import hashlib
import re
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def parse_calendar(raw, timezone_name):
    if len(raw) > 1024 * 1024:
        raise ValueError("Calendar must be at most 1 MB.")
    text = raw.decode("utf-8-sig")
    if "BEGIN:VCALENDAR" not in text or "END:VCALENDAR" not in text:
        raise ValueError("Choose a valid .ics calendar file.")
    lines = re.sub(r"\r?\n[ \t]", "", text).splitlines()
    events, fields = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            fields = {}
        elif line == "END:VEVENT" and fields is not None:
            if "SUMMARY" in fields and ("DUE" in fields or "DTSTART" in fields):
                prop, value = fields.get("DUE", fields.get("DTSTART"))
                tzid = next((p.split("=", 1)[1].strip('"') for p in prop.split(";")[1:] if p.startswith("TZID=")), timezone_name)
                try:
                    zone = ZoneInfo(tzid)
                    if len(value) == 8:
                        due = datetime.combine(datetime.strptime(value, "%Y%m%d").date(), time(23, 59), zone)
                    else:
                        due = datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc if value.endswith("Z") else zone)
                except (ValueError, ZoneInfoNotFoundError):
                    raise ValueError("A calendar event has an unsupported date or timezone.") from None
                title = re.sub(r"\\([nN,;\\])", lambda m: " " if m[1] in "nN" else m[1], fields["SUMMARY"][1]).strip()[:160]
                if title:
                    uid = fields.get("UID", ("", title + due.isoformat()))[1]
                    occurrence = fields.get("RECURRENCE-ID", ("", ""))[1]
                    events.append(dict(title=title, due_at=due.astimezone(timezone.utc).isoformat(),
                                       uid=hashlib.sha256((uid + "|" + occurrence).encode()).hexdigest(),
                                       recurring="RRULE" in fields))
            fields = None
        elif fields is not None and ":" in line:
            prop, value = line.split(":", 1)
            fields[prop.split(";", 1)[0]] = (prop, value)
        if len(events) > 200:
            raise ValueError("Import at most 200 events at a time.")
    if not events:
        raise ValueError("No events with a title and start/due date were found.")
    return events
