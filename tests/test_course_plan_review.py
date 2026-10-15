from types import SimpleNamespace as NS
from services.course_plan_review import review_plan


def row(id, name, year, status='planned', prerequisites=()):
    return dict(planned=NS(id=id,school_year=year,status=status),course=dict(course_name=name,display_name=name,prerequisites=prerequisites))


def test_prerequisite_order_and_completed_records():
    rows=[row(1,'Algebra',9),row(2,'Calculus',11,prerequisites=['Algebra'])]
    assert review_plan(rows,[],10)[0][2] == []
    rows[0]['planned'].school_year=12
    assert review_plan(rows,[],10)[0][2] == ['Algebra']
    rows[0]['planned'].status='completed'
    assert review_plan(rows,[],10)[0][2] == []


def test_considering_is_not_confirmed_preparation():
    rows=[row(1,'Algebra',9,'considering'),row(2,'Calculus',11,prerequisites=['Algebra'])]
    assert review_plan(rows,[],10)[0][2] == ['Algebra']


def test_hours_group_by_grade_and_term_exclude_completed():
    courses=[NS(school_year=11,term='Fall',weekly_hours=42,status='planned'),NS(school_year=11,term=' fall ',weekly_hours=42,status='considering'),NS(school_year=11,term='Spring',weekly_hours=3,status='planned'),NS(school_year=11,term='Fall',weekly_hours=100,status='completed')]
    warnings=review_plan([],courses,12)[1]
    assert len(warnings)==1
    assert warnings[0]['hours']==84
    assert not warnings[0]['impossible']
    courses.append(NS(school_year=11,term='Fall',weekly_hours=100,status='planned'))
    assert review_plan([],courses,12)[1][0]['impossible']
