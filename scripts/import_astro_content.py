import argparse
import json
import os
import subprocess
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parents[1]


def load_astro_data(astro_root: Path):
    result = subprocess.run(
        ["node", str(ROOT / "scripts" / "export_astro_content.mjs"), str(astro_root)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def execute_schema(connection):
    sql = (ROOT / "scripts" / "schema.sql").read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        for statement in (part.strip() for part in sql.split(";")):
            if statement:
                cursor.execute(statement)
        cursor.execute(
            "INSERT IGNORE INTO admin_users (username,password_hash) VALUES ('admin',%s)",
            (generate_password_hash("New2P@ss"),),
        )


def import_data(connection, data):
    content = data["content"]
    with connection.cursor() as cursor:
        for key, page in data["pages"].items():
            cursor.execute(
                """INSERT INTO page_content (content_key, title, subtitle, sections)
                VALUES (%s, %s, %s, %s) AS incoming
                ON DUPLICATE KEY UPDATE title=incoming.title, subtitle=incoming.subtitle, sections=incoming.sections""",
                (key, page["title"], page["subtitle"], json.dumps(page.get("sections"), ensure_ascii=False)),
            )

        collections = {
            key: value for key, value in content.items()
            if key not in {"courses", "articlePosts"}
        }
        collections.update({
            "newsItems": data["newsItems"],
            "navigation": data["navigation"],
            "site": [data["site"]],
            "seoTitles": [{"path": key, "title": value} for key, value in data["seoTitles"].items()],
        })
        for collection_name, items in collections.items():
            cursor.execute("DELETE FROM content_items WHERE collection_name=%s", (collection_name,))
            for index, item in enumerate(items):
                item_data = item if isinstance(item, dict) else {"value": item}
                item_key = str(item_data.get("slug") or item_data.get("code") or item_data.get("title") or item_data.get("name") or index)
                cursor.execute(
                    "INSERT INTO content_items (collection_name, item_key, sort_order, item_data) VALUES (%s,%s,%s,%s)",
                    (collection_name, item_key, index, json.dumps(item_data, ensure_ascii=False)),
                )

        for index, course in enumerate(content["courses"]):
            cursor.execute(
                """INSERT INTO courses
                (code, slug, title, description, image, alt, href, cta_label, detail, sort_order)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS incoming
                ON DUPLICATE KEY UPDATE title=incoming.title, description=incoming.description,
                image=incoming.image, alt=incoming.alt, href=incoming.href,
                cta_label=incoming.cta_label, detail=incoming.detail, sort_order=incoming.sort_order""",
                (course["code"], course["slug"], course["title"], course["description"], course["image"],
                 course["alt"], course["href"], course["ctaLabel"],
                 json.dumps(course.get("detail"), ensure_ascii=False), index),
            )

        for article in content["articlePosts"]:
            cursor.execute(
                """INSERT INTO articles
                (slug, title, excerpt, category, image, alt, published_date, href, detail, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'posted') AS incoming
                ON DUPLICATE KEY UPDATE title=incoming.title, excerpt=incoming.excerpt,
                category=incoming.category, image=incoming.image, alt=incoming.alt,
                published_date=incoming.published_date, href=incoming.href, detail=incoming.detail""",
                (article["slug"], article["title"], article["excerpt"], article["category"], article["image"],
                 article["alt"], article["date"], article["href"],
                 json.dumps(article.get("detail"), ensure_ascii=False)),
            )
    connection.commit()


def main():
    parser = argparse.ArgumentParser(description="Import Astro content modules into CAIM MySQL tables.")
    parser.add_argument("--astro-root", type=Path, default=ROOT.parent / "caim-website-francis-v2")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "caimadmin"),
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME", "caimdb"),
        charset="utf8mb4",
    )
    try:
        execute_schema(connection)
        data = load_astro_data(args.astro_root)
        import_data(connection, data)
        print(f"Imported {len(data['content']['courses'])} courses and {len(data['content']['articlePosts'])} articles.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
