from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta
import os

app = Flask(__name__)

# Fix the secret key - ensure it's properly set
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    # This is a fallback, but you should set SECRET_KEY in Railway environment variables
    SECRET_KEY = "your-fallback-secret-key-change-this-in-production"
app.secret_key = SECRET_KEY

# Database configuration for Railway Postgres
db_url = os.environ.get("DATABASE_URL")

# Handle the postgres:// to postgresql:// conversion for Heroku/Railway
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
else:
    # Fallback for local development
    db_url = "sqlite:///app.db"  # Use SQLite for local development

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    subscribed = db.Column(db.Boolean, default=False)
    subscription_expiry = db.Column(db.Date, nullable=True)

# Create tables at import (so it runs under Gunicorn on Railway)
with app.app_context():
    # Check if we're not using SQLite (i.e., we're in production)
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        db.create_all()
    else:
        # For SQLite, we can create all tables
        db.create_all()

# Helpers
def check_and_downgrade(user):
    if user.subscribed and user.subscription_expiry:
        if user.subscription_expiry < date.today():
            user.subscribed = False
            user.subscription_expiry = None
            db.session.commit()
            return False
    return True

# Routes
@app.route("/")
def home():
    # List of food options for the dropdowns
    foods = [
        "Chicken", "Fish", "Bread", "Eggs", "Sardines", 
        "Beans", "Tomatoes", "Beef", "Pork", "Rice", 
        "Salad", "Prawns"
    ]
    # Show your real UI
    return render_template("index.html", foods=foods)

@app.route("/signup", methods=["GET", "POST"])
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
        except Exception as e:
            db.session.rollback()  # Rollback the session on error
            flash("Username already exists.")
            return render_template("signup.html")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
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
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("login"))

@app.route("/upgrade", methods=["GET", "POST"])
def upgrade():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        expiry = date.today() + timedelta(days=30)
        user = db.session.get(User, session["user_id"])
        if user:
            user.subscribed = True
            user.subscription_expiry = expiry
            db.session.commit()
            session["subscribed"] = True
            session["subscription_expiry"] = str(expiry)
            flash("Pro subscription activated for 30 days!")
        return redirect(url_for("home"))
    return render_template("upgrade.html")

# New route to handle recipe search
@app.route("/recipes", methods=["POST"])
def find_recipes():
    first_food = request.form.get("first_food")
    second_food = request.form.get("second_food")
    
    if not first_food or not second_food:
        flash("Please select both foods.")
        return redirect(url_for("home"))
    
    # Here you would typically search your database for recipes
    # For now, we'll just pass the selected foods to a results template
    return render_template("recipes.html", 
                         first_food=first_food, 
                         second_food=second_food)

# Run locally (not used on Railway)
if __name__ == "__main__":
    # Get port from environment variable or default to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
