from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import date, timedelta, datetime

app = Flask(__name__)
app.secret_key = "change_this_secret"

# MySQL config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_MYSQL_PASSWORD",
    "database": "food_app"
}

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def check_and_downgrade(user_id):
    """Check subscription expiry and downgrade if expired"""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT subscribed, subscription_expiry FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    result = False
    if user and user["subscribed"]:
        expiry = user["subscription_expiry"]
        if expiry:
            if isinstance(expiry, str):
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            else:
                expiry_date = expiry
            if expiry_date < date.today():
                cur.execute("UPDATE users SET subscribed=FALSE, subscription_expiry=NULL WHERE id=%s", (user_id,))
                conn.commit()
                result = False
            else:
                result = True
    conn.close()
    return result

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s,%s)", (username, password))
            conn.commit()
            flash("Sign up successful! Please log in.")
            return redirect(url_for("login"))
        except mysql.connector.Error:
            flash("Username already exists.")
        finally:
            cur.close()
            conn.close()
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            # check expiry
            subscribed = check_and_downgrade(user["id"])
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["subscribed"] = subscribed
            session["subscription_expiry"] = str(user["subscription_expiry"]) if user["subscription_expiry"] else None
            flash(f"Welcome {username}!")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("login"))

@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    status = "Pro" if session.get("subscribed") else "Free"
    expiry = session.get("subscription_expiry", "N/A")
    return f"<h1>Welcome {session['username']}! Status: {status} (expires: {expiry})</h1>" \
           f"<p><a href='/upgrade'>Upgrade to Pro</a> | <a href='/logout'>Logout</a></p>"

@app.route("/upgrade", methods=["GET","POST"])
def upgrade():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        expiry = date.today() + timedelta(days=30)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET subscribed=TRUE, subscription_expiry=%s WHERE id=%s", (expiry, session["user_id"]))
        conn.commit()
        cur.close()
        conn.close()
        session["subscribed"] = True
        session["subscription_expiry"] = str(expiry)
        flash("Pro subscription activated for 30 days!")
        return redirect(url_for("home"))
    return render_template("upgrade.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
@app.route("/search", methods=["GET","POST"])
def search():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        food1 = request.form.get("food1")
        food2 = request.form.get("food2")

        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM recipes WHERE (food1=%s AND food2=%s) OR (food1=%s AND food2=%s)",
                    (food1, food2, food2, food1))
        recipes = cur.fetchall()
        cur.close()
        conn.close()

        # Free user sees only 1 recipe
        if not session.get("subscribed"):
            recipes = recipes[:1]

        return render_template("recipes.html", recipes=recipes, food1=food1, food2=food2, subscribed=session.get("subscribed"))

    # If GET request, show selection form
    return render_template("index.html")
