import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .context import register_context
from .routes import public


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "development-only-key"),
        DEFAULT_LOCALE="zh-Hant",
        SUPPORTED_LOCALES=("zh-Hant",),
    )
    if config:
        app.config.update(config)

    app.register_blueprint(public)
    register_context(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    return app
