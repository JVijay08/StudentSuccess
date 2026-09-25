from datetime import datetime
import math
from zoneinfo import available_timezones

from flask import Blueprint, g, redirect, render_template, request, url_for
from extensions import db
from models import StudentProfile
from services.auth_service import login_required
from services.access_service import verify_csrf
from services.settings_service import get_or_create_settings
from services.privacy_service import confirmation_errors

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    user = g.current_user
    preferences = get_or_create_settings(user)
    profile = user.profile
    first_setup = not user.onboarding_completed
    errors = []
    defaults = dict(academic_context=preferences.academic_context,
        grade=profile.grade if profile else 9, study_hours=profile.study_hours_per_week if profile else 10,
        timezone_name=preferences.timezone_name, college_program=preferences.college_program,
        college_term=preferences.college_term, term_credit_goal=preferences.term_credit_goal if preferences.term_credit_goal is not None else '',
        default_task_minutes=preferences.default_task_minutes, work_session_minutes=preferences.work_session_minutes,
        dashboard_mode=preferences.dashboard_mode, theme='light' if preferences.theme == 'system' else preferences.theme, text_scale=preferences.text_scale,
        reduce_motion=preferences.reduce_motion, reminders_enabled=preferences.reminders_enabled)
    values = {**defaults, **request.form} if request.method == 'POST' else defaults
    if request.method == 'POST':
        verify_csrf()
        errors.extend(confirmation_errors(request.form))
        if 'preferences_submitted' in request.form:
            values['reduce_motion'] = 'reduce_motion' in request.form
            values['reminders_enabled'] = 'reminders_enabled' in request.form
        context = values['academic_context']
        if context not in {'high_school','college'}:
            errors.append('Choose high school or college / university.')
        if values['timezone_name'] not in available_timezones():
            errors.append('Choose a valid planner timezone.')
        try:
            hours = float(values['study_hours'])
            if not math.isfinite(hours) or not 0 <= hours <= 80:
                raise ValueError
        except (ValueError,TypeError):
            errors.append('Study hours must be between 0 and 80 per week.')
        try:
            grade = int(values['grade']) if context == 'high_school' else (profile.grade if profile else 9)
            if grade not in {9,10,11,12}: raise ValueError
        except (ValueError,TypeError):
            errors.append('Choose a high-school grade from 9 to 12.')
        choices = dict(default_task_minutes={15,25,30,45,60,90,120}, work_session_minutes={15,20,25,30,45,50,60},
            text_scale={100,125,150,200}, dashboard_mode={'standard','focus'}, theme={'light','dark','high-contrast','system'})
        parsed = {}
        for key, allowed in choices.items():
            try:
                value = int(values[key]) if key in {'default_task_minutes','work_session_minutes','text_scale'} else values[key]
                if value not in allowed: raise ValueError
                parsed[key] = value
            except (ValueError,TypeError):
                errors.append('Choose a valid '+key.replace('_',' ')+'.')
        program, term, goal = preferences.college_program, preferences.college_term, preferences.term_credit_goal
        if context == 'college':
            program, term = str(values['college_program']).strip(), str(values['college_term']).strip()
            if len(program)>120 or len(term)>60:
                errors.append('Use up to 120 characters for your program and 60 for your term.')
            try:
                goal = None if values['term_credit_goal'] in ('',None) else float(values['term_credit_goal'])
                if goal is not None and (not math.isfinite(goal) or not 0 <= goal <= 60): raise ValueError
            except (ValueError,TypeError):
                errors.append('Enter a personal term credit target between 0 and 60, or leave it blank.')
        if not errors:
            if profile is None:
                profile = StudentProfile(user_id=user.id, first_name='Planner',grade=grade,
                    graduation_year=datetime.now().year+4,current_gpa=0,target_gpa=0,study_hours_per_week=hours)
                db.session.add(profile)
            profile.grade, profile.study_hours_per_week = grade, hours
            preferences.academic_context = context
            preferences.timezone_name = values['timezone_name']
            preferences.college_program, preferences.college_term, preferences.term_credit_goal = program, term, goal
            for key, value in parsed.items(): setattr(preferences,key,value)
            if 'preferences_submitted' in request.form:
                preferences.reduce_motion = 'reduce_motion' in request.form
                preferences.reminders_enabled = 'reminders_enabled' in request.form
            user.onboarding_completed = True
            db.session.commit()
            return redirect(url_for('main.dashboard') if first_setup else url_for('settings.settings'))
    return render_template('onboarding.html',errors=errors,values=values,first_setup=first_setup,
                           timezones=sorted(available_timezones()))


@profile_bp.get('/profile')
@login_required
def profile_view():
    return redirect(url_for('profile.onboarding'))
