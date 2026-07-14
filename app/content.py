import json

from .db import decode_json_fields, fetch_all, fetch_one, get_db


def validate_content_identity(kind, slug, original_slug="", code=""):
    tables = {"articles": "articles", "courses": "courses", "news": "news"}
    if kind not in tables:
        raise ValueError("Invalid content type")
    row = fetch_one(f"SELECT slug FROM `{tables[kind]}` WHERE slug=%s", (slug,))
    if row and row["slug"] != original_slug:
        raise ValueError(f"The slug '{slug}' already exists. Choose a unique slug for new content.")
    if kind == "courses" and code:
        row = fetch_one("SELECT slug FROM courses WHERE code=%s", (code,))
        if row and row["slug"] != original_slug:
            raise ValueError(f"The course code '{code}' already exists. Choose a unique course code.")


TRANSLATABLE_FIELDS = {
    "articles": ("title", "excerpt", "category", "alt", "detail"),
    "courses": ("title", "description", "alt", "cta_label", "detail"),
    "news": ("title", "date_label", "content"),
}


def content_payload(kind, item):
    return {field: item.get(field) for field in TRANSLATABLE_FIELDS[kind]}


def get_content_translation(kind, key, locale, public_only=False):
    status_clause = " AND status='posted' AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW())" if public_only else ""
    row = fetch_one(
        f"SELECT locale,source_locale,payload,status,scheduled_posting_at,posted_at FROM content_translations WHERE content_type=%s AND content_key=%s AND locale=%s{status_clause}",
        (kind, key, locale),
    )
    return decode_json_fields(row, "payload")


def save_content_translation(kind, key, locale, source_locale, payload, status="saved", scheduled_at=None, user_id=None):
    with get_db().cursor() as cursor:
        cursor.execute(
            """INSERT INTO content_translations
            (content_type,content_key,locale,source_locale,payload,status,scheduled_posting_at,created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE source_locale=VALUES(source_locale),payload=VALUES(payload),status=VALUES(status),
            scheduled_posting_at=VALUES(scheduled_posting_at),posted_at=IF(VALUES(status)='posted',COALESCE(posted_at,NOW()),posted_at),created_by=VALUES(created_by)""",
            (kind, key, locale, source_locale, json.dumps(payload, ensure_ascii=False), status, scheduled_at, user_id),
        )


def overlay_translation(kind, item, locale, public_only=False):
    if not item or locale == item.get("original_locale", "zh-Hant"):
        return item
    translation = get_content_translation(kind, item["slug"], locale, public_only)
    if not translation:
        if public_only:
            # An approved original is the public fallback until this locale is approved.
            item["active_locale"] = item.get("original_locale", "zh-Hant")
            item["translation_status"] = "fallback"
            return item
        item["translation_status"] = "missing"
        item["status"] = "saved"
        item["active_locale"] = locale
        return item
    item.update(translation["payload"])
    item["translation_status"] = translation["status"]
    item["status"] = translation["status"]
    item["scheduled_posting_at"] = translation["scheduled_posting_at"]
    item["posted_at"] = translation["posted_at"]
    item["active_locale"] = locale
    return item


def attach_translation_statuses(kind, items):
    for item in items:
        rows = fetch_all(
            "SELECT locale,status FROM content_translations WHERE content_type=%s AND content_key=%s ORDER BY locale",
            (kind, item["slug"]),
        )
        item["translations"] = {row["locale"]: row["status"] for row in rows}
    return items


def get_page(key):
    row = fetch_one("SELECT content_key, title, subtitle, sections FROM page_content WHERE content_key=%s", (key,))
    return decode_json_fields(row, "sections")


def get_collection(name):
    rows = fetch_all(
        "SELECT item_data FROM content_items WHERE collection_name=%s ORDER BY sort_order, id",
        (name,),
    )
    return [decode_json_fields(row, "item_data")["item_data"] for row in rows]


def get_courses(locale="zh-Hant"):
    rows = fetch_all(
        "SELECT code, slug, title, description, image, alt, href, cta_label, detail, content_type, original_locale "
        "FROM courses WHERE status='posted' AND is_published=1 "
        "AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW()) ORDER BY sort_order, id"
    )
    return [item for row in rows if (item := overlay_translation("courses", decode_json_fields(row, "detail"), locale, True))]


def get_course(slug, locale="zh-Hant"):
    row = fetch_one(
        "SELECT code, slug, title, description, image, alt, href, cta_label, detail, content_type, original_locale "
        "FROM courses WHERE slug=%s AND status='posted' AND is_published=1 "
        "AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW())",
        (slug.lower(),),
    )
    return overlay_translation("courses", decode_json_fields(row, "detail"), locale, True)


