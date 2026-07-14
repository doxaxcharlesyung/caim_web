import json
import os
import sys
import argparse
from datetime import date, datetime
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat(" ") if isinstance(value, datetime) else value.isoformat()
    raise TypeError(f"Unsupported value: {type(value)!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env")
    connection = pymysql.connect(host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "caimadmin"), password=os.environ["DB_PASSWORD"], database=os.getenv("DB_NAME", "caimdb"),
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            snapshot = {}
            for table, query in {
                "page_content": "SELECT content_key,title,subtitle,sections FROM page_content ORDER BY id",
                "content_items": "SELECT collection_name,item_key,sort_order,item_data FROM content_items ORDER BY collection_name,sort_order,id",
                "courses": "SELECT code,slug,title,description,image,alt,href,cta_label,detail,sort_order,is_published,content_type,original_locale,status,scheduled_posting_at,posted_at FROM courses WHERE status<>'deleted' ORDER BY sort_order,id",
                "articles": "SELECT slug,title,excerpt,category,image,alt,published_date,href,detail,status,original_locale,scheduled_posting_at,posted_at FROM articles WHERE status<>'deleted' ORDER BY id",
                "news": "SELECT slug,title,event_date,date_label,content,content_type,original_locale,status,scheduled_posting_at,posted_at FROM news WHERE status<>'deleted' ORDER BY event_date DESC,id",
                "content_translations": "SELECT content_type,content_key,locale,source_locale,payload,status,scheduled_posting_at,posted_at FROM content_translations ORDER BY content_type,content_key,locale",
            }.items():
                cursor.execute(query)
                snapshot[table] = cursor.fetchall()
        rendered = json.dumps(snapshot, ensure_ascii=False, indent=2, default=json_default) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
            print(f"Wrote {args.output}")
        else:
            print(rendered, end="")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
