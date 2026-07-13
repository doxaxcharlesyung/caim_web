import argparse
import json
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path, default=ROOT / "scripts" / "content_snapshot.json", nargs="?")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    connection = pymysql.connect(host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "caimadmin"), password=os.environ["DB_PASSWORD"], database=os.getenv("DB_NAME", "caimdb"),
        charset="utf8mb4")
    try:
        with connection.cursor() as cursor:
            for row in snapshot["page_content"]:
                cursor.execute("""INSERT INTO page_content (content_key,title,subtitle,sections) VALUES (%s,%s,%s,%s) AS incoming
                    ON DUPLICATE KEY UPDATE title=incoming.title,subtitle=incoming.subtitle,sections=incoming.sections""",
                    (row["content_key"], row["title"], row["subtitle"], row["sections"]))
            for row in snapshot["content_items"]:
                cursor.execute("""INSERT INTO content_items (collection_name,item_key,sort_order,item_data) VALUES (%s,%s,%s,%s) AS incoming
                    ON DUPLICATE KEY UPDATE sort_order=incoming.sort_order,item_data=incoming.item_data""",
                    (row["collection_name"], row["item_key"], row["sort_order"], row["item_data"]))
            for row in snapshot["courses"]:
                cursor.execute("""INSERT INTO courses (code,slug,title,description,image,alt,href,cta_label,detail,sort_order,is_published)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS incoming
                    ON DUPLICATE KEY UPDATE title=incoming.title,description=incoming.description,image=incoming.image,alt=incoming.alt,
                    href=incoming.href,cta_label=incoming.cta_label,detail=incoming.detail,sort_order=incoming.sort_order,is_published=incoming.is_published""",
                    tuple(row[key] for key in ("code","slug","title","description","image","alt","href","cta_label","detail","sort_order","is_published")))
            for row in snapshot["articles"]:
                cursor.execute("""INSERT INTO articles (slug,title,excerpt,category,image,alt,published_date,href,detail,status,scheduled_posting_at,posted_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS incoming
                    ON DUPLICATE KEY UPDATE title=incoming.title,excerpt=incoming.excerpt,category=incoming.category,image=incoming.image,
                    alt=incoming.alt,published_date=incoming.published_date,href=incoming.href,detail=incoming.detail,status=incoming.status,
                    scheduled_posting_at=incoming.scheduled_posting_at,posted_at=incoming.posted_at""",
                    tuple(row[key] for key in ("slug","title","excerpt","category","image","alt","published_date","href","detail","status","scheduled_posting_at","posted_at")))
        connection.commit()
    finally:
        connection.close()
    print("Imported content snapshot.")


if __name__ == "__main__":
    main()
