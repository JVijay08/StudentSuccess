import pytest
from extensions import db
from models import Task
from models.ai_planning import AIDraft
from services import ai_task_batch as batch
from tests.test_ai_planning import ready, token


def samples():
    opts=dict(format='mixed',style='detailed',limit=5,budget=None)
    rows=batch.validate([
        dict(title='Math exercises',subject='Math',due_at='2027-06-01T23:59',estimated_minutes=30,steps=[]),
        dict(title='History essay',subject='History',due_at='2027-06-03T18:00',estimated_minutes=60,
             steps=[dict(title='Research',minutes=20),dict(title='Draft',minutes=40)])],opts)
    return rows


def draft(client, monkeypatch, **extra):
    monkeypatch.setattr(batch,'generate',lambda *args:samples())
    response=client.post('/tasks/ai/new',data=dict(csrf_token=token(client),description='Math homework and history essay',
        output_format='mixed',consent='yes',**extra))
    assert response.status_code==302
    return response.location


def payload(client):
    data=dict(csrf_token=token(client),action='apply',selected=['0','1'],steps_1=['0','1'])
    for i,row in enumerate(samples()):
        for k,v in row.items():
            if k!='steps':data[f'{k}_{i}']=str(v)
        for j,step in enumerate(row['steps']):
            data[f'step_title_{i}_{j}']=step['title']
            data[f'step_minutes_{i}_{j}']=str(step['minutes'])
    return data


def test_mixed_preview_and_atomic_save(app,ready,monkeypatch):
    client,_=ready;url=draft(client,monkeypatch)
    assert b'Review drafted tasks' in client.get(url).data
    data=payload(client);data['action']='preview'
    assert b'4 tasks' in client.post(url,data=data).data
    with app.app_context():assert Task.query.count()==1
    data['action']='apply'
    assert client.post(url,data=data).status_code==302
    client.post(url,data=data)
    with app.app_context():
        assert Task.query.count()==5
        essay=Task.query.filter_by(title='History essay').one()
        assert len(essay.children)==2
        assert Task.query.filter_by(title='Math exercises').one().parent_task_id is None
        assert AIDraft.query.one().steps==[]


def test_separate_steps_repeat_and_deselection(app,ready,monkeypatch):
    client,_=ready;url=draft(client,monkeypatch)
    data=payload(client);data.update(selected=['1'],save_as_1='separate',repeat_rule_1='daily',repeat_until_1='2027-06-05')
    assert client.post(url,data=data).status_code==302
    with app.app_context():
        assert Task.query.count()==7
        assert Task.query.filter_by(title='History essay').count()==0
        assert Task.query.filter_by(title='Research').count()==3
        assert all(t.parent_task_id is None and t.recurrence_rule is None for t in Task.query.all())


def test_validation_keeps_edits_and_writes_nothing(app,ready,monkeypatch):
    client,_=ready;url=draft(client,monkeypatch)
    data=payload(client);data.update(title_0='Keep my title',due_at_1='')
    response=client.post(url,data=data)
    assert b'Keep my title' in response.data and b'valid due date' in response.data
    data=payload(client);data['selected']=['0','0']
    assert b'only once' in client.post(url,data=data).data
    data=payload(client);data.update(repeat_rule_0='daily',repeat_until_0='2028-01-01')
    assert b'more than 100' in client.post(url,data=data).data
    with app.app_context(): assert Task.query.count()==1


def test_budget_includes_repeats(app,ready,monkeypatch):
    client,_=ready;url=draft(client,monkeypatch,total_budget='90')
    data=payload(client);data.update(repeat_rule_0='daily',repeat_until_0='2027-06-02')
    assert b'exceeds your total' in client.post(url,data=data).data
    with app.app_context():assert Task.query.count()==1


