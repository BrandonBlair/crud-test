from flask import session, redirect, url_for, request, make_response
from db import token_is_valid, create_new_session

def require_auth(func, *args, **kwargs):
    def wrapper():
        if 'LSESSION' not in request.cookies and 'token' not in request.cookies:
            resp = make_response(redirect(url_for('login')))
            resp.set_cookie('LSESSION', create_new_session())
            return resp

        session_id = request.cookies['LSESSION']
        token = request.cookies['token']
        if not token_is_valid(session_id, token):
            # Session is invalid, redirect to login page
            resp = make_response(redirect(url_for('login')))
            resp.set_cookie('LSESSION', create_new_session())
            return resp

        return func(*args, **kwargs)

    return wrapper