import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]


def column_exists(cursor, column):
    cursor.execute("SHOW COLUMNS FROM articles LIKE %s", (column,))
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
            if not column_exists(cursor, "scheduled_posting_at"):
                cursor.execute("ALTER TABLE articles ADD scheduled_posting_at DATETIME NULL AFTER status")
            if not column_exists(cursor, "posted_at"):
                cursor.execute("ALTER TABLE articles ADD posted_at DATETIME NULL AFTER scheduled_posting_at")
            cursor.execute("UPDATE articles SET scheduled_posting_at=COALESCE(scheduled_posting_at,published_date), posted_at=COALESCE(posted_at,updated_at) WHERE status='posted'")
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_users (id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,password_hash VARCHAR(255) NOT NULL,is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)
                CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""")
            cursor.execute("INSERT IGNORE INTO admin_users (username,password_hash) VALUES ('admin',%s)", (generate_password_hash("New2P@ss"),))
        connection.commit()
        print("Article dashboard schema migrated; initial admin user is available.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
