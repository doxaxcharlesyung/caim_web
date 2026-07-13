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
        "SELECT code, slug, title, description, image, alt, href, cta_label, detail, content_type "
        "FROM courses WHERE status='posted' AND is_published=1 "
        "AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW()) ORDER BY sort_order, id"
    )
    return [decode_json_fields(row, "detail") for row in rows]


def get_course(slug):
    row = fetch_one(
        "SELECT code, slug, title, description, image, alt, href, cta_label, detail, content_type "
        "FROM courses WHERE slug=%s AND status='posted' AND is_published=1 "
        "AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW())",
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
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE title=VALUES(title), excerpt=VALUES(excerpt),
            category=VALUES(category), image=VALUES(image), alt=VALUES(alt),
            published_date=VALUES(published_date), href=VALUES(href),
            detail=VALUES(detail), status=VALUES(status),
            scheduled_posting_at=IF(articles.status='posted',articles.scheduled_posting_at,VALUES(scheduled_posting_at)),
            posted_at=COALESCE(articles.posted_at,VALUES(posted_at))""",
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
        f"SELECT code,slug,title,description,image,content_type,status,scheduled_posting_at,updated_at "
        f"FROM courses WHERE {where} ORDER BY updated_at DESC LIMIT %s OFFSET %s", params
    )
    return rows, total


def get_studio_course(slug):
    row = fetch_one(
        "SELECT code,slug,title,description,image,alt,href,cta_label,detail,sort_order,is_published,"
        "content_type,status,scheduled_posting_at,posted_at FROM courses WHERE slug=%s AND status<>'deleted'",
        (slug,),
    )
    return decode_json_fields(row, "detail")


def save_studio_course(course):
    with get_db().cursor() as cursor:
        cursor.execute(
            """INSERT INTO courses
            (code,slug,title,description,image,alt,href,cta_label,detail,sort_order,is_published,content_type,status,scheduled_posting_at,posted_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE code=VALUES(code),title=VALUES(title),description=VALUES(description),
            image=VALUES(image),alt=VALUES(alt),href=VALUES(href),cta_label=VALUES(cta_label),detail=VALUES(detail),
            sort_order=VALUES(sort_order),is_published=VALUES(is_published),content_type=VALUES(content_type),
            status=VALUES(status),scheduled_posting_at=VALUES(scheduled_posting_at),posted_at=COALESCE(courses.posted_at,VALUES(posted_at))""",
            (course["code"], course["slug"], course["title"], course["description"], course["image"],
             course["alt"], course["href"], course["cta_label"], json.dumps(course["detail"], ensure_ascii=False),
             course["sort_order"], course["is_published"], course["content_type"], course["status"],
             course["scheduled_posting_at"], course["posted_at"]),
        )


def set_course_status(slug, status):
    if status not in {"expired", "deleted"}:
        raise ValueError("Invalid course status")
    with get_db().cursor() as cursor:
        cursor.execute("UPDATE courses SET status=%s,is_published=0 WHERE slug=%s", (status, slug))


def get_news_items():
    return fetch_all(
        "SELECT slug,title,event_date AS date,date_label AS dateLabel,content,content_type "
        "FROM news WHERE status='posted' AND (scheduled_posting_at IS NULL OR scheduled_posting_at<=NOW()) "
        "ORDER BY event_date DESC,id DESC"
    )


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
        f"SELECT slug,title,content,content_type,event_date,status,scheduled_posting_at,updated_at "
        f"FROM news WHERE {where} ORDER BY updated_at DESC LIMIT %s OFFSET %s", params
    )
    return rows, total


def get_studio_news(slug):
    return fetch_one(
        "SELECT slug,title,event_date,date_label,content,content_type,status,scheduled_posting_at,posted_at "
        "FROM news WHERE slug=%s AND status<>'deleted'", (slug,)
    )


def save_studio_news(item):
    with get_db().cursor() as cursor:
        cursor.execute(
            """INSERT INTO news
            (slug,title,event_date,date_label,content,content_type,status,scheduled_posting_at,posted_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE title=VALUES(title),event_date=VALUES(event_date),date_label=VALUES(date_label),
            content=VALUES(content),content_type=VALUES(content_type),status=VALUES(status),
            scheduled_posting_at=VALUES(scheduled_posting_at),posted_at=COALESCE(news.posted_at,VALUES(posted_at))""",
            tuple(item[key] for key in ("slug","title","event_date","date_label","content","content_type","status","scheduled_posting_at","posted_at")),
        )


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
