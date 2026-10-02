import json
import pytest
from datetime import datetime, timedelta, timezone
from extensions import db
from models import Task, User
from models.ai_planning import AIDraft, AIQuota
from services import ai_planning as ai
from tests.test_course_routes import complete_profile
from tests.test_feedback_overhaul import create


@pytest.fixture
def ready(app, authed_client, monkeypatch):
    complete_profile(authed_client)
    create(authed_client, title="Research clean energy", estimated_minutes="60")
    app.config.update(GROQ_API_KEY="test-not-a-key", AI_ENABLED=True)
    monkeypatch.setattr(ai, "generate", lambda text, budget: [
        {"title":"Find sources","minutes":20},{"title":"Draft outline","minutes":40}])
    with app.app_context():
        task_id=Task.query.one().id
    return authed_client,task_id


def token(client):
    with client.session_transaction() as s:
        s["access_csrf"]="ai-test-csrf"
    return "ai-test-csrf"


def generate(client, tid, **extra):
    return client.post(f"/tasks/{tid}/ai",data={
        "csrf_token":token(client),"description":"Research clean energy",
        "consent":"yes",**extra})


def apply(client, url, **extra):
    return client.post(url,data={"csrf_token":token(client),"action":"apply",
        "selected":["0","1"],"title_0":"Edited research step","minutes_0":"20",
        "title_1":"Create outline","minutes_1":"40","nonpersonal_confirmed":"yes",**extra})


def test_preview_apply_and_replay(app,ready):
    client,tid=ready
    response=generate(client,tid)
    assert response.status_code==302
    url=response.location
    with app.app_context():assert Task.query.count()==1
    assert b"Make these steps your own" in client.get(url).data
    assert apply(client,url).status_code==302
    apply(client,url)
    with app.app_context():
        assert Task.query.count()==3
        children=Task.query.filter_by(parent_task_id=tid).all()
        assert sum(c.estimated_minutes for c in children)==60
        assert children[0].title=="Edited research step"
        assert all(c.planned_start_at is None for c in children)
        assert AIDraft.query.one().steps==[]


def test_consent_csrf_disabled_and_demo(app,ready,monkeypatch):
    client,tid=ready
    def forbidden(*args):pytest.fail("Provider must not be called")
    monkeypatch.setattr(ai,"generate",forbidden)
    assert client.post(f"/tasks/{tid}/ai",data={"description":"x"}).status_code==400
    assert b"Confirm the sharing" in generate(client,tid,consent="").data
    app.config["GROQ_API_KEY"]=""
    assert b"not available" in generate(client,tid).data
    app.config["GROQ_API_KEY"]="test"
    with client.session_transaction() as s:s["demo_mode"]=True
    assert b"not available" in generate(client,tid).data


def test_ownership(app,ready):
    client,tid=ready
    url=generate(client,tid).location
    other=app.test_client();other.post("/demo")
    assert other.get(f"/tasks/{tid}/ai").status_code==404
    assert other.get(url).status_code==404
    assert other.post(url,data={"csrf_token":token(other)}).status_code==404


def test_stale_and_expired_drafts(app,ready):
    client,tid=ready
    url=generate(client,tid).location
    with app.app_context():
        db.session.get(Task,tid).estimated_minutes=90;db.session.commit()
    assert b"assignment changed" in apply(client,url).data
    with app.app_context():
        assert Task.query.count()==1
        AIDraft.query.one().expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        db.session.commit()
    assert apply(client,url).status_code==302
    with app.app_context():assert Task.query.count()==1


def test_edit_validation_preserves_values(app,ready):
    client,tid=ready
    url=generate(client,tid).location
    response=apply(client,url,minutes_0="55",title_0="Keep my edit")
    assert b"exceed" in response.data and b"Keep my edit" in response.data
    with app.app_context():assert Task.query.count()==1
    assert b"whole minutes" in apply(client,url,minutes_0="oops").data
    assert b"between one and eight" in apply(client,url,selected=[]).data


def test_discard_and_account_cleanup(app,ready):
    client,tid=ready
    url=generate(client,tid).location
    assert client.post(url,data={"csrf_token":token(client),"action":"discard"}).status_code==302
    with app.app_context():
        assert AIDraft.query.count()==0 and Task.query.count()==1
        user=db.session.get(User,client.user_id)
        db.session.add(AIDraft(id="cleanup",user_id=user.id,task_id=tid,snapshot="x",
            steps=[],expires_at=datetime.now(timezone.utc)))
        db.session.commit();db.session.delete(user);db.session.commit()
        assert AIDraft.query.count()==0


def test_limits_count_failed_provider_requests(app,ready,monkeypatch):
    client,tid=ready
    def unavailable(*args):raise ai.AIUnavailable("Try later")
    monkeypatch.setattr(ai,"generate",unavailable)
    assert b"Try later" in generate(client,tid).data
    assert b"limit reached" in generate(client,tid).data
    with app.app_context():assert Task.query.count()==1


def test_site_quota_atomic_rollback(app,ready):
    app.config["AI_SITE_DAILY_LIMIT"]=1
    with app.app_context():
        ai.reserve(100)
        with pytest.raises(ai.AIUnavailable):ai.reserve(101)
        assert not AIQuota.query.filter(AIQuota.key.endswith(":user:101")).all()


@pytest.mark.parametrize("value",[
    [],[{"title":"x","minutes":True}],[{"title":"x","minutes":0}],
    [{"title":"x","minutes":61}],[{"title":"x"*161,"minutes":1}],
    [{"title":"x","minutes":40},{"title":"y","minutes":40}],["text"],
])
def test_reject_invalid_model_output(value):
    with pytest.raises(ValueError):ai.validate_steps(value,60)


def test_transport_is_bounded_and_minimal(app,monkeypatch):
    app.config.update(GROQ_API_KEY="not-real",GROQ_MODEL="openai/gpt-oss-20b")
    observed={}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):
            assert n==65537
            return json.dumps({"choices":[{"finish_reason":"stop","message":{"content":
                json.dumps({"steps":[{"title":"Read prompt","minutes":10}]})}}]}).encode()
    def transport(request,timeout):
        observed.update(json.loads(request.data))
        assert timeout==15
        assert request.full_url=="https://api.groq.com/openai/v1/chat/completions"
        return Response()
    monkeypatch.setattr(ai.urllib.request,"urlopen",transport)
    with app.app_context():assert ai.generate("Read essay prompt",10)[0]["minutes"]==10
    assert json.loads(observed["messages"][1]["content"])=={"assignment":"Read essay prompt","total_minutes":10}
    assert "tools" not in observed


def test_provider_errors_do_not_leak(app,monkeypatch):
    app.config["GROQ_API_KEY"]="secret-test-value"
    def fail(*args,**kwargs):raise ValueError("private provider response secret-test-value")
    monkeypatch.setattr(ai.urllib.request,"urlopen",fail)
    with app.app_context(),pytest.raises(ai.AIUnavailable) as err:ai.generate("private task",10)
    assert "private" not in str(err.value) and "secret" not in str(err.value)
