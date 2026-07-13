from datetime import date, datetime

from .studio import SLUG_PATTERN, save_course_image, split_paragraphs


def _schedule(form, existing):
    if existing and existing.get("status") == "posted":
        return existing.get("scheduled_posting_at")
    value = form.get("scheduled_posting_at", "").strip()
    return datetime.strptime(value, "%Y-%m-%dT%H:%M") if value else datetime.now()


def _status(form, existing):
    if form.get("action") == "post":
        return "review"
    return "posted" if existing and existing.get("status") == "posted" else "saved"


def _posted_at(status, existing):
    if existing and existing.get("posted_at"):
        return existing["posted_at"]
    return datetime.now() if status == "posted" else None


def build_course(form, image_upload=None, existing=None):
    code = form.get("code", "").strip().upper()
    slug = form.get("slug", "").strip().lower()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    if not code or not title or not description:
        raise ValueError("Code, title, and description are required.")
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("Slug may contain lowercase letters, numbers, and hyphens only.")
    body = form.get("body", "").strip()
    status = _status(form, existing)
    content_type = form.get("content_type", "course")
    if content_type not in {"course", "event"}:
        raise ValueError("Invalid course content type.")
    detail = dict((existing or {}).get("detail") or {})
    detail.update({
        "eyebrow": form.get("eyebrow", "").strip() or code,
        "subtitle": form.get("subtitle", "").strip(),
        "paragraphs": split_paragraphs(body),
    })
    uploaded_image = save_course_image(image_upload)
    image = uploaded_image or form.get("image", "").strip() or (existing or {}).get("image") or "/assets/courses-training-courses.png"
    return {
        "code": code, "slug": slug, "title": title, "description": description,
        "image": image,
        "alt": form.get("alt", "").strip() or title, "href": f"/courses/{slug}/",
        "cta_label": form.get("cta_label", "").strip() or "了解更多",
        "detail": detail, "sort_order": int(form.get("sort_order", 0) or 0),
        "is_published": status == "posted", "content_type": content_type, "status": status,
        "scheduled_posting_at": _schedule(form, existing), "posted_at": _posted_at(status, existing),
    }


def build_news(form, existing=None):
    slug = form.get("slug", "").strip().lower()
    title = form.get("title", "").strip()
    content = form.get("content", "").strip()
    event_date = form.get("event_date", "").strip() or date.today().isoformat()
    datetime.strptime(event_date, "%Y-%m-%d")
    if not title or not content:
        raise ValueError("Title and content are required.")
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("Slug may contain lowercase letters, numbers, and hyphens only.")
    content_type = form.get("content_type", "news")
    if content_type not in {"news", "event"}:
        raise ValueError("Invalid news content type.")
    status = _status(form, existing)
    label = form.get("date_label", "").strip() or datetime.strptime(event_date, "%Y-%m-%d").strftime("%b. %d, %Y").upper()
    return {
        "slug": slug, "title": title, "event_date": event_date, "date_label": label,
        "content": content, "content_type": content_type, "status": status,
        "scheduled_posting_at": _schedule(form, existing), "posted_at": _posted_at(status, existing),
    }
