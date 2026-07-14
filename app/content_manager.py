import math
import time
from datetime import datetime

import pymysql
import httpx
from flask import Blueprint, abort, current_app, g, redirect, render_template, request, session, url_for

from .admin import admin_required, authenticate, create_admin_user, get_admin_users, login_csrf_token, update_admin_user
from .approval import approve, attach_approval_states, available_reviewers, reviewer_options, submit_for_review, validate_reviewers
from .content import (
    attach_translation_statuses, content_payload, get_content_counts, get_content_translation,
    get_dashboard_articles, get_dashboard_courses, get_dashboard_news,
    get_studio_article, get_studio_course, get_studio_news, save_studio_article,
    save_content_translation, save_studio_course, save_studio_news, set_article_status,
    set_course_status, set_news_status, validate_content_identity, overlay_translation,
)
from .content_studio import build_course, build_news
from .studio import build_article, csrf_token, validate_csrf
from .translation import translate_payload

content_admin = Blueprint("content_admin", __name__, url_prefix="/content")


@content_admin.route("/content-manager", methods=["GET", "POST"])
def content_manager():
    if session.get("admin_user_id"):
        return redirect(url_for("content_admin.content_dashboard"))
    error = ""
    if request.method == "POST":
        if request.form.get("csrf_token") != session.get("login_csrf"):
            abort(400)
        user = authenticate(request.form.get("username", "").strip(), request.form.get("password", ""))
        if user:
            session.clear()
            session["admin_user_id"] = user["id"]
            session["session_epoch"] = current_app.config["SESSION_EPOCH"]
            session["last_activity"] = time.time()
            session.permanent = True
            return redirect(url_for("content_admin.content_dashboard"))
        error = "登入名稱或密碼不正確。"
    return render_template("content/login.html", page_title="CAIM Content Manager", csrf_token=login_csrf_token(), error=error)


@content_admin.post("/logout")
@admin_required
def logout():
    session.clear()
    return redirect(url_for("content_admin.content_manager"))


@content_admin.get("/content-dashboard")
@admin_required
def content_dashboard():
    return render_template("content/dashboard.html", page_title="Content Dashboard", counts=get_content_counts())


def _page_number():
    try:
        return max(1, int(request.args.get("page", 1)))
    except ValueError:
        return 1


def _content_locale(selected=None):
    requested = request.form.get("content_locale") or request.args.get("lang")
    if requested in current_app.config["ENABLED_LOCALES"]:
        return requested
    return (selected or {}).get("original_locale", current_app.config["DEFAULT_LOCALE"])


def _available_content_locales(kind, selected):
    if not selected:
        return []
    attach_translation_statuses(kind, [selected])
    return [selected["original_locale"], *[
        code for code in current_app.config["ENABLED_LOCALES"]
        if code != selected["original_locale"] and code in selected["translations"]
    ]]


def _language_statuses(selected):
    if not selected:
        return []
    translations = selected.get("translations", {})
    return [
        {
            "locale": code,
            "generated": code == selected["original_locale"] or code in translations,
            "status": selected["status"] if code == selected["original_locale"] else translations.get(code),
        }
        for code in current_app.config["ENABLED_LOCALES"]
    ]


@content_admin.get("/articles")
@admin_required
def articles():
    search, current_page = request.args.get("q", "").strip(), _page_number()
    items, total = get_dashboard_articles(search, current_page)
    attach_translation_statuses("articles", items)
    attach_approval_states("articles", items, g.admin_user["id"], request.args.get("lang"))
    return render_template("content/list.html", page_title="Articles", content_kind="articles", items=items,
        search=search, current_page=current_page, total_pages=max(1, math.ceil(total / 6)), csrf_token=csrf_token(),
        notice=request.args.get("notice", ""))


