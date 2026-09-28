import re
from datetime import datetime, timezone
from extensions import db
from models import Task, User, StudentProfile
from tests.test_course_routes import complete_profile
from tests.test_feedback_overhaul import create
from tests.account_helpers import csrf


def review(client, ids):
    return client.post('/tasks/select',data={'csrf_token':csrf(client,'/tasks/select'),'task_ids':[str(i) for i in ids]})


def confirm(client, response):
    token=re.search(rb'name="selection_token" value="([^"]+)"',response.data).group(1).decode()
    return client.post('/tasks/delete-selected',data={'csrf_token':csrf(client,'/tasks/select'),'selection_token':token})


def test_review_then_delete_exact_selection(app,authed_client):
    complete_profile(authed_client)
    for title in ['Delete A','Delete B','Keep C']:
        create(authed_client,title=title)
    with app.app_context():
        ids=[t.id for t in Task.query.order_by(Task.id)]
    response=review(authed_client,ids[:2])
    assert response.status_code==200 and b'Delete 2 tasks?' in response.data
    with app.app_context(): assert Task.query.count()==3
    assert confirm(authed_client,response).status_code==302
    with app.app_context(): assert [t.title for t in Task.query.all()]==['Keep C']
    assert confirm(authed_client,response).status_code==302
    with app.app_context(): assert Task.query.count()==1


def test_project_expansion_and_preserved_completed_prep(app,authed_client):
    complete_profile(authed_client)
    create(authed_client,title='Project')
    with app.app_context():
        parent=Task.query.one()
        common=dict(student_profile_id=parent.student_profile_id,due_at=parent.due_at,estimated_minutes=20)
        child=Task(title='Step',parent=parent,**common)
        prep=Task(title='Prep',prep_for_id=parent.id,**common)
        history=Task(title='Completed prep',prep_for_id=parent.id,status='completed',**common)
        db.session.add_all([child,prep,history]);db.session.commit()
        identifier=parent.id
    response=review(authed_client,[identifier])
    assert b'Delete 3 tasks?' in response.data
    confirm(authed_client,response)
    with app.app_context():
        remaining=Task.query.one()
        assert remaining.title=='Completed prep' and remaining.prep_for_id is None


def test_foreign_selection_is_atomic_and_csrf_required(app,authed_client):
    complete_profile(authed_client)
    create(authed_client)
    with app.app_context():
        owned=Task.query.one().id
        other=User(username='other-bulk-user',password_hash='unused',onboarding_completed=True)
        profile=StudentProfile(user=other,first_name='Practice',grade=11,graduation_year=2028,current_gpa=3,target_gpa=3.5,study_hours_per_week=10)
        foreign=Task(student_profile=profile,title='Private',due_at=datetime.now(timezone.utc),estimated_minutes=20)
        db.session.add_all([other,profile,foreign]);db.session.commit()
        foreign_id=foreign.id
    assert review(authed_client,[owned,foreign_id]).status_code==404
    assert authed_client.post('/tasks/select',data={'task_ids':str(owned)}).status_code==400
    with app.app_context():assert Task.query.count()==2


def test_new_subtask_requires_new_review(app,authed_client):
    complete_profile(authed_client);create(authed_client)
    with app.app_context(): identifier=Task.query.one().id
    response=review(authed_client,[identifier])
    with app.app_context():
        parent=db.session.get(Task,identifier)
        db.session.add(Task(title='New step',parent=parent,student_profile_id=parent.student_profile_id,due_at=parent.due_at,estimated_minutes=10))
        db.session.commit()
    result=confirm(authed_client,response)
    assert result.location.endswith('/tasks/select')
    with app.app_context():assert Task.query.count()==2


def test_removing_one_step_updates_parent_and_rejects_forgery(app,authed_client):
    complete_profile(authed_client);create(authed_client,title='Parent')
    with app.app_context():
        parent=Task.query.one()
        common=dict(student_profile_id=parent.student_profile_id,due_at=parent.due_at,estimated_minutes=20)
        done=Task(title='Finished',parent=parent,status='completed',completed_at=datetime.now(timezone.utc),**common)
        todo=Task(title='Remove this step',parent=parent,**common)
        db.session.add_all([done,todo]);db.session.commit()
        parent_id,todo_id=parent.id,todo.id
    response=review(authed_client,[todo_id])
    invalid=authed_client.post('/tasks/delete-selected',data={'csrf_token':csrf(authed_client,'/tasks/select'),'selection_token':'forged'})
    assert invalid.location.endswith('/tasks/select')
    with app.app_context():assert Task.query.count()==3
    confirm(authed_client,response)
    with app.app_context():
        parent=db.session.get(Task,parent_id)
        assert parent.status=='completed' and len(parent.children)==1