def get_articles(locale="zh-Hant"):
    rows = fetch_all(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail, original_locale "
        "FROM articles WHERE status='posted' AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW()) "
        "ORDER BY COALESCE(scheduled_posting_at,published_date) DESC, id DESC"
    )
    return [item for row in rows if (item := overlay_translation("articles", decode_json_fields(row, "detail"), locale, True))]


def get_article(slug, locale="zh-Hant"):
    row = fetch_one(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail, original_locale "
        "FROM articles WHERE slug=%s AND status='posted' AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW())",
        (slug,),
    )
    return overlay_translation("articles", decode_json_fields(row, "detail"), locale, True)


def get_studio_articles():
    rows = fetch_all(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail, status, original_locale, scheduled_posting_at, posted_at "
        "FROM articles ORDER BY published_date DESC, id DESC"
    )
    return [decode_json_fields(row, "detail") for row in rows]


def get_studio_article(slug):
    row = fetch_one(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail, status, original_locale, scheduled_posting_at, posted_at "
        "FROM articles WHERE slug=%s AND status<>'deleted'",
        (slug,),
    )
    return decode_json_fields(row, "detail")


def save_studio_article(article, original_slug=None):
    with get_db().cursor() as cursor:
        values = (
            article["slug"], article["title"], article["excerpt"], article["category"],
            article["image"], article["alt"], article["published_date"], article["href"],
            json.dumps(article["detail"], ensure_ascii=False), article["status"],
            article.get("original_locale", "zh-Hant"),
            article["scheduled_posting_at"], article["posted_at"],
        )
        if original_slug:
            cursor.execute("SELECT id FROM articles WHERE slug=%s", (original_slug,))
            if not cursor.fetchone():
                raise ValueError("The article being edited no longer exists.")
            cursor.execute(
                """UPDATE articles SET slug=%s,title=%s,excerpt=%s,category=%s,image=%s,alt=%s,
                published_date=%s,href=%s,detail=%s,status=%s,original_locale=%s,
                scheduled_posting_at=IF(status='posted',scheduled_posting_at,%s),
                posted_at=COALESCE(posted_at,%s) WHERE slug=%s""",
                values + (original_slug,),
            )
            if original_slug != article["slug"]:
                cursor.execute("UPDATE content_approvals SET content_key=%s WHERE content_type='articles' AND content_key=%s",
                    (article["slug"], original_slug))
        else:
            cursor.execute(
                """INSERT INTO articles
            (slug, title, excerpt, category, image, alt, published_date, href, detail, status, original_locale, scheduled_posting_at, posted_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", values)


def delete_studio_article(slug):
    with get_db().cursor() as cursor:
        cursor.execute("DELETE FROM articles WHERE slug=%s", (slug,))
        return cursor.rowcount > 0


def get_dashboard_articles(search, page, per_page=6):
    where = "status<>'deleted'"
    params = []
    if search:
        where += " AND (title LIKE %s OR excerpt LIKE %s OR category LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])
    total = fetch_one(f"SELECT COUNT(*) total FROM articles WHERE {where}", params)["total"]
    params.extend([per_page, (page - 1) * per_page])
    rows = fetch_all(
        f"SELECT slug,title,excerpt,category,image,status,original_locale,scheduled_posting_at,updated_at FROM articles WHERE {where} "
        "ORDER BY updated_at DESC LIMIT %s OFFSET %s", params
    )
    return rows, total


def set_article_status(slug, status):
    if status not in {"expired", "deleted"}:
        raise ValueError("Invalid article status")
    with get_db().cursor() as cursor:
        cursor.execute("UPDATE articles SET status=%s WHERE slug=%s", (status, slug))


def get_dashboard_courses(search, page, per_page=6):
    where = "status<>'deleted'"
    params = []
    if search:
        where += " AND (title LIKE %s OR description LIKE %s OR code LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])
    total = fetch_one(f"SELECT COUNT(*) total FROM courses WHERE {where}", params)["total"]
    params.extend([per_page, (page - 1) * per_page])
    rows = fetch_all(
        f"SELECT code,slug,title,description,image,content_type,status,original_locale,scheduled_posting_at,updated_at "
        f"FROM courses WHERE {where} ORDER BY updated_at DESC LIMIT %s OFFSET %s", params
    )
    return rows, total


def get_studio_course(slug):
    row = fetch_one(
        "SELECT code,slug,title,description,image,alt,href,cta_label,detail,sort_order,is_published,"
        "content_type,original_locale,status,scheduled_posting_at,posted_at FROM courses WHERE slug=%s AND status<>'deleted'",
        (slug,),
    )
    return decode_json_fields(row, "detail")


def save_studio_course(course, original_slug=None):
    with get_db().cursor() as cursor:
        values = (course["code"], course["slug"], course["title"], course["description"], course["image"],
            course["alt"], course["href"], course["cta_label"], json.dumps(course["detail"], ensure_ascii=False),
            course["sort_order"], course["is_published"], course["content_type"], course.get("original_locale", "zh-Hant"), course["status"],
            course["scheduled_posting_at"], course["posted_at"])
        if original_slug:
            cursor.execute("SELECT id FROM courses WHERE slug=%s", (original_slug,))
            if not cursor.fetchone():
                raise ValueError("The course being edited no longer exists.")
            cursor.execute(
                """UPDATE courses SET code=%s,slug=%s,title=%s,description=%s,image=%s,alt=%s,href=%s,
                cta_label=%s,detail=%s,sort_order=%s,is_published=%s,content_type=%s,original_locale=%s,status=%s,
                scheduled_posting_at=%s,posted_at=COALESCE(posted_at,%s) WHERE slug=%s""",
                values + (original_slug,),
            )
            if original_slug != course["slug"]:
                cursor.execute("UPDATE content_approvals SET content_key=%s WHERE content_type='courses' AND content_key=%s",
                    (course["slug"], original_slug))
        else:
            cursor.execute(
                """INSERT INTO courses
            (code,slug,title,description,image,alt,href,cta_label,detail,sort_order,is_published,content_type,original_locale,status,scheduled_posting_at,posted_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", values)


def set_course_status(slug, status):
    if status not in {"expired", "deleted"}:
        raise ValueError("Invalid course status")
    with get_db().cursor() as cursor:
        cursor.execute("UPDATE courses SET status=%s,is_published=0 WHERE slug=%s", (status, slug))


def get_news_items(locale="zh-Hant"):
    rows = fetch_all(
        "SELECT slug,title,event_date AS date,date_label AS dateLabel,date_label,content,content_type,original_locale "
        "FROM news WHERE status='posted' AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW()) "
        "ORDER BY event_date DESC,id DESC"
    )
    items = []
    for row in rows:
        item = overlay_translation("news", row, locale, True)
        if item:
            item["dateLabel"] = item.get("date_label", item.get("dateLabel"))
            items.append(item)
    return items


def get_dashboard_news(search, page, per_page=6):
    where = "status<>'deleted'"
    params = []
    if search:
        where += " AND (title LIKE %s OR content LIKE %s OR content_type LIKE %s)"
        term = f"%{search}%"
        params.extend([term, term, term])
    total = fetch_one(f"SELECT COUNT(*) total FROM news WHERE {where}", params)["total"]
    params.extend([per_page, (page - 1) * per_page])
    rows = fetch_all(
        f"SELECT slug,title,content,content_type,event_date,status,original_locale,scheduled_posting_at,updated_at "
        f"FROM news WHERE {where} ORDER BY updated_at DESC LIMIT %s OFFSET %s", params
    )
    return rows, total


def get_studio_news(slug):
    return fetch_one(
        "SELECT slug,title,event_date,date_label,content,content_type,original_locale,status,scheduled_posting_at,posted_at "
        "FROM news WHERE slug=%s AND status<>'deleted'", (slug,)
    )


def save_studio_news(item, original_slug=None):
    with get_db().cursor() as cursor:
        values = tuple(item[key] for key in (
            "slug","title","event_date","date_label","content","content_type","original_locale","status","scheduled_posting_at","posted_at"
        ))
        if original_slug:
            cursor.execute("SELECT id FROM news WHERE slug=%s", (original_slug,))
            if not cursor.fetchone():
                raise ValueError("The news or event item being edited no longer exists.")
            cursor.execute(
                """UPDATE news SET slug=%s,title=%s,event_date=%s,date_label=%s,content=%s,
                content_type=%s,original_locale=%s,status=%s,scheduled_posting_at=%s,posted_at=COALESCE(posted_at,%s)
                WHERE slug=%s""", values + (original_slug,))
            if original_slug != item["slug"]:
                cursor.execute("UPDATE content_approvals SET content_key=%s WHERE content_type='news' AND content_key=%s",
                    (item["slug"], original_slug))
        else:
            cursor.execute(
                """INSERT INTO news
            (slug,title,event_date,date_label,content,content_type,original_locale,status,scheduled_posting_at,posted_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", values)


def set_news_status(slug, status):
    if status not in {"expired", "deleted"}:
        raise ValueError("Invalid news status")
    with get_db().cursor() as cursor:
        cursor.execute("UPDATE news SET status=%s WHERE slug=%s", (status, slug))


def get_content_counts():
    return {
        "articles": fetch_one("SELECT COUNT(*) total FROM articles WHERE status<>'deleted'")["total"],
        "courses": fetch_one("SELECT COUNT(*) total FROM courses WHERE status<>'deleted'")["total"],
        "news": fetch_one("SELECT COUNT(*) total FROM news WHERE status<>'deleted'")["total"],
    }
