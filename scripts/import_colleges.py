"""Build a minimal public institution directory from an official IPEDS HD ZIP.

Usage: python scripts/import_colleges.py HD2024.zip --year 2024
No student data, officials' names, phone numbers or street addresses are imported.
"""
import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
from urllib.parse import urlsplit


def build(path, year):
    raw = Path(path).read_bytes()
    with ZipFile(io.BytesIO(raw)) as archive:
        with archive.open(f"HD{year}.csv") as source:
            rows = list(csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig")))
    institutions = []
    for row in rows:
        if row['CYACTIVE'] != '1':
            continue
        website = row['WEBADDR'].strip()
        if website and not website.startswith(('https://', 'http://')):
            website = 'https://' + website
        parsed = urlsplit(website)
        if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username:
            website = ''
        institutions.append(dict(id=row['UNITID'], name=row['INSTNM'].strip(),
            aliases=row['IALIAS'].strip(), state=row['STABBR'], city=row['CITY'].strip(),
            website=website, sector=row['SECTOR'], degree_granting=row['DEGGRANT'] == '1'))
    institutions.sort(key=lambda item: (item['name'].casefold(), item['id']))
    assert len(institutions) > 4000 and len({r['id'] for r in institutions}) == len(institutions)
    assert len({r['state'] for r in institutions}) >= 51
    return dict(source='NCES IPEDS', source_url=f'https://nces.ed.gov/ipeds/datacenter/data/HD{year}.zip',
        release_year=year, retrieved_at=datetime.now(timezone.utc).isoformat(),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        coverage='Institutions marked active in this IPEDS release; not every institution or current course offering.',
        institutions=institutions)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip_file')
    parser.add_argument('--year', type=int, required=True)
    args = parser.parse_args()
    payload = build(args.zip_file, args.year)
    destination = Path(__file__).resolve().parents[1] / 'data' / 'colleges.json'
    destination.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f"Imported {len(payload['institutions'])} institutions from IPEDS {args.year}.")
