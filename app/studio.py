import hmac
import re
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from docx import Document
from flask import current_app
from pypdf import PdfReader
from werkzeug.utils import secure_filename


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
SOURCE_EXTENSIONS = {".md", ".txt", ".docx", ".pdf"}


def csrf_token():
    secret = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.digest(secret, b"caim-article-studio", "sha256").hex()


def validate_csrf(value):
    return hmac.compare_digest(value or "", csrf_token())


def extract_source_text(upload):
    if not upload or not upload.filename:
        return "", ""
    filename = secure_filename(upload.filename)
    extension = Path(filename).suffix.lower()
    if extension not in SOURCE_EXTENSIONS:
        raise ValueError("文章來源只支援 md、txt、docx 或 pdf。")
    data = upload.read()
    if extension in {".md", ".txt"}:
        return data.decode("utf-8-sig"), filename
    if extension == ".docx":
        document = Document(BytesIO(data))
        return "\n\n".join(p.text.strip() for p in document.paragraphs if p.text.strip()), filename
    reader = PdfReader(BytesIO(data))
    page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(text for text in page_text if text), filename


def save_hero_image(upload):
    if not upload or not upload.filename:
        return None
    extension = Path(secure_filename(upload.filename)).suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        raise ValueError("Hero Image 只支援 JPG、PNG、WebP 或 AVIF。")
    directory = Path(current_app.static_folder) / "assets" / "articles"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    upload.save(directory / filename)
    return f"/assets/articles/{filename}"


def save_course_image(upload):
    if not upload or not upload.filename:
        return None
    extension = Path(secure_filename(upload.filename)).suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        raise ValueError("Course image supports JPG, PNG, WebP, or AVIF only.")
    directory = Path(current_app.static_folder) / "assets" / "courses"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    upload.save(directory / filename)
    return f"/assets/courses/{filename}"


def remove_uploaded_image(image_path):
    prefix = "/assets/articles/"
    if not image_path or not image_path.startswith(prefix):
        return
    target = (Path(current_app.static_folder) / image_path.lstrip("/")).resolve()
    upload_root = (Path(current_app.static_folder) / "assets" / "articles").resolve()
    if upload_root in target.parents and target.exists():
        target.unlink()


def split_paragraphs(body):
    return [block.strip() for block in re.split(r"\n\s*\n", body or "") if block.strip()]


def build_article(form, source_file, hero_image, existing=None):
    title = form.get("title", "").strip()
    slug = form.get("slug", "").strip().lower()
    if not title:
        raise ValueError("文章標題不能留空。")
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug 只能使用小寫英文字母、數字和連字號。")

    extracted_body, source_filename = extract_source_text(source_file)
    body = form.get("body", "").strip() or extracted_body
    if not body:
        raise ValueError("文章內容不能留空。")
    image = save_hero_image(hero_image)
    old_image = (existing or {}).get("image", "")
    if old_image and (image or form.get("remove_image") == "1"):
        remove_uploaded_image(old_image)
    if not image and form.get("remove_image") != "1":
        image = form.get("existing_image", "").strip()
    if not image and existing and form.get("remove_image") != "1":
        image = existing.get("image", "")
    image = image or "/assets/hero-asian-creative-team.jpg"
    lead = form.get("lead", "").strip()
    description = form.get("description", "").strip() or lead
    topics = [item.strip() for item in form.get("topics", "").split(",") if item.strip()]
    published_date = form.get("date", "").strip() or date.today().isoformat()
    datetime.strptime(published_date, "%Y-%m-%d")
    schedule_value = form.get("scheduled_posting_at", "").strip()
    if existing and existing.get("status") == "posted":
        scheduled_at = existing.get("scheduled_posting_at")
    else:
        scheduled_at = datetime.strptime(schedule_value, "%Y-%m-%dT%H:%M") if schedule_value else datetime.now()
    action = form.get("action")
    status = "review" if action == "post" else (existing.get("status") if existing and existing.get("status") == "posted" else "saved")
    detail = {
        "author": form.get("author", "CAIM").strip() or "CAIM",
        "updatedAt": published_date,
        "metaTitle": form.get("meta_title", "").strip() or title,
        "lead": lead,
        "description": description,
        "body": body,
        "paragraphs": split_paragraphs(body),
        "relatedTopics": [{"label": topic, "href": "/articles/"} for topic in topics],
        "sourceFileName": source_filename or (existing or {}).get("detail", {}).get("sourceFileName", ""),
    }
    return {
        "slug": slug,
        "title": title,
        "excerpt": lead or description or body[:240],
        "category": form.get("category", "AI 與教會").strip() or "AI 與教會",
        "image": image,
        "alt": form.get("image_alt", "").strip() or title,
        "published_date": published_date,
        "href": f"/articles/{slug}/",
        "detail": detail,
        "status": status,
        "scheduled_posting_at": scheduled_at,
        "posted_at": (existing or {}).get("posted_at"),
    }
