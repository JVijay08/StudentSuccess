"""Give legacy route tests the token a rendered browser form now supplies.

Previously protected endpoints stay raw so existing negative CSRF tests retain
their meaning. New security tests use FlaskClient directly. Protection is never
disabled in the application, including TESTING mode.
"""
import re
import secrets
from urllib.parse import urlsplit
from flask.testing import FlaskClient


class BrowserFormClient(FlaskClient):
    def open(self, *args, **kwargs):
        path = urlsplit(str(args[0] if args else kwargs.get('path', ''))).path
        protected = path in {
            '/register', '/login', '/transfer-planner', '/onboarding',
            '/settings/password', '/settings/clear-history', '/settings/delete-account',
            '/tutorial/start', '/tutorial/step', '/tutorial/finish',
            '/tasks/select', '/tasks/delete-selected', '/tasks/undo-schedule', '/tasks/ai/new',
        } or path.startswith('/ai/drafts/') or re.fullmatch(r'/tasks/\d+/(ai|reschedule)', path)
        if kwargs.get('method', 'GET').upper() == 'POST' and not protected:
            data = kwargs.get('data')
            if data is None or hasattr(data, 'items'):
                data = data.copy() if data is not None else {}
                if 'csrf_token' not in data:
                    with self.session_transaction() as state:
                        data['csrf_token'] = state.setdefault('access_csrf', secrets.token_urlsafe(32))
                    kwargs['data'] = data
        return super().open(*args, **kwargs)
