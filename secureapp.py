import os
import re
import sqlite3
import bcrypt

from flask import Flask, request, jsonify, session
from functools import wraps

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)

DB_PATH = os.environ.get("DB_PATH", "users.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def valid_username(username):
    return (
        isinstance(username, str)
        and 3 <= len(username) <= 50
        and re.fullmatch(r"[A-Za-z0-9_.-]+", username)
    )


def get_current_user():
    username = session.get("username")
    if not username:
        return None

    with get_db_connection() as conn:
        return conn.execute(
            "SELECT username, role FROM users WHERE username = ?",
            (username,)
        ).fetchone()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()

            if not user or user["role"] not in roles:
                return jsonify({"error": "Forbidden"}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not valid_username(username):
        return jsonify({"error": "Invalid username"}), 400

    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (username, password, role, email)
                VALUES (?, ?, ?, ?)
                """,
                (username, hashed, "user", email)
            )
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409

    return jsonify({"message": "User registered"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT username, password, role FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if user and bcrypt.checkpw(
        password.encode("utf-8"),
        user["password"]
    ):
        session.clear()
        session["username"] = user["username"]
        return jsonify({"message": "Login successful"})

    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/user/<username>", methods=["GET"])
@login_required
def get_user(username):
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    if current_user["username"] != username and current_user["role"] != "admin":
        return jsonify({"error": "Forbidden"}), 403

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT username, role, email FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if user:
        return jsonify(dict(user))

    return jsonify({"error": "User not found"}), 404


@app.route("/admin", methods=["GET"])
@roles_required("admin")
def admin_panel():
    return jsonify({"data": "Sensitive admin data"})


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)