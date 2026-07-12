from flask import Blueprint, abort, current_app, g, render_template

from .data import PAGE_META

public = Blueprint("public", __name__)


@public.before_request
def select_locale() -> None:
    # The route architecture is locale-ready; only Traditional Chinese is enabled in this migration.
    g.locale = current_app.config["DEFAULT_LOCALE"]


def page(template: str, key: str, **context):
    title, description = PAGE_META[key]
    return render_template(template, page_title=title, description=description, **context)


@public.get("/")
def home():
    return page("pages/home.html", "home")


@public.get("/about/")
def about():
    return page("pages/about.html", "about")


@public.get("/services/")
def services():
    return page("pages/services.html", "services")


@public.get("/dx-sermon/")
def dx_sermon():
    return page("pages/dx_sermon.html", "dx_sermon")


@public.get("/dx-sermon/pricing/")
def dx_pricing():
    return page("pages/dx_pricing.html", "dx_pricing")


@public.get("/missionaries/")
def missionaries():
    return page("pages/missionaries.html", "missionaries")


@public.get("/church-ai-transformation/")
def church_ai_transformation():
    return page("pages/church_ai_transformation.html", "church_ai_transformation")


@public.get("/courses/")
def courses():
    return page("pages/courses.html", "courses")


@public.get("/courses/<slug>/")
def course_detail(slug: str):
    return page("pages/course_detail.html", "courses", slug=slug)


@public.route("/course-registration/", methods=["GET", "POST"])
def course_registration():
    return page("pages/course_registration.html", "course_registration")


@public.get("/articles/")
def articles():
    return page("articles/index.html", "articles")


@public.get("/articles/published/")
def published_articles():
    return page("articles/published.html", "articles")


@public.get("/articles/<slug>/")
def article_detail(slug: str):
    # A database-backed article service will replace this placeholder in the approved DB phase.
    return page("articles/detail.html", "articles", slug=slug)


@public.get("/contact/")
def contact():
    return page("pages/contact.html", "contact")


@public.app_errorhandler(404)
def not_found(_error):
    return render_template("pages/404.html", page_title="找不到頁面｜CAIM"), 404