@content_admin.route("/article-studio", methods=["GET", "POST"])
@admin_required
def article_studio():
    slug = request.args.get("slug", "").strip()
    selected = get_studio_article(slug) if slug else None
    available_content_locales = _available_content_locales("articles", selected)
    active_locale = _content_locale(selected)
    if selected and active_locale not in available_content_locales:
        active_locale = selected["original_locale"]
    if selected and active_locale != selected["original_locale"]:
        selected = overlay_translation("articles", selected, active_locale)
    error = ""
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            abort(400)
        original = request.form.get("original_slug", "").strip()
        base_selected = get_studio_article(original) if original else None
        active_locale = _content_locale(base_selected)
        if not base_selected:
            active_locale = request.form.get("original_locale", active_locale)
        selected = overlay_translation("articles", base_selected, active_locale) if base_selected else None
        try:
            if request.form.get("action") == "post":
                validate_reviewers(g.admin_user["id"], request.form.getlist("reviewer_ids"))
            validate_content_identity("articles", request.form.get("slug", "").strip().lower(), original)
            article = build_article(request.form, request.files.get("source_file"), request.files.get("hero_image"), selected)
            article["original_locale"] = (base_selected or {}).get("original_locale", active_locale)
            if base_selected and active_locale != base_selected["original_locale"]:
                save_content_translation("articles", original, active_locale, base_selected["original_locale"], content_payload("articles", article), article["status"], article["scheduled_posting_at"], g.admin_user["id"])
            else:
                save_studio_article(article, original)
            if article["status"] == "review":
                submit_for_review("articles", article["slug"], g.admin_user["id"], request.form.getlist("reviewer_ids"), active_locale)
            return redirect(url_for("content_admin.article_studio", slug=article["slug"], lang=active_locale, notice="Submitted for Review" if article["status"] == "review" else "Saved"))
        except (ValueError, OSError, pymysql.IntegrityError) as exc:
            error = str(exc)
    return render_template("content/article_studio.html", page_title="Article Studio", selected=selected,
        csrf_token=csrf_token(), notice=request.args.get("notice", ""), error=error, now_value=datetime.now().strftime("%Y-%m-%dT%H:%M"),
        reviewers=reviewer_options(g.admin_user["id"], "articles", selected["slug"] if selected else None,
            request.form.getlist("reviewer_ids") if request.method == "POST" else None, locale=active_locale), content_locale=active_locale,
        available_content_locales=available_content_locales, language_statuses=_language_statuses(selected))


@content_admin.get("/courses")
@admin_required
def courses():
    search, current_page = request.args.get("q", "").strip(), _page_number()
    items, total = get_dashboard_courses(search, current_page)
    attach_translation_statuses("courses", items)
    attach_approval_states("courses", items, g.admin_user["id"], request.args.get("lang"))
    return render_template("content/list.html", page_title="Courses & Events", content_kind="courses", items=items,
        search=search, current_page=current_page, total_pages=max(1, math.ceil(total / 6)), csrf_token=csrf_token(),
        notice=request.args.get("notice", ""))


