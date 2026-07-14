import os
from datetime import timedelta

from flask import Flask
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

from .context import register_context
from .content_manager import content_admin
from .db import close_db
from .i18n import ENABLED_LOCALES, SUPPORTED_LOCALES
from .routes import public


def create_app(config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "development-only-key"),
        DEFAULT_LOCALE="zh-Hant",
        SUPPORTED_LOCALES=SUPPORTED_LOCALES,
        ENABLED_LOCALES=ENABLED_LOCALES,
        DB_HOST=os.getenv("DB_HOST", "127.0.0.1"),
        DB_PORT=int(os.getenv("DB_PORT", "3306")),
        DB_USER=os.getenv("DB_USER", "caimadmin"),
        DB_PASSWORD=os.getenv("DB_PASSWORD", ""),
        DB_NAME=os.getenv("DB_NAME", "caimdb"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
        SESSION_COOKIE_NAME="caim_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("APP_ENV") == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
        SESSION_REFRESH_EACH_REQUEST=True,
        SESSION_EPOCH=os.getenv("INVOCATION_ID", f"gunicorn-parent-{os.getppid()}"),
        SESSION_IDLE_SECONDS=3600,
    )
    if config:
        app.config.update(config)

    app.register_blueprint(public)
    app.register_blueprint(content_admin)
    app.teardown_appcontext(close_db)
    register_context(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    return app
