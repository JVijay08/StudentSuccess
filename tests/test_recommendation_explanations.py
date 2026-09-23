from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services.procrastination_service import explain_procrastination_risk
from services.suggestion_service import get_suggested_tasks
from services.recommendation_explanations import explain_recommendations


NOW = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)


def task(title="Assignment", **changes):
    values = dict(title=title, status="not_started", subject="Math", task_type=None,
                  due_at=NOW + timedelta(hours=12), estimated_minutes=30,
                  difficulty="low", interest_level="high", started_at=None,
                  planned_start_at=None)
    values.update(changes)
    return SimpleNamespace(**values)


def explain(tasks):
    return explain_recommendations(get_suggested_tasks(tasks, now=NOW), tasks)


def test_factor_totals_and_existing_score_rules():
    record = task(due_at=NOW-timedelta(hours=1), estimated_minutes=120,
                  difficulty="high", interest_level="low")
    result = explain_procrastination_risk(record, now=NOW)
    assert result["score"] == 10
    assert sum(f["points"] for f in result["factors"]) == result["score"]
    assert [f["reason"] for f in result["factors"]] == result["reasons"]


def test_imminent_deadline_precedes_harder_later_task_with_tier_explanation():
    rows = explain([task("Soon", subject="English"), task("Long", due_at=NOW+timedelta(hours=30), estimated_minutes=120, difficulty="high")])
    assert rows[0]["task"].title == "Soon"
    assert "urgency tier" in rows[0]["comparison_note"]
    assert "earlier" not in rows[0]["comparison_note"]


def test_equal_score_uses_deadline_and_exact_tie_does_not_invent_a_winner():
    rows = explain([task("Later", due_at=NOW+timedelta(hours=20)), task("Soon")])
    assert "deadline is earlier" in rows[0]["comparison_note"]
    rows = explain([task("A"), task("B")])
    assert "rules do not favor one" in rows[0]["comparison_note"]


def test_history_nudge_names_qualifying_sample_and_can_change_order():
    history = [task(status="completed", planned_start_at=NOW-timedelta(hours=8), started_at=NOW-timedelta(hours=2)) for _ in range(2)]
    rows = explain(history+[task("English", subject="English"), task("Math", due_at=NOW+timedelta(hours=20))])
    assert rows[0]["task"].title == "Math"
    assert "2 completed Math tasks" in rows[0]["history_note"]
    assert "6.0 hours late" in rows[0]["history_note"]
    assert "your recorded start history" in rows[0]["comparison_note"]
    assert sum(f["points"] for f in rows[0]["factors"]) == rows[0]["score"]


def test_missing_timestamps_and_other_subjects_do_not_count():
    rows = explain([task(status="completed"), task(status="completed", subject="English", planned_start_at=NOW, started_at=NOW), task()])
    assert "0 of 2 completed Math tasks" in rows[0]["history_note"]
    assert "only active task" in rows[0]["comparison_note"]


def test_sufficient_on_time_history_is_distinct_from_no_history():
    history = [task(status="completed", planned_start_at=NOW, started_at=NOW) for _ in range(2)]
    row = explain(history+[task()])[0]
    assert "History checked: 2" in row["history_note"]
    assert "no extra priority nudge" in row["history_note"]
    assert row["bonus"] == 0


def test_dashboard_brief_and_score_disclosure(authed_client):
    from tests.test_course_routes import complete_profile
    complete_profile(authed_client)
    authed_client.post('/tasks', data={
        'title':'Sample essay', 'due_at':'2027-01-01T12:00', 'estimated_minutes':'60',
        'difficulty':'high', 'interest_level':'medium', 'nonpersonal_confirmed':'yes',
    })
    response = authed_client.get('/dashboard')
    assert b'Why this task:' in response.data
    assert b'<details class="priority-reasons">' in response.data
    assert b'No history adjustment yet' in response.data
    assert b'not AI learning' in response.data