@content_admin.route("/course-studio", methods=["GET", "POST"])
@admin_required
def course_studio():
    slug = request.args.get("slug", "").strip()
    selected = get_studio_course(slug) if slug else None
    available_content_locales = _available_content_locales("courses", selected)
    active_locale = _content_locale(selected)
    if selected and active_locale not in available_content_locales:
        active_locale = selected["original_locale"]
    if selected and active_locale != selected["original_locale"]:
        selected = overlay_translation("courses", selected, active_locale)
    error = ""
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            abort(400)
        original = request.form.get("original_slug", "").strip()
        base_selected = get_studio_course(original) if original else None
        active_locale = _content_locale(base_selected)
        if not base_selected:
            active_locale = request.form.get("original_locale", active_locale)
        selected = overlay_translation("courses", base_selected, active_locale) if base_selected else None
        try:
            if request.form.get("action") == "post":
                validate_reviewers(g.admin_user["id"], request.form.getlist("reviewer_ids"))
            validate_content_identity("courses", request.form.get("slug", "").strip().lower(), original,
                request.form.get("code", "").strip().upper())
            item = build_course(request.form, request.files.get("course_image"), selected)
            item["original_locale"] = (base_selected or {}).get("original_locale", active_locale)
            if base_selected and active_locale != base_selected["original_locale"]:
                save_content_translation("courses", original, active_locale, base_selected["original_locale"], content_payload("courses", item), item["status"], item["scheduled_posting_at"], g.admin_user["id"])
            else:
                save_studio_course(item, original)
            if item["status"] == "review":
                submit_for_review("courses", item["slug"], g.admin_user["id"], request.form.getlist("reviewer_ids"), active_locale)
            return redirect(url_for("content_admin.course_studio", slug=item["slug"], lang=active_locale, notice="Submitted for Review" if item["status"] == "review" else "Saved"))
        except (ValueError, OSError, pymysql.IntegrityError) as exc:
            error = str(exc)
    return render_template("content/course_studio.html", page_title="Course Studio", selected=selected,
        csrf_token=csrf_token(), notice=request.args.get("notice", ""), error=error, now_value=datetime.now().strftime("%Y-%m-%dT%H:%M"),
        reviewers=reviewer_options(g.admin_user["id"], "courses", selected["slug"] if selected else None,
            request.form.getlist("reviewer_ids") if request.method == "POST" else None, locale=active_locale), content_locale=active_locale,
        available_content_locales=available_content_locales, language_statuses=_language_statuses(selected))


@content_admin.get("/news")
@admin_required
def news():
    search, current_page = request.args.get("q", "").strip(), _page_number()
    items, total = get_dashboard_news(search, current_page)
    attach_translation_statuses("news", items)
    attach_approval_states("news", items, g.admin_user["id"], request.args.get("lang"))
    return render_template("content/list.html", page_title="News & Events", content_kind="news", items=items,
        search=search, current_page=current_page, total_pages=max(1, math.ceil(total / 6)), csrf_token=csrf_token(),
        notice=request.args.get("notice", ""))


@content_admin.route("/news-studio", methods=["GET", "POST"])
@admin_required
def news_studio():
    slug = request.args.get("slug", "").strip()
    selected = get_studio_news(slug) if slug else None
    available_content_locales = _available_content_locales("news", selected)
    active_locale = _content_locale(selected)
    if selected and active_locale not in available_content_locales:
        active_locale = selected["original_locale"]
    if selected and active_locale != selected["original_locale"]:
        selected = overlay_translation("news", selected, active_locale)
    error = ""
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            abort(400)
        original = request.form.get("original_slug", "").strip()
        base_selected = get_studio_news(original) if original else None
        active_locale = _content_locale(base_selected)
        if not base_selected:
            active_locale = request.form.get("original_locale", active_locale)
        selected = overlay_translation("news", base_selected, active_locale) if base_selected else None
        try:
            if request.form.get("action") == "post":
                validate_reviewers(g.admin_user["id"], request.form.getlist("reviewer_ids"))
            validate_content_identity("news", request.form.get("slug", "").strip().lower(), original)
            item = build_news(request.form, selected)
            item["original_locale"] = (base_selected or {}).get("original_locale", active_locale)
            if base_selected and active_locale != base_selected["original_locale"]:
                save_content_translation("news", original, active_locale, base_selected["original_locale"], content_payload("news", item), item["status"], item["scheduled_posting_at"], g.admin_user["id"])
            else:
                save_studio_news(item, original)
            if item["status"] == "review":
                submit_for_review("news", item["slug"], g.admin_user["id"], request.form.getlist("reviewer_ids"), active_locale)
            return redirect(url_for("content_admin.news_studio", slug=item["slug"], lang=active_locale, notice="Submitted for Review" if item["status"] == "review" else "Saved"))
        except (ValueError, pymysql.IntegrityError) as exc:
            error = str(exc)
    return render_template("content/news_studio.html", page_title="News Studio", selected=selected,
        csrf_token=csrf_token(), notice=request.args.get("notice", ""), error=error, now_value=datetime.now().strftime("%Y-%m-%dT%H:%M"),
        reviewers=reviewer_options(g.admin_user["id"], "news", selected["slug"] if selected else None,
            request.form.getlist("reviewer_ids") if request.method == "POST" else None, locale=active_locale), content_locale=active_locale,
        available_content_locales=available_content_locales, language_statuses=_language_statuses(selected))


