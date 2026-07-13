"""Create and bootstrap the CAIM production MySQL database.

This script is idempotent and never stores the MySQL administrator password.
Provide MYSQL_ADMIN_PASSWORD through the environment or a protected env file.
"""

import os
import re
from pathlib import Path

import pymysql
from dotenv import dotenv_values, load_dotenv
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]


def env_value(name, values):
    return os.getenv(name) or values.get(name)


def execute_schema(connection):
    statements = (ROOT / "scripts" / "schema.sql").read_text(encoding="utf-8").split(";")
    with connection.cursor() as cursor:
        for statement in statements:
            if statement.strip():
                cursor.execute(statement)


def main():
    load_dotenv(ROOT / ".env")
    bootstrap_values = dotenv_values(os.getenv("CAIM_BOOTSTRAP_ENV", "")) if os.getenv("CAIM_BOOTSTRAP_ENV") else {}
    host = env_value("MYSQL_ADMIN_HOST", bootstrap_values) or env_value("DB_HOST", bootstrap_values) or "127.0.0.1"
    port = int(env_value("MYSQL_ADMIN_PORT", bootstrap_values) or env_value("DB_PORT", bootstrap_values) or 3306)
    socket_path = env_value("MYSQL_ADMIN_SOCKET", bootstrap_values)
    admin_user = env_value("MYSQL_ADMIN_USER", bootstrap_values) or "root"
    admin_password = env_value("MYSQL_ADMIN_PASSWORD", bootstrap_values)
    app_password = env_value("DB_PASSWORD", bootstrap_values)
    if not admin_password:
        raise SystemExit("MYSQL_ADMIN_PASSWORD is required")
    if not app_password:
        raise SystemExit("DB_PASSWORD is required")

    database = env_value("DB_NAME", bootstrap_values) or "caimdb"
    app_user = env_value("DB_USER", bootstrap_values) or "caimadmin"
    if not re.fullmatch(r"[A-Za-z0-9_]+", app_user) or not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise SystemExit("DB_NAME and DB_USER may contain only letters, numbers, and underscores")
    connection_options = {"user": admin_user, "password": admin_password, "charset": "utf8mb4", "autocommit": True}
    if socket_path:
        connection_options["unix_socket"] = socket_path
    else:
        connection_options.update({"host": host, "port": port})
    connection = pymysql.connect(**connection_options)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"CREATE USER IF NOT EXISTS `{app_user}`@'%%' IDENTIFIED BY %s", (app_password,))
            cursor.execute(f"ALTER USER `{app_user}`@'%%' IDENTIFIED BY %s", (app_password,))
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{database}`.* TO `{app_user}`@'%%'")
            cursor.execute("FLUSH PRIVILEGES")
        connection.select_db(database)
        execute_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute("INSERT IGNORE INTO admin_users (username,password_hash) VALUES ('admin',%s)",
                (generate_password_hash("New2P@ss"),))
        connection.commit()
    finally:
        connection.close()
    print(f"Database {database} and application user {app_user} are ready.")


if __name__ == "__main__":
    main()
