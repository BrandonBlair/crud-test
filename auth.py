from flask import session, redirect, url_for, request, make_response
from db import token_is_valid, create_new_session, add_token, NoMemberFoundException

def require_auth(func, *args, **kwargs):
    def wrapper():
        headers = {}

        token = request.cookies.get('token', None)
        if not token:
            body = {
                'error': 'tokenInvalidError',
                'details': 'token {} is not valid'.format(token)
            }
            return (body, 403)

        resp = make_response(redirect(url_for('search')))
        return func(*args, **kwargs)



    return wrapper