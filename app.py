import flask
from flask import request, make_response, abort, Flask, redirect, url_for, render_template

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


@app.route('/join', methods=['POST', 'GET'], endpoint='join')
def join():
    if 'LSESSION' in request.cookies and 'token' in request.cookies:
        if db.token_is_valid(request.cookies['LSESSION'], request.cookies['token']):
            print("Session already valid, redirecting to search")
            redirect(url_for('search'))
    if 'LSESSION' not in request.cookies:
        resp = make_response()
        resp.set_cookie('LSESSION', db.create_new_session())
    if request.method == 'GET':
        return render_template('join.html')
    elif request.method == 'POST':
        required_fields = {'email', 'password', 'confirm_password'}
        supplied_fields = set(request.form.keys())
        if not supplied_fields.issubset(required_fields):
            print("Must include email, password, and confirm_password fields")
            return render_template('join.html')

        if request.form['password'] != request.form['confirm_password']:
            print("Password does not match Confirm Password")
            return render_template('join.html')

        try:
            member_id = db.add_new_member(request.form['email'], request.form['password'])
        except db.InvalidEmailException:
            return render_template('bad_email.html')
        if member_id == None:
            return render_template('bad_email.html')
        print(request.cookies)
        session_id = request.cookies['LSESSION']
        user_agent = request.headers['User-Agent']
        db.associate_session_with_user(request.cookies['LSESSION'], member_id, request.remote_addr, user_agent)
        token_id = db.add_token(request.cookies['LSESSION'])
        print("Token {} created successfully...".format(token_id))

        resp = make_response(redirect(url_for('search')))
        resp.set_cookie('token', str(token_id))
        return resp


@app.route('/search', methods=['GET'], endpoint='search')
@require_auth
def search():
    if 'search_author' in request.args:
        results = db.search_resources_by_author(request.args.get('search_author'))
    elif 'search_title' in request.args:
        results = db.search_resources_by_title(request.args.get('search_title'))
    elif 'search_isbn10' in request.args:
        results = db.search_resources_by_isbn10(request.args.get('search_isbn10'))
    else:
        results = []
    return render_template('search.html', search_results=results)

@app.route('/resource', methods=['POST', 'GET'], endpoint='resource')
@require_auth
def resource():
    if request.method == 'GET':
        return render_template('add_resource.html')
    elif request.method == 'POST':
        db.add_resource_to_inventory(
            request.form['title'],
            request.form['author_first'],
            request.form['author_middle'],
            request.form['author_last'],
            request.form['edition'],
            request.form['isbn_10'],
            request.form['isbn_13']
        )
        return render_template('added_successfully.html')
    

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




