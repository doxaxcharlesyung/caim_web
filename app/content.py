import json

from .db import decode_json_fields, fetch_all, fetch_one, get_db


def get_page(key):
    row = fetch_one("SELECT content_key, title, subtitle, sections FROM page_content WHERE content_key=%s", (key,))
    return decode_json_fields(row, "sections")


def get_collection(name):
    rows = fetch_all(
        "SELECT item_data FROM content_items WHERE collection_name=%s ORDER BY sort_order, id",
        (name,),
    )
    return [decode_json_fields(row, "item_data")["item_data"] for row in rows]


def get_courses():
    rows = fetch_all(
        "SELECT code, slug, title, description, image, alt, href, cta_label, detail "
        "FROM courses WHERE is_published=1 ORDER BY sort_order, id"
    )
    return [decode_json_fields(row, "detail") for row in rows]


def get_course(slug):
    row = fetch_one(
        "SELECT code, slug, title, description, image, alt, href, cta_label, detail "
        "FROM courses WHERE slug=%s AND is_published=1",
        (slug.lower(),),
    )
    return decode_json_fields(row, "detail")


def get_articles():
    rows = fetch_all(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail "
        "FROM articles WHERE status='posted' AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW()) "
        "ORDER BY COALESCE(scheduled_posting_at,published_date) DESC, id DESC"
    )
    return [decode_json_fields(row, "detail") for row in rows]


def get_article(slug):
    row = fetch_one(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail "
        "FROM articles WHERE slug=%s AND status='posted' AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW())",
        (slug,),
    )
    return decode_json_fields(row, "detail")


def get_studio_articles():
    rows = fetch_all(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail, status, scheduled_posting_at, posted_at "
        "FROM articles ORDER BY published_date DESC, id DESC"
    )
    return [decode_json_fields(row, "detail") for row in rows]


def get_studio_article(slug):
    row = fetch_one(
        "SELECT slug, title, excerpt, category, image, alt, published_date, href, detail, status, scheduled_posting_at, posted_at "
        "FROM articles WHERE slug=%s AND status<>'deleted'",
        (slug,),
    )
    return decode_json_fields(row, "detail")


def save_studio_article(article):
    with get_db().cursor() as cursor:
        cursor.execute(
            """INSERT INTO articles
            (slug, title, excerpt, category, image, alt, published_date, href, detail, status, scheduled_posting_at, posted_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS incoming
            ON DUPLICATE KEY UPDATE title=incoming.title, excerpt=incoming.excerpt,
            category=incoming.category, image=incoming.image, alt=incoming.alt,
            published_date=incoming.published_date, href=incoming.href,
            detail=incoming.detail, status=incoming.status,
            scheduled_posting_at=IF(articles.status='posted',articles.scheduled_posting_at,incoming.scheduled_posting_at),
            posted_at=COALESCE(articles.posted_at,incoming.posted_at)""",
            (
                article["slug"], article["title"], article["excerpt"], article["category"],
                article["image"], article["alt"], article["published_date"], article["href"],
                json.dumps(article["detail"], ensure_ascii=False), article["status"],
                article["scheduled_posting_at"], article["posted_at"],
            ),
        )


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
        f"SELECT slug,title,excerpt,category,image,status,scheduled_posting_at,updated_at FROM articles WHERE {where} "
        "ORDER BY updated_at DESC LIMIT %s OFFSET %s", params
    )
    return rows, total


def set_article_status(slug, status):
    if status not in {"expired", "deleted"}:
        raise ValueError("Invalid article status")
    with get_db().cursor() as cursor:
        cursor.execute("UPDATE articles SET status=%s WHERE slug=%s", (status, slug))
