import flask
from flask import request, make_response, abort, Flask, session, redirect, url_for, render_template

from auth import require_auth
import db

db.prepare_db()



app = Flask(__name__)

# This app is just for testing. Never expose your secret in a production app!
app.secret_key = b'mysecretkey'

@require_auth
@app.route('/')
def index():
    return redirect(url_for('search'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'session_id' not in session:
        session['session_id'] = db.create_new_session()
    if request.method == 'POST':
        email_provided = request.form['email']

        if not db.password_matches(email_provided, request.form['password']):
            print("Login not valid")
            return render_template('login.html')

        member_id = db.get_member_by_email(email_provided)
        db.associate_session_with_user(session['session_id'], member_id, request.remote_addr, request.headers['User-Agent'])
        session['token'] = add_token()
        return render_template('search.html')

    else:
        return render_template('login.html')


@app.route('/join', methods=['POST', 'GET'])
def join():
    if 'session_id' in session and 'token' in session:
        if token_is_valid(session['session_id'], session['token']):
            print("Session alreadhy valid, redirecting to search")
            redirect(url_for('search'))
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

        member_id = db.add_new_member(request.form['email'], request.form['password'])
        if member_id == None:
            print("There was a problem creating user {}".format(request.form['email']))
            return render_template('join.html')
        db.associate_session_with_user(session['session_id'], member_id, request.remote_addr, request.headers['User-Agent'])
        token_id = db.add_token(session['session_id'])
        print("Token {} created successfully...".format(token_id))
        session['token'] = token_id
        return render_template('search.html')

@app.route('/search', methods=['GET'])
def search():
    if 'author' in request.args:
        results = db.search_by_author(request.args.get('author'))
    elif 'title' in request.args:
        results = db.search_by_title(request.args.get('title'))
    elif 'isbn10' in request.args:
        results = db.search_by_isbn10(request.args.get('isbn10'))
    else:
        results = []
    return render_template('search.html', search_results=results)

@app.route('/logout', methods=['GET'])
def logout():
    del session['token']
    del session['session_id']
    redirect(url_for('login'))



