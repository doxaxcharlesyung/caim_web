import json
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]


def column_exists(cursor, table, column):
    cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
    return cursor.fetchone() is not None


def main():
    load_dotenv(ROOT / ".env")
    connection = pymysql.connect(host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "caimadmin"), password=os.environ["DB_PASSWORD"], database=os.getenv("DB_NAME", "caimdb"), charset="utf8mb4")
    try:
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE articles MODIFY status VARCHAR(20) NOT NULL DEFAULT 'posted'")
            cursor.execute("UPDATE articles SET status='saved' WHERE status='draft'")
            cursor.execute("UPDATE articles SET status='posted' WHERE status='published'")
            if not column_exists(cursor, "articles", "scheduled_posting_at"):
                cursor.execute("ALTER TABLE articles ADD scheduled_posting_at DATETIME NULL AFTER status")
            if not column_exists(cursor, "articles", "posted_at"):
                cursor.execute("ALTER TABLE articles ADD posted_at DATETIME NULL AFTER scheduled_posting_at")
            cursor.execute("UPDATE articles SET scheduled_posting_at=COALESCE(scheduled_posting_at,published_date), posted_at=COALESCE(posted_at,updated_at) WHERE status='posted'")
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_users (id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,password_hash VARCHAR(255) NOT NULL,is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_reviewer BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
                CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""")
            if not column_exists(cursor, "admin_users", "is_reviewer"):
                cursor.execute("ALTER TABLE admin_users ADD is_reviewer BOOLEAN NOT NULL DEFAULT FALSE AFTER is_active")
            cursor.execute("INSERT IGNORE INTO admin_users (username,password_hash) VALUES ('admin',%s)", (generate_password_hash("New2P@ss"),))
            for username in ("charles.yung", "francis.lau"):
                cursor.execute("INSERT IGNORE INTO admin_users (username,password_hash,is_reviewer) VALUES (%s,%s,1)",
                    (username, generate_password_hash("New2P@ss")))
                cursor.execute("UPDATE admin_users SET is_active=1,is_reviewer=1 WHERE username=%s", (username,))
            course_status_added = not column_exists(cursor, "courses", "status")
            for column, definition in {
                "content_type": "VARCHAR(20) NOT NULL DEFAULT 'course' AFTER is_published",
                "status": "VARCHAR(20) NOT NULL DEFAULT 'posted' AFTER content_type",
                "scheduled_posting_at": "DATETIME NULL AFTER status",
                "posted_at": "DATETIME NULL AFTER scheduled_posting_at",
            }.items():
                if not column_exists(cursor, "courses", column):
                    cursor.execute(f"ALTER TABLE courses ADD `{column}` {definition}")
            if course_status_added:
                cursor.execute("UPDATE courses SET status=IF(is_published=1,'posted','saved')")
            cursor.execute("UPDATE courses SET posted_at=COALESCE(posted_at,updated_at) WHERE status='posted'")
            cursor.execute("""CREATE TABLE IF NOT EXISTS news (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,slug VARCHAR(191) NOT NULL UNIQUE,
                title VARCHAR(500) NOT NULL,event_date DATE NOT NULL,date_label VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,content_type VARCHAR(20) NOT NULL DEFAULT 'news',status VARCHAR(20) NOT NULL DEFAULT 'posted',
                scheduled_posting_at DATETIME NULL,posted_at DATETIME NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                KEY ix_news_status_date (status,event_date)) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""")
            cursor.execute("SELECT item_key,item_data FROM content_items WHERE collection_name='newsItems' ORDER BY sort_order,id")
            for row in cursor.fetchall():
                item = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                cursor.execute("""INSERT IGNORE INTO news
                    (slug,title,event_date,date_label,content,content_type,status,scheduled_posting_at,posted_at)
                    VALUES (%s,%s,%s,%s,%s,'news','posted',%s,NOW())""",
                    (row[0].lower().replace("_", "-"), item["title"], item["date"], item.get("dateLabel", ""), item["content"], item["date"]))
            cursor.execute("""CREATE TABLE IF NOT EXISTS content_approvals (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,content_type VARCHAR(20) NOT NULL,
                content_key VARCHAR(191) NOT NULL,submitted_by BIGINT UNSIGNED NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME NULL,UNIQUE KEY uq_content_approval (content_type,content_key),
                KEY ix_approval_status (status,submitted_at)) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS content_approval_reviewers (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,approval_id BIGINT UNSIGNED NOT NULL,
                reviewer_id BIGINT UNSIGNED NOT NULL,assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_approval_assigned_reviewer (approval_id,reviewer_id),
                CONSTRAINT fk_reviewer_approval FOREIGN KEY (approval_id) REFERENCES content_approvals(id) ON DELETE CASCADE)
                CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS content_approval_votes (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,approval_id BIGINT UNSIGNED NOT NULL,
                reviewer_id BIGINT UNSIGNED NOT NULL,approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_approval_reviewer (approval_id,reviewer_id),
                CONSTRAINT fk_vote_approval FOREIGN KEY (approval_id) REFERENCES content_approvals(id) ON DELETE CASCADE)
                CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""")
            cursor.execute("""INSERT IGNORE INTO content_approval_reviewers (approval_id,reviewer_id)
                SELECT a.id,u.id FROM content_approvals a JOIN admin_users u
                ON u.is_active=1 AND u.is_reviewer=1 AND u.id<>a.submitted_by
                WHERE a.status='pending'""")
        connection.commit()
        print("Content manager schema migrated; article, course, news, and admin data are ready.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
