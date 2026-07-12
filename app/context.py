from datetime import UTC, datetime

from flask import Flask, g

from .data import NAVIGATION, SITE


def register_context(app: Flask) -> None:
    @app.context_processor
    def shared_template_context() -> dict:
        return {
            "current_year": datetime.now(UTC).year,
            "locale": getattr(g, "locale", app.config["DEFAULT_LOCALE"]),
            "navigation": NAVIGATION,
            "site": SITE,
        }
