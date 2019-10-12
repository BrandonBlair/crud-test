from datetime import datetime
from uuid import uuid4
import sqlite3
from sqlite3 import connect as sqlite_connect

SCHEMA = "library"
DB_NAME = "{}.db".format(SCHEMA)
TOKEN_TTL_SECS = 120
RESOURCE_CHECKOUT_LIMIT = 3

class CheckoutException(Exception):
    pass


class CheckinException(Exception):
    pass


class InvalidEmailException(Exception):
    pass


class NoMemberFoundException(Exception):
    pass

class MultipleAuthorsMatchedException(Exception):
    pass


# SQLite3
def get_sqlite3_conx(db_name):
    """Get SQLite3 connection for communicating with the local DB"""
    conn = sqlite_connect(db_name, check_same_thread=False)  # Allows multithread access
    return conn


def query_result(cxn, qry, args=None, single_row=False, all_fields=True, empty_results=False):
    """Executes a READ-only query against the database (does not COMMIT changes).
    Args:
        cxn (DB-API 2.0 compliant DB connection)
        qry (str): Valid SQL query
        args (dict): (MySQL) Map of names to interpolated values to be substituted during query
             (list): (SQLite3) collection of values to be interpolated into query
        single_row (bool): Whether or not to limit results to the first row
        all_fields (bool): Whether or not to include all fields or only the first
        empty_results (bool): Whether or not empty results are acceptable (raises Exception if not)
    Returns:
        result (list) if all_fields is True
        result (str) if all_fields is False
    """
    args = args or []
    curs = cxn.cursor()
    curs.execute(qry, args)
    if single_row:
        result = curs.fetchone()
    else:
        result = curs.fetchall()
    if not result and not empty_results:
        raise Exception("Query results were empty, but empty results are not allowed")
    if not result:
        return []
    else:
        return result if all_fields else result[0]

def update_db(cxn, qry, args=None):
    """Executes a WRITE query against the database, including a COMMIT.
    Args:
        cxn (DB-API 2.0 compliant DB connection)
        qry (str): Valid SQL query
        args (dict): (MySQL) Map of names to interpolated values to be substituted during query
             (list): (SQLite3) collection of values to be interpolated into query
    Returns:
        last_row_id (cursor.lastrowid): ID of row just inserted
    """
    args = args or []
    curs = cxn.cursor()
    try:
        curs.execute(qry, args)
        cxn.commit()
        return curs.lastrowid
    except Exception as e:
        raise Exception('Update was unsuccessful') from e


def prepare_db():
    conx = get_sqlite3_conx(DB_NAME)
    create_db_tables(conx)
    #clear_db_data(conx)


def clear_db_data(conx):
    cursor = conx.cursor()
    cursor.execute("DELETE FROM member")
    cursor.execute("DELETE FROM token")
    cursor.execute("DELETE FROM resource")
    cursor.execute("DELETE FROM stock")
    cursor.execute("DELETE FROM borrow")
    conx.commit()


