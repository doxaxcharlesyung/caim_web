import math

import pymysql
from flask import Blueprint, abort, current_app, g, redirect, render_template, request, session, url_for

from .crm import submit_consultation_request
from .content import (
    get_article,
    get_articles,
    get_collection,
    get_course,
    get_courses,
    get_page,
    get_news_items,
    get_studio_article,
    get_dashboard_articles,
    save_studio_article,
    set_article_status,
)
from .admin import admin_required, authenticate, create_admin_user, get_admin_users, login_csrf_token, update_admin_user
from .data import PAGE_META
from .studio import build_article, csrf_token, validate_csrf

public = Blueprint("public", __name__)

PAGE_CONTENT_KEYS = {
    "dx_sermon": "dx",
    "church_ai_transformation": "churchAiTransformation",
}


@public.before_request
def select_locale() -> None:
    # The route architecture is locale-ready; only Traditional Chinese is enabled in this migration.
    g.locale = current_app.config["DEFAULT_LOCALE"]


def page(template: str, key: str, **context):
    title, description = PAGE_META[key]
    return render_template(
        template,
        page_title=title,
        description=description,
        page_content=get_page(PAGE_CONTENT_KEYS.get(key, key)),
        **context,
    )


@public.get("/")
def home():
    return page(
        "pages/home.html",
        "home",
        pillars=get_collection("pillars"),
        services=get_collection("services"),
        testimonials=get_collection("testimonials"),
        news_items=get_news_items(),
    )


@public.get("/about/")
def about():
    return page("pages/about.html", "about", leaders=get_collection("leaders"))


@public.get("/services/")
def services():
    return page("pages/services.html", "services", services=get_collection("services"))


@public.get("/dx-sermon/")
def dx_sermon():
    return page(
        "pages/dx_sermon.html",
        "dx_sermon",
        dx_tools=get_collection("dxTools"),
        toolbox=get_collection("toolbox"),
        one_key_tools=get_collection("oneKeyTools"),
        testimonials=get_collection("testimonials"),
    )


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
    return page("pages/courses.html", "courses", courses=get_courses())


@public.get("/courses/<slug>/")
def course_detail(slug: str):
    course = get_course(slug)
    if course is None:
        abort(404)
    return page("pages/course_detail.html", "courses", course=course)


@public.route("/course-registration/", methods=["GET", "POST"])
def course_registration():
    return page("pages/course_registration.html", "course_registration")


@public.get("/articles/")
def articles():
    return page("articles/index.html", "articles", articles=get_articles())


@public.get("/articles/published/")
def published_articles():
    return page("articles/published.html", "articles")


@public.get("/articles/<slug>/")
def article_detail(slug: str):
    article = get_article(slug)
    if article is None:
        abort(404)
    return page("articles/detail.html", "articles", article=article)


@public.route("/article-studio/", methods=["GET", "POST"])
@admin_required
def article_studio():
    if request.method == "GET":
        return redirect(url_for("content_admin.article_studio", slug=request.args.get("slug", "")))
    selected_slug = request.args.get("slug", "").strip()
    selected = get_studio_article(selected_slug) if selected_slug else None
    notice = request.args.get("notice", "")
    error = ""
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            abort(400)
        selected_slug = request.form.get("original_slug", "").strip()
        selected = get_studio_article(selected_slug) if selected_slug else None
        try:
            article = build_article(
                request.form,
                request.files.get("source_file"),
                request.files.get("hero_image"),
                selected,
            )
            save_studio_article(article)
            action_label = "已發佈" if article["status"] == "posted" else "已儲存"
            return redirect(url_for("public.article_studio", slug=article["slug"], notice=action_label))
        except (ValueError, OSError) as exc:
            error = str(exc)
    return render_template(
        "articles/studio.html",
        page_title="人工智能事工中心 (CAIM) 文章生成工具",
        description="建立、編輯及發佈 CAIM 專欄文章。",
        selected=selected,
        csrf_token=csrf_token(),
        notice=notice,
        error=error,
    )


@public.post("/article-studio/delete/")
@admin_required
def article_studio_delete():
    if not validate_csrf(request.form.get("csrf_token")):
        abort(400)
    slug = request.form.get("slug", "").strip()
    if slug:
        set_article_status(slug, "deleted")
    return redirect(url_for("public.article_dashboard", notice="文章已標記為 Deleted"))


@public.route("/article-dashboard/login/", methods=["GET", "POST"])
def article_dashboard_login():
    return redirect(url_for("content_admin.content_manager"), code=301)
    error = ""
    if request.method == "POST":
        if request.form.get("csrf_token") != session.get("login_csrf"):
            abort(400)
        user = authenticate(request.form.get("username", "").strip(), request.form.get("password", ""))
        if user:
            session.clear()
            session["admin_user_id"] = user["id"]
            return redirect(url_for("public.article_dashboard"))
        error = "登入名稱或密碼不正確。"
    return render_template("articles/login.html", page_title="文章管理登入｜CAIM", csrf_token=login_csrf_token(), error=error)


@public.post("/article-dashboard/logout/")
@admin_required
def article_dashboard_logout():
    session.clear()
    return redirect(url_for("public.article_dashboard_login"))


@public.get("/article-dashboard/")
@admin_required
def article_dashboard():
    return redirect(url_for("content_admin.content_dashboard"), code=301)
    search = request.args.get("q", "").strip()
    try:
        current_page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        current_page = 1
    articles, total = get_dashboard_articles(search, current_page)
    return render_template("articles/dashboard.html", page_title="文章管理｜CAIM", articles=articles,
        search=search, current_page=current_page, total_pages=max(1, math.ceil(total / 6)),
        csrf_token=csrf_token(), notice=request.args.get("notice", ""))


@public.post("/article-dashboard/articles/<slug>/status/")
@admin_required
def article_dashboard_status(slug):
    if not validate_csrf(request.form.get("csrf_token")):
        abort(400)
    set_article_status(slug, request.form.get("status", ""))
    return redirect(url_for("public.article_dashboard"))


@public.route("/article-dashboard/users/", methods=["GET", "POST"])
@admin_required
def article_dashboard_users():
    if request.method == "GET":
        return redirect(url_for("content_admin.users"), code=301)
    error = ""
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            abort(400)
        try:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if len(username) < 3 or len(password) < 8:
                raise ValueError("登入名稱最少 3 個字元，密碼最少 8 個字元。")
            create_admin_user(username, password)
            return redirect(url_for("public.article_dashboard_users"))
        except (ValueError, pymysql.IntegrityError) as exc:
            error = "登入名稱已存在。" if isinstance(exc, pymysql.IntegrityError) else str(exc)
    return render_template("articles/users.html", page_title="管理使用者｜CAIM", users=get_admin_users(), csrf_token=csrf_token(), error=error)


@public.post("/article-dashboard/users/<int:user_id>/")
@admin_required
def article_dashboard_user_update(user_id):
    if not validate_csrf(request.form.get("csrf_token")):
        abort(400)
    action = request.form.get("action", "")
    if action == "toggle" and user_id == g.admin_user["id"]:
        abort(400)
    password = request.form.get("password", "")
    if action == "password" and len(password) < 8:
        abort(400)
    update_admin_user(user_id, action, password)
    return redirect(url_for("public.article_dashboard_users"))


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
