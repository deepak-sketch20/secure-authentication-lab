import os
import re
import sqlite3
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

limiter = Limiter(key_func=get_remote_address, default_limits=[])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
PASSWORD_MIN_LENGTH = 10


def get_db():
    if "db" not in g:
        db_path = current_app_config_path()
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def current_app_config_path():
    return g._database_path


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL
            )
        """)
        db.commit()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret"),
        DATABASE=os.environ.get("DATABASE_PATH", str(Path(app.instance_path) / "auth.sqlite3")),
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=20),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=16 * 1024,
        RATELIMIT_STORAGE_URI=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_db(app)
    limiter.init_app(app)

    @app.before_request
    def attach_database_path():
        g._database_path = app.config["DATABASE"]

    app.teardown_appcontext(close_db)

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login"))
            user = get_db().execute(
                "SELECT id, username FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if user is None:
                session.clear()
                flash("Your session is no longer valid. Please sign in again.", "error")
                return redirect(url_for("login"))
            g.current_user = user
            return view(*args, **kwargs)
        return wrapped

    @app.get("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    @limiter.limit("5 per hour")
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not USERNAME_RE.fullmatch(username):
                flash("Use a username with 3–30 letters, numbers, dots, underscores or hyphens.", "error")
                return render_template("register.html"), 400
            if len(password) < PASSWORD_MIN_LENGTH or len(password) > 128:
                flash("Password must be between 10 and 128 characters.", "error")
                return render_template("register.html"), 400
            password_hash = generate_password_hash(password, method="scrypt")
            try:
                get_db().execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
                get_db().commit()
            except sqlite3.IntegrityError:
                # Avoid disclosing whether an account exists.
                flash("Unable to create this account with the supplied details.", "error")
                return render_template("register.html"), 400
            flash("Account created. You can now sign in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("5 per minute")
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            # Same outward error for unknown username and incorrect password.
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid username or password.", "error")
                return render_template("login.html"), 401
            session.clear()  # Prevent session fixation.
            session.permanent = True
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", username=g.current_user["username"])

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))

    @app.errorhandler(429)
    def rate_limit_exceeded(_error):
        return render_template("message.html",
                               title="Please slow down",
                               message="Too many attempts. Wait a while before trying again."), 429

    return app


app = create_app()

if __name__ == "__main__":
    # Local development only. Use a production WSGI server for deployment.
    app.run(host="127.0.0.1", port=5000, debug=False)