def create_db_tables(conx):
    cursor = conx.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS member(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT, checked_out INTEGER DEFAULT 0, total_borrowed INTEGER DEFAULT 0, date_joined TEXT DEFAULT CURRENT_DATE, active INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS token(id TEXT PRIMARY KEY, session_id INTEGER, time_created TEXT DEFAULT CURRENT_TIMESTAMP, active INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS resource(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, author_id INTEGER, edition TEXT, isbn_10 TEXT, isbn_13 TEXT, date_added TEXT DEFAULT CURRENT_DATE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id INTEGER, date_added TEXT DEFAULT CURRENT_DATE, active INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS borrow(id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, stock_id INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP, closed INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS session(id TEXT PRIMARY KEY, member_id INTEGER, ip_address TEXT, user_agent TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS author(id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, middle_name TEXT, last_name TEXT)")  # How do we handle authors with the same name?

def token_is_valid(session_id, token):
    conx = get_sqlite3_conx(DB_NAME)
    token_data = query_result(
        conx,
        "SELECT id, time_created FROM token WHERE session_id=? AND active=1",
        [session_id],
        single_row=True,
        all_fields=True,
        empty_results=True
    )
    if not token_data:
        print("No active tokens")
        # There are no active tokens
        return False

    current_token, time_created = token_data

    # Does the token match?
    if token != current_token:
        print("token {} != {}", token, current_token)
        return False

    # Has the TTL expired?
    token_created_dt = datetime.strptime(time_created, "%Y-%m-%d %X")
    current_time = datetime.now()
    secs_token_active = (current_time - token_created_dt).total_seconds()

    if secs_token_active > TOKEN_TTL_SECS:
        return False

    return True


def generate_new_token():
    return str(uuid4())


def password_matches(email, password_provided):
    conx = get_sqlite3_conx(DB_NAME)
    password_db = query_result(
        conx,
        "SELECT password FROM member WHERE email=?",
        [email],
        single_row=True,
        all_fields=False,
        empty_results=True
    )
    return password_provided == password_db


def create_new_session():
    session_id = str(uuid4())
    conx = get_sqlite3_conx(DB_NAME)
    update_db(
        conx,
        "INSERT INTO session(id) VALUES(?)",
        [session_id]
    )
    return session_id


def associate_session_with_user(session_id, member_id, ip_address, user_agent):
    conx = get_sqlite3_conx(DB_NAME)
    update_db(
        conx,
        "UPDATE session SET member_id=?, ip_address=?, user_agent=? WHERE id=?",
        [member_id, ip_address, user_agent, session_id]
    )
    return None


def get_member_by_email(email):
    conx = get_sqlite3_conx(DB_NAME)
    member = query_result(
        conx,
        "SELECT id FROM member WHERE email=?",
        [email],
        single_row=True,
        all_fields=False,
        empty_results=True
    )
    return member


def get_member_by_session(session_id):
    conx = get_sqlite3_conx(DB_NAME)
    member = query_result(
        conx,
        "SELECT member_id FROM session WHERE id=?",
        [session_id],
        single_row=True,
        all_fields=False,
        empty_results=True
    )
    return member


def add_new_member(email, password):
    conx = get_sqlite3_conx(DB_NAME)

    email = email.lower()
    existing_member = get_member_by_email(email)

    if existing_member:
        raise InvalidEmailException("We cannot create a member with this email at this time")

    member_id = update_db(
        conx,
        "INSERT INTO member(email, password) VALUES(?, ?)",
        [email, password]
    )
    return member_id


def deactivate_member(member_id):
    conx = get_sqlite3_conx(DB_NAME)

    deactivate_tokens(member_id)
    return update_db(conx, "UPDATE member SET active=0 WHERE id=?", [member_id])

def get_author_by_name(first=None, middle=None, last=None):
    if not first and not middle and not last:
        raise Exception("Must provide first, middle, or last name to retrieve author")

    conx = get_sqlite3_conx(DB_NAME)

    qry = "SELECT id FROM author WHERE first_name=? AND middle_name=? and last_name=?"
    authors = query_result(
        conx,
        qry,
        [first, middle, last],
        single_row=False,
        all_fields=True,
        empty_results=True
    )

    authors_found_total = len(authors)
    if authors_found_total > 1:
        raise MultipleAuthorsMatchedException(
    '       Found {} authors with name {} {} {}'.format(
                authors_found_total,
                first,
                middle,
                last
            )
        )
    return authors[0]


def add_token(session_id):
    conx = get_sqlite3_conx(DB_NAME)
    member_id = get_member_by_session(session_id)

    if not member_id:
        print("Found no member for session {}".format(session_id))
        raise NoMemberFoundException()

    # Invalidate old tokens
    deactivate_tokens(member_id)

    new_token = generate_new_token()
    token_id = update_db(
        conx,
        "INSERT INTO token(id, session_id) VALUES(?, ?)",
        [new_token, session_id]
    )
    return new_token


def deactivate_tokens(member_id):
    conx = get_sqlite3_conx(DB_NAME)
    sessions = query_result(
        conx,
        "SELECT id from session WHERE member_id=?",
        [member_id],
        single_row=False,
        all_fields=False
    )
    sessions_str = "', '".join(sessions)
    sessions_str = "'{}'".format(sessions_str)
    update_db(
        conx,
        "UPDATE token set active=0 WHERE session_id in ({})".format(sessions_str)
    )
    return None


def add_borrow(member_id, stock_id):
    conx = get_sqlite3_conx(DB_NAME)
    borrow_id = update_db(
        conx,
        "INSERT INTO borrow(member_id, stock_id) VALUES(?, ?)",
        [member_id, stock_id]
    )
    return borrow_id


def add_resource(title, author_first, author_middle, author_last, edition, isbn10, isbn13):
    conx = get_sqlite3_conx(DB_NAME)

    author_id, author_first, author_middle, author_last = get_author_by_name(author_first, author_middle, author_last)
    print("Found author {} with ID {}".format(author_last, author_id))
    if not author_id:
        print("Author {author_first} {author_middle} {author_last} did not exist in the system. Adding...")
        author_id = add_author(author_first, author_middle, author_last)

    resource_id = update_db(
        conx,
        "INSERT INTO resource(title, author_id, edition, isbn_10, isbn_13) VALUES(?, ?, ?, ?, ?)",
        [title, author_id, edition, isbn10, isbn13]
    )
    return resource_id


def deactivate_resource(resource_id):
    conx = get_sqlite3_conx(DB_NAME)
    update_db(
        conx,
        "UPDATE resource set active=0 WHERE id=?",
        [resource_id]
    )

def add_author(first, middle, last):
    conx = get_sqlite3_conx(DB_NAME)
    author_id = update_db(
        conx,
        "INSERT INTO author(first_name, middle_name, last_name) VALUES(?, ?, ?)",
        [first, middle, last]
    )
    return author_id


def add_stock(resource_id):
    conx = get_sqlite3_conx(DB_NAME)
    stock_id = update_db(conx, "INSERT INTO stock(resource_id) VALUES(?)", [resource_id])
    return stock_id

def add_resource_to_inventory(title, author_first, author_middle, author_last, isbn10, isbn13):
    conx = get_sqlite3_conx(DB_NAME)

    # Has this resource already been added?
    existing_resource = query_result(
        conx,
        "SELECT * FROM resource WHERE isbn_10 = ?",
        [isbn10],
        single_row=True,
        all_fields=True
    )
    resource_id = None
    if existing_resource:
        resource_id = existing_resource[0]
        # Add another stock for the resource
        add_stock(resource_id)
    else:
        resource_id = add_resource(title, author_first, author_middle, author_last, isbn10, isbn13)
    return resource_id


def search_resources_by_author(author):
    conx = get_sqlite3_conx(DB_NAME)
    resources = query_result(
        conx,
        "SELECT * FROM resource WHERE author like '%{}%'".format(author),
        [],
        single_row=False,
        all_fields=True,
        empty_results=True
    )
    print(resources)

    return resources


def search_resources_by_title(title):
    conx = get_sqlite3_conx(DB_NAME)
    resources = query_result(
        conx,
        "SELECT * FROM resource WHERE title like '{}%'".format(title),
        [],
        single_row=False,
        all_fields=True,
        empty_results=True
    )

    return resources


def search_resources_by_isbn10(isbn10):
    conx = get_sqlite3_conx(DB_NAME)
    resources = query_result(
        conx,
        "SELECT * FROM resource WHERE isbn_10 like '{}%'".format(isbn10),
        [],
        single_row=False,
        all_fields=True,
        empty_results=True
    )

    return resources

def check_in_resource(member_id, stock_id):
    conx = get_sqlite3_conx(DB_NAME)
    stock_data = query_result(
        conx,
        "SELECT * FROM stock WHERE id=?",
        [stock_id],
        single_row=True,
        all_fields=True
    )
    if not stock_data:
        raise CheckinException("Stock {} not found in system".format(stock_id))
    stock_id, resource_id, date_added, active = stock_data

    resource = query_result(
        conx,
        "SELECT * FROM resource WHERE id=?",
        [resource_id],
        single_row=True,
        all_fields=True
    )
    if not resource:
        raise CheckinException("Resource {} not found in system".format(resource))

    resource_id, title, author, date_added, isbn_10, isbn_13 = resource
    borrow_id = query_result(
        conx,
        "SELECT id FROM borrow WHERE member_id=? AND stock_id=? AND closed=0",
        [member_id, stock_id],
        single_row=True,
        all_fields=False
    )
    update_db(conx, "UPDATE borrow SET closed=1 WHERE id=?", [borrow_id])
    return None


def checkout_resource(member_id, stock_id):
    conx = get_sqlite3_conx(DB_NAME)
    member_data = query_result(
        conx,
        "SELECT * FROM member WHERE id=?",
        [member_id],
        single_row=True,
        all_fields=True
    )

    stock_data = query_result(conx, GET_STOCK_SQL, [stock_id], single_row=True, all_fields=True)
    stock_id, resource_id, date_added, active = stock_data

    resource = query_result(
        conx,
        "SELECT * FROM resource WHERE id=?",
        [resource_id],
        single_row=True,
        all_fields=True
    )
    resource_id, title, author, date_added, isbn_10, isbn_13 = resource

    if not active:
        raise CheckoutException("Stock item {} '{}' is not active".format(stock_id, title))

    member_id, member_email, member_password, member_checked_out, member_total_borrowed, member_joined, member_active = member_data
    if not member_active:
        raise CheckoutException("Member {} is not active".format(member_id))

    if member_total_borrowed >= RESOURCE_CHECKOUT_LIMIT:
        raise CheckoutException("Member is limited to {} items borrowed at one time".format(RESOURCE_CHECKOUT_LIMIT))

    # Add borrow
    borrow_id = add_borrow(member_id, stock_id)

    return borrow_id
