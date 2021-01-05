from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import random
import json

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///database.db")

@app.route("/")
def index():
    """Show portfolio of stocks"""

    if session.get("user_id") is None:
        return render_template("welcome.html");

    gates = db.execute("SELECT * FROM gates WHERE user_id = :id",
                        id = session["user_id"])

    for gate in gates:
        if gate['timestamp'] + 432000 > datetime.timestamp(datetime.now()):
            gate['status'] = "Available"
        else:
            gate['status'] = "Expired"

    return render_template("index.html", gates=gates, length = len(gates))


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Declaring variables
        pedido = request.form['list']
        url_list = json.loads(pedido)
        gate_id = '%016x' % random.randrange(16**16)

        print(url_list)

        db.execute("INSERT INTO gates (user_id, id, timestamp) VALUES (:user_id, :id, :timestamp)",
                   user_id=session["user_id"], id=gate_id,
                   timestamp=datetime.timestamp(datetime.now()))

        for url in url_list:
            db.execute("INSERT INTO links (url, gate_id) VALUES (:url, :gate_id)",
                       url=url, gate_id=gate_id,)

        return jsonify(dict(redirect='/'))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("create.html")

@app.route("/history")
@login_required
def view():
    """Show history of transactions"""

    transactions = db.execute("SELECT * FROM transactions WHERE user_id = :id",
                               id = session["user_id"])

    for transaction in transactions:
        transaction['price'] = usd(transaction['price'])
        transaction['timestamp'] = datetime.fromtimestamp(transaction['timestamp'])

    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/g", methods=["GET"])
def redirection():
    """Get stock quote."""
    id = request.args.get('i')

    urls = [url['url']
            for url in db.execute("SELECT url FROM links WHERE gate_id = :id", id=id)]

    destination = random.choice(urls)
    print(destination)

    return redirect(destination)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password and confirmation are equal
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords don't match", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username is available
        if len(rows) != 0:
            return apology("username already taken", 403)

        # Add user to database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                   username = request.form.get("username"), hash = generate_password_hash(request.form.get("password")))

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)