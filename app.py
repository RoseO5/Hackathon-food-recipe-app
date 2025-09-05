from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

# ---- Database (Railway Postgres) ----
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    # Railway sometimes gives "postgres://", but SQLAlchemy needs "postgresql://"
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---- Models ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)

# ---- Routes ----
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add_user", methods=["POST"])
def add_user():
    username = request.form.get("username")
    if username:
        new_user = User(username=username)
        db.session.add(new_user)
        db.session.commit()
        flash("User added successfully!", "success")
    else:
        flash("Username cannot be empty", "error")
    return redirect(url_for("home"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(host="0.0.0.0", port=5000)
