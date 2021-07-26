import json

import flask
from flask import request, make_response, abort, Flask, redirect, url_for, render_template
import requests

from auth import require_auth
import db


db.prepare_db()



app = Flask(__name__)

# This app is just for testing. Never expose your secret in a production app!
app.secret_key = b'mysecretkey'


@app.route('/', endpoint='index')
def index():
    headers = {}
    lsession = request.headers.get('LSESSION', None)
    if not lsession:
        lsession = db.create_new_session()
        headers['LSESSION'] = lsession
    return redirect(url_for('login')), 302, headers


@app.route('/v1/login', methods=['POST'], endpoint='api_login')
def api_login():
    headers = {}
    lsession = request.headers.get('LSESSION', None)
    if not lsession:
        lsession = db.create_new_session()
        headers['LSESSION'] = lsession
    if not request.form['email'] or not request.form['password']:
        body = {
            'error': 'missingFields',
            'details': 'Must include email and password'
        }
        return (body, 400, headers)

    email_provided = request.form['email']
    if not db.password_matches(email_provided, request.form['password']):
        print(email_provided, request.form['password'])
        body = {
            'error': 'passwordInvalid',
            'details': 'Password was not valid'
        }
        return (body, 400, headers)

    member_id = db.get_member_by_email(email_provided)
    db.associate_session_with_user(lsession, member_id, request.remote_addr, request.headers['User-Agent'])
    token = db.add_token(lsession)
    headers['Set-Cookie'] = f'token={token}; Path=/; HttpOnly'
    body = {
        'error': 'None',
        'details': 'Member logged in successfully'
    }
    return (body, 200, headers)


@app.route('/login', methods=['GET'], endpoint='login')
def login():
    return render_template('login.html')

@app.route('/join', methods=['GET'], endpoint='join')
def join():
    return render_template('join.html')

@app.route('/v1/join', methods=['POST'], endpoint='api_join')
def api_join():
    headers = {}

    # Ensure user has a session
    lsession = request.headers.get('LSESSION')
    if lsession is None:  # New user or cookies have been cleared
        lsession = db.create_new_session()
    headers['LSESSION'] = lsession

    # Check fields
    required_fields = {'email', 'password', 'confirm_password'}
    received_fields = set(request.form.keys())
    if received_fields.intersection(required_fields) != required_fields:
        body = {
            'error': 'Missing fields',
            'details': (
                f"Fields required: {', '.join(required_fields)}, ",
                f"Fields received: {', '.join(received_fields)}"
            )
        }
        return (body, 400, headers)

    # Validate password
    pw = request.form.get('password')
    conf_pw = request.form.get('confirm_password')
    if pw != conf_pw:
        body = {
            'error': 'passwordMismatch',
            'details': (
                f"{pw} != {conf_pw} (password vs confirmation)"
            )
        }
        return (body, 400, headers)

    # Add new member
    try:
        member_id = db.add_new_member(request.form['email'], request.form['password'])
    except db.InvalidEmailException as iee:
        body = {
            'error': 'invalidEmail',
            'details': str(iee)
        }
        return (body, 400, headers)

    if member_id == None:  # Failed to create a new member
        body = {
            'error': 'joinFailed',
            'details': 'Failed to create new member'
        }
        return (body, 400, headers)

    # Associate session with user
    user_agent = request.headers['User-Agent']
    db.associate_session_with_user(lsession, member_id, request.remote_addr, user_agent)
    token_id = db.add_token(lsession)
    headers['Set-Cookie'] = f'token={token_id}; Path=/; HttpOnly'
    body = {
        'error': 'None',
        'details': 'Member created successfully'
    }
    return (body, 200, headers)


@app.route('/search', methods=['GET'], endpoint='search')
@require_auth
def search():
    return render_template('search.html')


@app.route('/v1/search', methods=['GET'], endpoint='api_search')
@require_auth
def api_search():
    author = request.args.get('author')
    title = request.args.get('title')
    isbn = request.args.get('isbn')

    if not author and not title and not isbn:  # No fields were provided
        body = {
            'results': []
        }
        return (body, 200)

    fields = {
        'author': author,
        'title': title,
        'isbn': isbn
    }

    results = db.search_resources(**fields)  # Pass dict as kwargs for extensibility
    results_as_dicts = [r.__dict__ for r in results]
    body = {
        'results': results_as_dicts
    }

    return (body, 200)


@app.route('/resource', methods=['GET'], endpoint='resource')
@require_auth
def resource():
    return render_template('add_resource.html')


@app.route('/v1/resource', methods=['POST'], endpoint='api_resource')
@require_auth
def api_resource():
    body = request.json

    error = 'None'
    details = 'None'
    status = 0
    resource = {}

    try:
        resource = db.add_resource_to_inventory(
            body['title'],
            body['authorFirst'],
            body['authorMiddle'],
            body['authorLast'],
            body['edition'],
            body['isbn10'],
            body['isbn13']
        )
        details = f"{body['title']} added successfully."
        status = 200
    except Exception as e:
        print(e)
        error = "add-resource-error"
        details = str(e)
        status = 500

    body = {
        'resource': resource,
        'error': error,
        'details': details
    }
    return (body, status)


@app.route('/methods/<user_id>', methods=['DELETE'], endpoint='methods')
@app.route('/methods', methods=['POST', 'GET'], endpoint='methods')
def methods(user_id=None):
    formatted_resp = f"HTTP Request Method {request.method} | "
    if request.method == 'DELETE':
        formatted_resp += f"Ok, deleting user {user_id}"
        return formatted_resp
    if request.args:
        formatted_resp += "Query String args: "
        for arg in request.args.items():
            formatted_resp += f"{arg[0]} = {arg[1]}, "
    if request.json:
        formatted_resp += f"JSON: {request.json}"
    if request.form:
        formatted_resp += f"FORM: "
        for item in request.form.items():
            formatted_resp += f"{item[0]} = {item[1]}, "

    return formatted_resp


@app.route('/logout', methods=['GET'], endpoint='logout')
def logout():
    del request.cookies['token']
    del request.cookies['LSESSION']
    redirect(url_for('login'))




