"""Versioned public institutions, separate from student-entered course plans."""
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from services.course_service import US_STATES

STATE_NAMES = {**US_STATES, 'DC': 'District of Columbia', 'PR': 'Puerto Rico',
    'AS': 'American Samoa', 'GU': 'Guam', 'MP': 'Northern Mariana Islands',
    'VI': 'U.S. Virgin Islands', 'FM': 'Federated States of Micronesia',
    'MH': 'Marshall Islands', 'PW': 'Palau'}


@lru_cache(maxsize=1)
def directory():
    return json.loads((Path(__file__).resolve().parents[1] / 'data/colleges.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def index():
    return {row['id']: row for row in directory()['institutions']}


def institution(identifier):
    return index().get(str(identifier)) if identifier else None


def states():
    return sorted({row['state'] for row in directory()['institutions']})


def search(query='', state=''):
    words = query.casefold().split()
    return [row for row in directory()['institutions']
            if (not state or row['state'] == state)
            and all(word in f"{row['name']} {row['aliases']} {row['city']}".casefold() for word in words)]


def valid_catalog_url(value):
    try:
        parsed = urlsplit(value)
        return (len(value) <= 500 and parsed.scheme in {'http', 'https'}
                and bool(parsed.hostname) and not parsed.username
                and not any(c.isspace() for c in value))
    except ValueError:
        return False