def test_owner_expiry_discard_and_consent(app,ready,monkeypatch):
    client,_=ready;url=draft(client,monkeypatch)
    other=app.test_client();other.post('/demo')
    assert other.get(url).status_code==404
    assert other.post(url,data=payload(other)).status_code==404
    assert client.post(url,data={'csrf_token':token(client),'action':'discard'}).status_code==302
    assert client.get(url).status_code==404
    monkeypatch.setattr(batch,'generate',lambda *a:pytest.fail('No consent'))
    response=client.post('/tasks/ai/new',data=dict(csrf_token=token(client),description='x',output_format='mixed'))
    assert b'Confirm the sharing' in response.data


def test_single_task_and_global_overrides(app,ready,monkeypatch):
    client,_=ready
    monkeypatch.setattr(batch,'generate',lambda *args:[samples()[0]])
    response=client.post('/tasks/ai/new',data=dict(csrf_token=token(client),description='Math',
        output_format='single',consent='yes',default_subject='Algebra',default_due='2027-06-10T14:00'))
    with app.app_context():
        row=AIDraft.query.one().steps[0]
        assert row['subject']=='Algebra' and row['due_at']=='2027-06-10T14:00'
    data=payload(client);data['selected']=['0'];data['subject_0']='Algebra'
    assert client.post(response.location,data=data).status_code==302
    with app.app_context():
        assert Task.query.count()==2
        assert Task.query.filter_by(title='Math exercises').one().children==[]


def test_model_contract_and_options():
    opts=dict(format='multiple',style='concise',limit=2,budget=None)
    with pytest.raises(ValueError):batch.validate(samples(),opts)
    opts['format']='mixed';opts['budget']=10
    with pytest.raises(ValueError):batch.validate(samples(),opts)
    opts['budget']=None;opts['limit']=1
    with pytest.raises(ValueError):batch.validate(samples(),opts)
    for form in [dict(task_limit='99'),dict(output_format='bad'),dict(total_budget='0')]:
        with pytest.raises(ValueError):batch.options(form)


def test_batch_transport_shape_and_input_limits(app,ready,monkeypatch):
    client,_=ready
    seen={}
    def response(description,budget,instruction,max_tokens):
        import json
        seen.update(json.loads(description))
        assert max_tokens==3300
        return {'tasks':[dict(title='Independent task',subject='',due_at=None,estimated_minutes=20,steps=[])]}
    monkeypatch.setattr(batch.ai,'_request',response)
    opts=dict(format='single',style='concise',limit=1,budget=30)
    result=batch.generate('Write notes','2026-10-04',opts)
    assert result[0]['due_at']=='' and result[0]['steps']==[]
    assert seen==dict(note='Write notes',local_today='2026-10-04',**opts)
    url=draft(client,monkeypatch)
    assert client.post(url,data=dict(csrf_token=token(client),padding='x'*(256*1024))).status_code==413
    assert client.post('/tasks/ai/new',data=dict(csrf_token=token(client),padding='x'*16384)).status_code==413


def test_thirty_independent_tasks_preview_and_save(app,ready,monkeypatch):
    client,_=ready
    opts=batch.options(dict(output_format='multiple',task_limit='30'))
    tasks=[dict(title=f'Practice topic {i+1}',subject='Math',due_at='2027-06-01T23:59',estimated_minutes=10,steps=[]) for i in range(30)]
    rows=batch.validate(tasks,opts)
    monkeypatch.setattr(batch,'generate',lambda *args:rows)
    response=client.post('/tasks/ai/new',data=dict(csrf_token=token(client),description='Thirty practice topics',output_format='multiple',task_limit='30',consent='yes'))
    assert response.status_code==302
    data=dict(csrf_token=token(client),action='preview',selected=[str(i) for i in range(30)])
    for i,row in enumerate(rows):
        for key,value in row.items():
            if key!='steps':data[f'{key}_{i}']=str(value)
    assert b'30 tasks' in client.post(response.location,data=data).data
    with app.app_context():assert Task.query.count()==1
    data['action']='apply'
    assert client.post(response.location,data=data).status_code==302
    with app.app_context():assert Task.query.count()==31
    with pytest.raises(ValueError):batch.options(dict(task_limit='31'))
    with pytest.raises(ValueError):batch.validate(tasks+[tasks[0]],opts)
