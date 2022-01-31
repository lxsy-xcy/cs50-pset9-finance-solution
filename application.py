import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    userinformations=db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])
    theuser = userinformations[0]
    bought = db.execute("SELECT user_id,SUM(shares),symbol FROM buy WHERE user_id = ? GROUP BY symbol",session["user_id"])

    sumbuy = 0
    for row in bought:
        sumbuy+=row["SUM(shares)"]*lookup(row["symbol"])["price"]
        infor=lookup(row["symbol"])
        row["cominfor"]=infor
        row['total']=usd(infor['price']*row['SUM(shares)'])
        row["cominfor"]["price"]=usd(row["cominfor"]["price"])

    total =  sumbuy + theuser["cash"]

    return render_template("index.html",bought = bought,curcash = usd(theuser["cash"]),total = usd(total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    else:
        symboll = request.form.get("symbol")
        sharess = request.form.get("shares")

        for i in sharess:
            if i not in ['0','1','2','3','4','5','6','7','8','9','.']:
                return apology("invalid shares",400)

        if float(sharess) != int(float(sharess)):
            return apology("invalid shares",400)

        sharess = int(float(sharess))

        information = lookup(symboll)

        userinformation = db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])

        if not symboll or not information:
            return apology("cannot find the symbol",400)

        moneycost = sharess*information["price"]

        if sharess <=0:
            return apology("you must input a positive number",400)
        if moneycost>userinformation[0]["cash"]:
            return apology("you do not have enough money!",400)

        db.execute("INSERT INTO buy(user_id,symbol,shares) VALUES(?,?,?)",session["user_id"],symboll,sharess)

        db.execute("UPDATE users SET cash = ? WHERE id = ?",userinformation[0]["cash"]-moneycost,session["user_id"])

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transaction = db.execute("SELECT * FROM buy")
    for row in transaction:
        if row["shares"]>0:
            row["action"]="buy"
        else:
            row["action"]="sell"
            row["shares"]=-row["shares"]
    return render_template("history.html",transaction = transaction)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == 'POST':
        symboll = request.form.get("symbol")
        ans = lookup(symboll)

        if not symboll or not ans:
            return apology("cannot find the symbol",400)

        ans["price"]=usd(ans['price'])
        return render_template("quoted.html",ans = ans)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

    if request.method == "POST":

        usernamee = request.form.get("username")
        passwordd = request.form.get("password")
        confirmationn = request.form.get("confirmation")

        if not usernamee:
            return apology("must provide username", 400)

        alluser = db.execute("SELECT username FROM users ");
        users = []

        for row in alluser:
            users.append(row["username"])

        if usernamee in users:
            return apology("someone has already use this username",400)

        if not passwordd or not confirmationn or passwordd!=confirmationn:
            return apology("password error",400)

        hashpassword = generate_password_hash(passwordd)

        db.execute("INSERT INTO users(username,hash) VALUES(?,?)",usernamee,hashpassword)

        return redirect("/login")
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        return render_template("sell.html")
    else:
        symboll = request.form.get("symbol")
        sharess = int(request.form.get("shares"))
        information = lookup(symboll)

        userinformation = db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])
        own = db.execute("SELECT symbol FROM buy WHERE user_id = ?",session["user_id"])
        userownsymbols =[]
        for row in own:
            userownsymbols.append(row["symbol"])

        if not symboll or not information or symboll not in userownsymbols:
            return apology("cannot find the symbol",400)

        moneyget = sharess*information["price"]
        userownshares = db.execute("SELECT SUM(shares) FROM buy WHERE user_id = ? AND symbol = ? GROUP BY symbol",session["user_id"],symboll)

        if sharess <=0 or sharess>userownshares[0]["SUM(shares)"]:
            return apology("share number error",400)

        db.execute("INSERT INTO buy(user_id,symbol,shares) VALUES(?,?,?)",session["user_id"],symboll,-sharess)

        db.execute("UPDATE users SET cash = ? WHERE id = ?",userinformation[0]["cash"]+moneyget,session["user_id"])

        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)