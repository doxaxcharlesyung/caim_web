import secrets
import time
from functools import wraps

from flask import current_app, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import fetch_all, fetch_one, get_db


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("admin_user_id")
        now = time.time()
        epoch_matches = session.get("session_epoch") == current_app.config["SESSION_EPOCH"]
        last_activity = float(session.get("last_activity", 0) or 0)
        active = epoch_matches and now - last_activity <= current_app.config["SESSION_IDLE_SECONDS"]
        user = fetch_one("SELECT id, username, is_active, is_reviewer FROM admin_users WHERE id=%s", (user_id,)) if user_id and active else None
        if not user or not user["is_active"]:
            session.clear()
            # The login endpoint always returns to the dashboard. Avoid carrying
            # request.full_path, which can include a trailing bare '?'.
            return redirect(url_for("content_admin.content_manager"))
        g.admin_user = user
        session["last_activity"] = now
        session.permanent = True
        return view(*args, **kwargs)
    return wrapped


def authenticate(username, password):
    user = fetch_one("SELECT * FROM admin_users WHERE username=%s AND is_active=1", (username,))
    return user if user and check_password_hash(user["password_hash"], password) else None


def get_admin_users():
    return fetch_all("SELECT id, username, is_active, is_reviewer, created_at FROM admin_users ORDER BY username")


def create_admin_user(username, password):
    with get_db().cursor() as cursor:
        cursor.execute("INSERT INTO admin_users (username,password_hash) VALUES (%s,%s)", (username, generate_password_hash(password)))


def update_admin_user(user_id, action, password=""):
    with get_db().cursor() as cursor:
        if action == "password":
            cursor.execute("UPDATE admin_users SET password_hash=%s WHERE id=%s", (generate_password_hash(password), user_id))
        elif action == "toggle":
            cursor.execute("UPDATE admin_users SET is_active=NOT is_active WHERE id=%s", (user_id,))
        elif action == "reviewer":
            cursor.execute("UPDATE admin_users SET is_reviewer=NOT is_reviewer WHERE id=%s", (user_id,))


def login_csrf_token():
    if "login_csrf" not in session:
        session["login_csrf"] = secrets.token_urlsafe(24)
    return session["login_csrf"]
