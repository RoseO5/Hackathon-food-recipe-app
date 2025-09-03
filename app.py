from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_secret")

# ---- Database (Railway Postgres) ----
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---- Models ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # NOTE: plain text (simplest); use hashing later
    subscribed = db.Column(db.Boolean, default=False)
    subscription_expiry = db.Column(db.Date, nullable=True)

# Create tables at import (so it runs under Gunicorn on Railway)
with app.app_context():
    db.create_all()

# ---- Helpers ----
def check_and_downgrade(user: User):
    if user.subscribed and user.subscription_expiry:
        if user.subscription_expiry < date.today():
            user.subscribed = False
            user.subscription_expiry = None
            db.session.commit()
            return False
        return True
    return False

# ---- Routes ----
@app.route("/")
def home():
    # Show your real UI
    return render_template("index.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        if not username or not password:
            flash("All fields are required.")
            return redirect(url_for("signup"))
        try:
            db.session.add(User(username=username, password=password))
            db.session.commit()
            flash("Sign up successful! Please log in.")
            return redirect(url_for("login"))
        except Exception:
            flash("Username already exists.")
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            subscribed = check_and_downgrade(user)
            session["user_id"] = user.id
            session["username"] = user.username
            session["subscribed"] = subscribed
            session["subscription_expiry"] = (
                str(user.subscription_expiry) if user.subscription_expiry else None
            )
            flash(f"Welcome {username}!")
            return redirect(url_for("home"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("login"))

@app.route("/upgrade", methods=["GET","POST"])
def upgrade():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        expiry = date.today() + timedelta(days=30)
        user = db.session.get(User, session["user_id"])
        user.subscribed = True
        user.subscription_expiry = expiry
        db.session.commit()
        session["subscribed"] = True
        session["subscription_expiry"] = str(expiry)
        flash("Pro subscription activated for 30 days!")
        return redirect(url_for("home"))
    return render_template("upgrade.html")

# ---- Run locally (not used on Railway) ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
