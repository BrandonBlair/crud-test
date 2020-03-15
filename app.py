import json
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
@require_auth
def index():
    print("index")
    return redirect(url_for('search'))


@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    # No LSESSION
    if 'LSESSION' not in request.cookies:
        print("There was not lsession in request.cookies")
        resp = make_response(
            render_template('login.html')
        )
        resp.set_cookie('LSESSION', db.create_new_session())
        return resp

    # Attempted login
    if request.method == 'POST':
        if not request.form['email'] or not request.form['password']:
            print("Must provide both an email and a password to login")
            return redirect(url_for('login'))
        email_provided = request.form['email']

        if not db.password_matches(email_provided, request.form['password']):
            print("Login not valid")
            return render_template('login.html')

        member_id = db.get_member_by_email(email_provided)
        db.associate_session_with_user(request.cookies['LSESSION'], member_id, request.remote_addr, request.headers['User-Agent'])
        resp = make_response(redirect(url_for('search')))
        resp.set_cookie('token', db.add_token(request.cookies['LSESSION']))
        return resp

    elif request.method == 'GET':
        return render_template('login.html')

    else:
        return redirect(url_for('login'))

@app.route('/v1/join', methods=['POST'], endpoint='join')
def api_join():
    headers = {}

    # Ensure user has a session
    lsession = request.cookies.get('LSESSION')
    if lsession is None:  # New user or cookies have been cleared
        lsession = db.create_new_session()
    headers['LSESSION'] = lsession

    # Check fields
    required_fields = {'email', 'password', 'conf_password'}
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
    conf_pw = request.form.get('conf_password')
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
    session_id = lsession
    user_agent = request.headers['User-Agent']
    db.associate_session_with_user(lsession, member_id, request.remote_addr, user_agent)
    token_id = db.add_token(lsession)
    print("Token {} created successfully...".format(token_id))
    headers['token'] = str(token_id)
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
    resource = db.add_resource_to_inventory(
        body['title'],
        body['author_first'],
        body['author_middle'],
        body['author_last'],
        body['edition'],
        body['isbn10'],
        body['isbn13']
    )
    return (resource, 200)


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




