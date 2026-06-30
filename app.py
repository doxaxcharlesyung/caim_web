from pathlib import Path

from flask import Flask, abort, send_from_directory
from werkzeug.exceptions import NotFound

app = Flask(__name__, static_folder=None)
ROOT = Path(__file__).resolve().parent

PAGE_MAP = {
    "/": "home.html",
    "/home.html": "home.html",
    "/zh/": "zh_home.html",
    "/zh_home.html": "zh_home.html",
    "/dx-sermon/": "dx_sermon.html",
    "/dx_sermon.html": "dx_sermon.html",
    "/zh/dx-sermon/": "zh_dx_sermon.html",
    "/zh_dx_sermon.html": "zh_dx_sermon.html",
    "/ai-courses/": "ai_courses.html",
    "/ai_courses.html": "ai_courses.html",
    "/zh/ai-courses/": "zh_ai_courses.html",
    "/zh_ai_courses.html": "zh_ai_courses.html",
    "/workshop/": "workshop.html",
    "/workshop.html": "workshop.html",
    "/zh/workshop/": "zh_workshop.html",
    "/zh_workshop.html": "zh_workshop.html",
    "/how-to-help/": "how_to_help.html",
    "/how_to_help.html": "how_to_help.html",
    "/zh/how-to-help/": "zh_how_to_help.html",
    "/zh_how_to_help.html": "zh_how_to_help.html",
    "/caim-2/": "home.html",
}


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_site(path: str):
    route = "/" if not path else f"/{path}"
    if route in PAGE_MAP:
        return send_from_directory(ROOT, PAGE_MAP[route])

    if route == "/site.css":
        return send_from_directory(ROOT, "site.css")

    if route.startswith("/assets/"):
        return send_from_directory(ROOT / "assets", route.removeprefix("/assets/"))

    if route.endswith("/"):
        candidate = route[:-1] + ".html"
        if candidate in PAGE_MAP:
            return send_from_directory(ROOT, PAGE_MAP[candidate])

    file_path = ROOT / route.lstrip("/")
    if file_path.exists() and file_path.is_file():
        return send_from_directory(ROOT, route.lstrip("/"))

    abort(404)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
