"""Minimal structured events. Never log credentials, input text, tokens or raw IPs."""
import json
from flask import current_app, request, has_request_context


def security_event(event, outcome='blocked', user_id=None):
    record = {'event': event, 'outcome': outcome,
              'endpoint': request.endpoint if has_request_context() else None}
    if isinstance(user_id, int):
        record['user_id'] = user_id
    current_app.logger.warning('security %s', json.dumps(record, separators=(',', ':')))
