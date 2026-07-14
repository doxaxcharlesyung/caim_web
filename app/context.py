from datetime import UTC, datetime

from flask import Flask, g

from .data import NAVIGATION, SITE
from .i18n import LANGUAGE_NAMES, language_url, select_locale, translate


def register_context(app: Flask) -> None:
    app.before_request(select_locale)

    @app.context_processor
    def shared_template_context() -> dict:
        return {
            "current_year": datetime.now(UTC).year,
            "locale": getattr(g, "locale", app.config["DEFAULT_LOCALE"]),
            "navigation": NAVIGATION,
            "site": SITE,
            "supported_locales": app.config["ENABLED_LOCALES"],
            "language_names": LANGUAGE_NAMES,
            "language_url": language_url,
            "t": translate,
        }