@content_admin.post("/<kind>/<slug>/approve")
@admin_required
def approve_content(kind, slug):
    if not validate_csrf(request.form.get("csrf_token")):
        abort(400)
    try:
        locale = request.form.get("content_locale", current_app.config["DEFAULT_LOCALE"])
        published = approve(kind, slug, g.admin_user["id"], locale)
        notice = "All reviewers approved; content is Posted." if published else "Approval recorded."
    except ValueError as exc:
        notice = str(exc)
    return redirect(url_for(f"content_admin.{kind}", lang=locale, notice=notice))


@content_admin.post("/<kind>/<slug>/translate")
@admin_required
def translate_content(kind, slug):
    if not validate_csrf(request.form.get("csrf_token")):
        abort(400)
    getters = {"articles": get_studio_article, "courses": get_studio_course, "news": get_studio_news}
    studios = {"articles": "article_studio", "courses": "course_studio", "news": "news_studio"}
    if kind not in getters:
        abort(404)
    item = getters[kind](slug)
    if not item:
        abort(404)
    source_locale = item["original_locale"]
    try:
        if item["status"] != "posted":
            raise ValueError("The original language must be approved and Posted before translation.")
        targets = [
            code for code in current_app.config["ENABLED_LOCALES"]
            if code != source_locale and not get_content_translation(kind, slug, code)
        ]
        if not targets:
            raise ValueError("All supported translations already exist.")
        translated_payloads = {
            code: translate_payload(content_payload(kind, item), source_locale, code)
            for code in targets
        }
        reviewer_ids = [str(reviewer["id"]) for reviewer in available_reviewers(g.admin_user["id"])]
        validate_reviewers(g.admin_user["id"], reviewer_ids)
        for code, translated in translated_payloads.items():
            save_content_translation(kind, slug, code, source_locale, translated, "review",
                item.get("scheduled_posting_at"), g.admin_user["id"])
            submit_for_review(kind, slug, g.admin_user["id"], reviewer_ids, code)
        notice = "All supported languages were translated and submitted for separate review."
    except (ValueError, httpx.HTTPError) as exc:
        notice = str(exc)
    return redirect(url_for(f"content_admin.{studios[kind]}", slug=slug, lang=source_locale, notice=notice))


@content_admin.post("/<kind>/<slug>/status")
@admin_required
def set_status(kind, slug):
    if not validate_csrf(request.form.get("csrf_token")):
        abort(400)
    status = request.form.get("status", "")
    handlers = {"articles": set_article_status, "courses": set_course_status, "news": set_news_status}
    if kind not in handlers:
        abort(404)
    handlers[kind](slug, status)
    return redirect(url_for(f"content_admin.{kind}"))


@content_admin.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    error = ""
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            abort(400)
        try:
            username, password = request.form.get("username", "").strip(), request.form.get("password", "")
            if len(username) < 3 or len(password) < 8:
                raise ValueError("Username requires 3 characters and password requires 8 characters.")
            create_admin_user(username, password)
            return redirect(url_for("content_admin.users"))
        except (ValueError, pymysql.IntegrityError) as exc:
            error = str(exc)
    return render_template("content/users.html", page_title="Users", users=get_admin_users(), csrf_token=csrf_token(), error=error)


@content_admin.post("/users/<int:user_id>")
@admin_required
def user_update(user_id):
    if not validate_csrf(request.form.get("csrf_token")):
        abort(400)
    action, password = request.form.get("action", ""), request.form.get("password", "")
    if action == "toggle" and user_id == g.admin_user["id"]:
        abort(400)
    if action == "password" and len(password) < 8:
        abort(400)
    update_admin_user(user_id, action, password)
    return redirect(url_for("content_admin.users"))
