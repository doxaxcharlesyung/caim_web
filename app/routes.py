from flask import Blueprint, abort, current_app, g, render_template, request

from .crm import submit_consultation_request
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


@public.route("/contact/", methods=["GET", "POST"])
def contact():
    contact_notice = ""
    contact_error = ""
    if request.method == "POST":
        form = request.form
        name_parts = form.get("name", "").strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else "-"
        message = form.get("message", "").strip()
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": form.get("email", "").strip(),
            "phone": form.get("phone", "").strip(),
            "company_name": form.get("organization", "").strip(),
            "message": f"查詢類別：{form.get('type', '一般查詢').strip()}\n\n{message}",
        }
        if not first_name or not payload["email"] or not message:
            contact_error = "請填寫姓名、電郵及訊息內容。"
        else:
            submitted, error_message = submit_consultation_request(payload)
            if submitted:
                contact_notice = "查詢已成功送出，CAIM 團隊將與你聯絡。"
            else:
                contact_error = error_message
    return page("pages/contact.html", "contact", contact_notice=contact_notice, contact_error=contact_error)


@public.app_errorhandler(404)
def not_found(_error):
    return render_template("pages/404.html", page_title="找不到頁面｜CAIM"), 404
