from flask import session, redirect, url_for, request, make_response
from db import token_is_valid, create_new_session

def require_auth(func, *args, **kwargs):
    def wrapper():
        headers = {}
        token = request.cookies.get('token', None)
        if token and token_is_valid(token):
            resp = make_response(redirect(url_for('search')))
            return func(*args, **kwargs)

        body = {
            'error': 'sessionExpiredError',
            'details': 'Session not valid'
        }
        return (body, 403)

    return wrapper