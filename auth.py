from flask import session, redirect, url_for
from db import token_is_valid, create_new_session

def require_auth(func):
    print("WE ARE HERE")
    def wrapper():
        print("WE ARE IN WRAPPER")
        # Already logged in?
        if 'session_id' in session and 'token' in session:
            session_id = session['session_id']
            token = session['token']
            if not token_is_valid(session_id, token):
                session['session_id'] = create_new_session()
                return redirect(url_for('login'))
            func(*args, **kwargs)
        return redirect(url_for('login'))
    return wrapper