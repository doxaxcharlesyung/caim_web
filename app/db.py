import json

import pymysql
from flask import current_app, g
from pymysql.cursors import DictCursor


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,
        )
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def fetch_all(query, params=()):
    with get_db().cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def fetch_one(query, params=()):
    with get_db().cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def decode_json_fields(record, *fields):
    if not record:
        return record
    for field in fields:
        value = record.get(field)
        if isinstance(value, str):
            record[field] = json.loads(value)
    return record
