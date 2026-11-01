import json
from flask import Blueprint, current_app, g, request, render_template, redirect, url_for, flash, session, abort
from itsdangerous import URLSafeTimedSerializer, BadData
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User
from services.auth_service import login_required
from services.settings_service import get_or_create_settings
from services.browser_transfer import validate_backup, review_backup, import_backup, MAX_BYTES

browser_transfer_bp = Blueprint('browser_transfer', __name__)


@browser_transfer_bp.route('/planner/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    if session.get('demo_mode') or session.get('tutorial_mode'):
        return render_template('browser_transfer.html', practice=True)
    if not g.current_user.profile:
        return redirect(url_for('profile.onboarding'))
    get_or_create_settings(g.current_user)
    signer = URLSafeTimedSerializer(current_app.secret_key, salt='browser-transfer-v1')
    error, data, rows, preview = None, None, [], None
    if request.method == 'POST':
        try:
            if request.form.get('confirmed') != 'yes':
                raise ValueError('Confirm that you want to copy this browser plan into the signed-in account.')
            if request.form.get('save'):
                payload = signer.loads(request.form.get('preview', ''), max_age=1800)
                if payload['user'] != g.current_user.id:
                    abort(404)
                data = validate_backup(json.dumps(payload['data']).encode())
                db.session.query(User).filter_by(id=g.current_user.id).with_for_update().one()
                db.session.expire(g.current_user.profile, ['tasks', 'planned_courses'])
                db.session.expire(g.current_user, ['term_courses'])
                count = import_backup(data, g.current_user, set(payload['allowed']))
                if request.form.get('apply_context') == 'yes':
                    g.current_user.settings.academic_context = data['context']
                if request.form.get('apply_budget') == 'yes' and data['budget'] is not None:
                    if data['budget'] > 80:
                        raise ValueError('The account study budget supports up to 80 hours. Leave that option unchecked.')
                    g.current_user.profile.study_hours_per_week = data['budget']
                db.session.commit()
                flash(f'Transferred {count} tasks and courses. Existing account items and your browser copy were kept.', 'success')
                return redirect(url_for('main.dashboard'))
            upload = request.files.get('backup')
            if not upload:
                raise ValueError('Choose a browser backup or use the plan saved in this browser.')
            data = validate_backup(upload.read(MAX_BYTES + 1))
            rows = review_backup(data, g.current_user)
            preview = signer.dumps(dict(user=g.current_user.id, data=data,
                                        allowed=[r['key'] for r in rows if not r['skip']]))
        except BadData:
            error = 'This preview expired or is invalid. Preview your browser plan again.'
        except (ValueError, TypeError, KeyError) as exc:
            db.session.rollback()
            error = str(exc) if isinstance(exc, ValueError) else 'This backup is not valid. Export it again from the browser planner.'
        except IntegrityError:
            db.session.rollback()
            error = 'Your account changed during this transfer. Preview again; no changes were saved.'
    return render_template('browser_transfer.html', practice=False, error=error, data=data, rows=rows, preview=preview)
