"""Explicit, one-way calendar copies. No Google credentials are collected."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode


def utc(value):
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(timezone.utc)


def google_deadline_url(task, timezone_name='America/New_York'):
    start=utc(task.due_at)
    end=start+timedelta(minutes=1)
    return 'https://calendar.google.com/calendar/r/eventedit?' + urlencode({
        'action':'TEMPLATE', 'text':f'{task.title} — due',
        'dates':f"{start:%Y%m%dT%H%M%SZ}/{end:%Y%m%dT%H%M%SZ}",
        'stz':timezone_name, 'etz':timezone_name,
        'details':'StudentSuccess deadline marker (1 minute), not a study session. This is a copy: edits and completion do not sync. Update or remove this event manually.'
    })


def escape(value):
    return str(value).replace('\\','\\\\').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n').replace(';','\\;').replace(',','\\,')


def fold(line):
    """RFC 5545 physical lines are at most 75 octets, including continuation space."""
    result=[]
    current=''
    for character in line:
        if len((current+character).encode('utf-8'))>75:
            result.append(current)
            current=' '
        current+=character
    result.append(current)
    return '\r\n'.join(result)


def calendar_file(tasks):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//StudentSuccess//Task Calendar//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH']
    for task in tasks:
        due=utc(task.due_at)
        lines.extend(['BEGIN:VEVENT',f'UID:task-{task.id}@studentsuccess',
            f'DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}',
            f'DTSTART:{due:%Y%m%dT%H%M%SZ}',f'DTEND:{due+timedelta(minutes=1):%Y%m%dT%H%M%SZ}',
            'TRANSP:TRANSPARENT',f'SUMMARY:{escape(task.title)} due',
            'DESCRIPTION:Deadline marker (1 minute). Changes in StudentSuccess do not sync. Update or remove this calendar copy manually.',
            'END:VEVENT'])
    lines.append('END:VCALENDAR')
    return '\r\n'.join(fold(line) for line in lines)+'\r\n'
