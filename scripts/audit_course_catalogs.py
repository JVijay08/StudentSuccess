"""Report quarantined imports and grouped listings without changing saved IDs."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.course_service import get_catalogs, load_courses, browse_courses

report = []
for catalog, config in get_catalogs().items():
    raw = load_courses(catalog)
    visible = browse_courses(catalog)
    report.append({
        'catalog': catalog,
        'coverage': config['description'],
        'records': len(raw),
        'visible_groups': len(visible),
        'needs_source_verification': [c['course_id'] for c in raw if c['quality_review']],
        'grouped_listings': {c['course_id']: c['alternate_ids'] for c in visible if len(c['alternate_ids']) > 1},
    })
print(json.dumps(report, indent=2))
