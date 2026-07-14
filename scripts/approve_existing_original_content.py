import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_KEY = "approve-existing-original-content-v1"
CONTENT_TABLES = {
    "articles": "articles",
    "courses": "courses",
    "news": "news",
}


def main():
    load_dotenv(ROOT / ".env")
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "caimadmin"),
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME", "caimdb"),
        charset="utf8mb4",
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS app_migrations (
                migration_key VARCHAR(191) PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""")
            cursor.execute("SELECT 1 FROM app_migrations WHERE migration_key=%s", (MIGRATION_KEY,))
            if cursor.fetchone():
                print("Existing original content approval migration was already applied.")
                connection.commit()
                return

            cursor.execute("SELECT id FROM admin_users WHERE username='admin' LIMIT 1")
            admin = cursor.fetchone()
            if not admin:
                raise RuntimeError("The seeded admin user is required before approving legacy content.")
            admin_id = admin[0]

            approved_counts = {}
            for content_type, table in CONTENT_TABLES.items():
                publish_extra = ",is_published=1" if table == "courses" else ""
                cursor.execute(
                    f"""UPDATE `{table}` SET status='posted',posted_at=COALESCE(posted_at,NOW()){publish_extra}
                    WHERE status NOT IN ('expired','deleted')"""
                )
                approved_counts[content_type] = cursor.rowcount
                cursor.execute(
                    f"""INSERT INTO content_approvals
                    (content_type,content_key,locale,submitted_by,status,submitted_at,approved_at)
                    SELECT %s,slug,original_locale,%s,'approved',NOW(),NOW()
                    FROM `{table}` WHERE status='posted'
                    ON DUPLICATE KEY UPDATE status='approved',approved_at=COALESCE(approved_at,NOW())""",
                    (content_type, admin_id),
                )

            cursor.execute("""INSERT IGNORE INTO content_approval_votes (approval_id,reviewer_id)
                SELECT r.approval_id,r.reviewer_id
                FROM content_approval_reviewers r
                JOIN content_approvals a ON a.id=r.approval_id
                WHERE a.status='approved'""")
            cursor.execute("INSERT INTO app_migrations (migration_key) VALUES (%s)", (MIGRATION_KEY,))
        connection.commit()
        summary = ", ".join(f"{kind}={count}" for kind, count in approved_counts.items())
        print(f"Existing original content approved and posted ({summary}).")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
