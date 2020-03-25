from flask import session, redirect, url_for, request, make_response
from db import token_is_valid, create_new_session

def require_auth(func, *args, **kwargs):
    def wrapper():
        headers = {}

        # Use token if it is present
        token = request.cookies.get('token', None)
        if token_is_valid(token):
            resp = make_response(redirect(url_for('search')))
            return func(*args, **kwargs)

        lsession = request.headers.get('LSESSION', None)
        # Session missing
        if not lsession:
            resp = make_response(redirect(url_for('login')))
            headers['LSESSION'] = create_new_session()
            body = {
                'error': 'noSessionError',
                'details': 'No session found'
            }
            return (body, 400, headers)

        # Session had expired
        session_id = lsession
        if not session_is_valid(session_id):
            body = {
                'error': 'sessionExpiredError',
                'details': 'Session not valid'
            }
            return (body, 403, headers)

        return func(*args, **kwargs)

    return wrapper