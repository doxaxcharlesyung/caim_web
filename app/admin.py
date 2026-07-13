import secrets
from functools import wraps

from flask import g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import fetch_all, fetch_one, get_db


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("admin_user_id")
        user = fetch_one("SELECT id, username, is_active FROM admin_users WHERE id=%s", (user_id,)) if user_id else None
        if not user or not user["is_active"]:
            session.clear()
            return redirect(url_for("public.article_dashboard_login", next=request.full_path))
        g.admin_user = user
        return view(*args, **kwargs)
    return wrapped


def authenticate(username, password):
    user = fetch_one("SELECT * FROM admin_users WHERE username=%s AND is_active=1", (username,))
    return user if user and check_password_hash(user["password_hash"], password) else None


def get_admin_users():
    return fetch_all("SELECT id, username, is_active, created_at FROM admin_users ORDER BY username")


def create_admin_user(username, password):
    with get_db().cursor() as cursor:
        cursor.execute("INSERT INTO admin_users (username,password_hash) VALUES (%s,%s)", (username, generate_password_hash(password)))


def update_admin_user(user_id, action, password=""):
    with get_db().cursor() as cursor:
        if action == "password":
            cursor.execute("UPDATE admin_users SET password_hash=%s WHERE id=%s", (generate_password_hash(password), user_id))
        elif action == "toggle":
            cursor.execute("UPDATE admin_users SET is_active=NOT is_active WHERE id=%s", (user_id,))


def login_csrf_token():
    if "login_csrf" not in session:
        session["login_csrf"] = secrets.token_urlsafe(24)
    return session["login_csrf"]
