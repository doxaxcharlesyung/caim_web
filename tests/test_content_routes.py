import re
import time
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from app import create_app


class ContentRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app({"TESTING": True})
        cls.client = cls.app.test_client()

    def assert_page_contains(self, path, expected):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(expected, response.get_data(as_text=True))

    def test_course_listing_and_details_are_database_backed(self):
        self.assert_page_contains("/courses/", "教會AI應用全方位工作坊")
        self.assert_page_contains("/courses/mt101/", "每人加幣150")
        self.assert_page_contains("/courses/mt210/", "MT210")

        root = Path(__file__).resolve().parents[1]
        styles = (root / "static" / "css" / "v3" / "pages" / "courses.css").read_text(encoding="utf-8")
        self.assertIn("flex: 1", styles)
        self.assertIn("margin-top: auto", styles)
        self.assert_page_contains("/courses/", "bottom-aligned-cta")

    def test_requested_article_contains_migrated_body(self):
        self.assert_page_contains(
            "/articles/human-machine-coexistence-ai-tools-vs-ai-risk/",
            "AI進步的速度讓我感到驚訝",
        )

    def test_unknown_database_content_returns_404(self):
        self.assertEqual(self.client.get("/courses/not-a-course/").status_code, 404)
        self.assertEqual(self.client.get("/articles/not-an-article/").status_code, 404)

    def test_homepage_news_accordion_renders_the_latest_five_items(self):
        from app.content import get_news_items
        with self.app.app_context():
            expected_count = min(5, len(get_news_items()))
        page = self.client.get("/").get_data(as_text=True)
        self.assertEqual(page.count('class="news-item reveal"'), expected_count)
        root = Path(__file__).resolve().parents[1]
        styles = (root / "static" / "css" / "v3" / "pages" / "index.css").read_text(encoding="utf-8")
        overrides = (root / "static" / "css" / "v3" / "overrides.css").read_text(encoding="utf-8")
        self.assertIn(".news-list", styles)
        self.assertIn(".news-item", styles)
        self.assertIn("min-height: clamp(600px, 68vh, 720px)", styles)
        self.assertIn("hero-height-cap", self.client.get("/").get_data(as_text=True))
        self.assertIn("animation: marquee 100s linear infinite !important", overrides)
        self.assertIn("animation-play-state: paused", overrides)
        self.assertIn(".transform-section .transform-copy .info-card h3", styles)
        self.assertIn("color: #fff", styles)
        self.assertIn("font-size: clamp(2.25rem, 3.85vw, 4.15rem)", overrides)
        self.assertIn("font-size: clamp(1.85rem, 8.7vw, 2.55rem)", overrides)
        self.assertIn(".page-hero h1", overrides)
        self.assertNotIn(".page-hero:not(.article-detail):not(.course-detail) h1", overrides)

        global_styles = (root / "static" / "css" / "v3" / "global.css").read_text(encoding="utf-8")
        self.assertIn("padding: 112px 0 28px", global_styles)
        self.assertIn("padding: 96px 0 20px", global_styles)
        self.assertNotIn("about-hero", self.client.get("/about/").get_data(as_text=True))
        for path in ("/about/", "/courses/", "/contact/", "/dx-sermon/", "/missionaries/"):
            self.assertIn("compact-page-hero", self.client.get(path).get_data(as_text=True))


class PublicCRMIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app({"TESTING": True, "SERVER_NAME": "localhost:8021"})
        cls.client = cls.app.test_client()

    def test_contact_submits_dx_crm_consultation_fields(self):
        with patch("app.routes.submit_consultation_request", return_value=(True, "")) as submit:
            response = self.client.post("/contact/", data={
                "name": "Avery Stone",
                "organization": "Example Church",
                "email": "avery@example.com",
                "phone": "555-0110",
                "type": "General inquiry",
                "message": "Please contact me.",
            })
        self.assertEqual(response.status_code, 200)
        payload = submit.call_args.args[0]
        self.assertEqual(payload["source"], "caim.doxaxsolutions.com")
        self.assertEqual(payload["type"], "General inquiry")
        self.assertEqual(payload["message"], "Please contact me.")

    def test_course_registration_submits_selected_activity(self):
        results = [
            (True, "", {"registration_id": 901, "activity_id": None}),
            (True, "", {"registration_id": 902, "activity_id": None}),
        ]
        with patch("app.routes.submit_activity_registration", side_effect=results) as submit:
            response = self.client.post("/course-registration/", data={
                "course_slug": "mt101",
                "english_name": "Ming Wang",
                "chinese_full_name": "Wang Ming",
                "church_name": "Example Church",
                "email": "ming@example.com",
                "mobile": "555-0100",
                "ministry_experience": "5 years",
                "notes": "No dietary restrictions",
            })
            second_response = self.client.post("/course-registration/", data={
                "course_slug": "mt101",
                "english_name": "Avery Stone",
                "church_name": "Another Church",
                "email": "avery@example.com",
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn("901", response.get_data(as_text=True))
        self.assertIn("902", second_response.get_data(as_text=True))
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["last_activity_registration_id"], 902)
        payload = submit.call_args_list[0].args[0]
        second_payload = submit.call_args_list[1].args[0]
        self.assertNotIn("activity_id", payload)
        self.assertEqual(payload["activity_type"], "course")
        self.assertEqual(payload["activity_key"], "mt101")
        self.assertEqual(second_payload["activity_key"], "mt101")
        self.assertEqual(payload["source_name"], "caim.doxaxsolutions.com")
        self.assertEqual(payload["source_url"], "https://caim.doxaxsolutions.com/")
        self.assertEqual(payload["email"], "ming@example.com")
        self.assertEqual(payload["questionnaire"]["ministry_experience"], "5 years")

    def test_course_registration_preserves_values_after_api_error(self):
        with patch("app.routes.submit_activity_registration", return_value=(False, "CRM unavailable", None)):
            response = self.client.post("/course-registration/", data={
                "course_slug": "mt101",
                "english_name": "Ming Wang",
                "church_name": "Example Church",
                "email": "ming@example.com",
                "notes": "Keep this note",
            })
        body = response.get_data(as_text=True)
        self.assertIn('value="ming@example.com"', body)
        self.assertIn("Keep this note", body)
        self.assertIn("CRM unavailable", body)

    def test_course_detail_preselects_registration_activity(self):
        body = self.client.get("/courses/mt101/").get_data(as_text=True)
        self.assertIn("course=mt101", body)

    def test_registration_form_labels_are_translated(self):
        body = self.client.get("/course-registration/?lang=en").get_data(as_text=True)
        self.assertIn("Select course", body)
        self.assertIn("English name", body)
        self.assertIn("Submit registration", body)

    def test_activity_client_uses_configured_url_and_server_side_token(self):
        from app.crm import submit_activity_registration

        with patch.dict("os.environ", {
            "CRM_ACTIVITY_REGISTRATION_URL": "http://127.0.0.1:8000/api/v1/public/activity-registration",
            "CRM_ACTIVITY_TOKEN": "activity-secret",
        }), patch("app.crm.httpx.post") as post:
            post.return_value.status_code = 201
            post.return_value.json.return_value = {"registration_id": 42, "activity_id": None}
            submitted, error, result = submit_activity_registration({"email": "ming@example.com"})
        self.assertTrue(submitted)
        self.assertEqual(error, "")
        self.assertEqual(result["registration_id"], 42)
        self.assertIsNone(result["activity_id"])
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:8000/api/v1/public/activity-registration")
        self.assertEqual(post.call_args.kwargs["headers"]["X-Activity-Token"], "activity-secret")

    def test_activity_client_handles_401_and_422(self):
        from app.crm import submit_activity_registration

        with patch.dict("os.environ", {"CRM_ACTIVITY_REGISTRATION_URL": "https://crm.example/register"}):
            for status, expected in ((401, "token is invalid or missing"), (422, "information is invalid")):
                with self.subTest(status=status), patch("app.crm.httpx.post") as post:
                    post.return_value.status_code = status
                    submitted, error, result = submit_activity_registration({"email": "invalid"})
                self.assertFalse(submitted)
                self.assertIn(expected, error)
                self.assertIsNone(result)


class ArticleStudioTests(unittest.TestCase):
    slug = "article-studio-automated-test"
    course_slug = "content-manager-course-test"
    news_slug = "content-manager-news-test"
    append_slugs = ("append-article-one", "append-article-two", "append-course-one", "append-course-two", "append-news-one", "append-news-two")

    @classmethod
    def setUpClass(cls):
        cls.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "article-studio-test-secret",
        })
        cls.client = cls.app.test_client()
        login_page = cls.client.get("/content/content-manager").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', login_page).group(1)
        response = cls.client.post("/content/content-manager", data={"csrf_token": token, "username": "admin", "password": "New2P@ss"})
        assert response.status_code == 302
        from app.db import fetch_all
        with cls.app.app_context():
            from app.db import get_db
            with get_db().cursor() as cursor:
                cursor.execute("DELETE FROM articles WHERE slug IN (%s,%s)", cls.append_slugs[:2])
                cursor.execute("DELETE FROM courses WHERE slug IN (%s,%s)", cls.append_slugs[2:4])
                cursor.execute("DELETE FROM news WHERE slug IN (%s,%s)", cls.append_slugs[4:])
            cls.reviewer_ids = [str(row["id"]) for row in fetch_all(
                "SELECT id FROM admin_users WHERE username IN ('charles.yung','francis.lau') ORDER BY username"
            )]

    @classmethod
    def tearDownClass(cls):
        from app.content import delete_studio_article
        from app.db import get_db
        with cls.app.app_context():
            delete_studio_article(cls.slug)
            with get_db().cursor() as cursor:
                cursor.execute("SELECT image FROM courses WHERE slug=%s", (cls.course_slug,))
                course = cursor.fetchone()
                cursor.execute("DELETE FROM courses WHERE slug=%s", (cls.course_slug,))
                cursor.execute("DELETE FROM news WHERE slug=%s", (cls.news_slug,))
                cursor.execute("DELETE FROM content_approvals WHERE content_key IN (%s,%s,%s)",
                    (cls.slug, cls.course_slug, cls.news_slug))
                cursor.execute("DELETE FROM articles WHERE slug IN (%s,%s)", cls.append_slugs[:2])
                cursor.execute("DELETE FROM courses WHERE slug IN (%s,%s)", cls.append_slugs[2:4])
                cursor.execute("DELETE FROM news WHERE slug IN (%s,%s)", cls.append_slugs[4:])
            if course and course["image"].startswith("/assets/courses/"):
                (Path(cls.app.static_folder) / course["image"].lstrip("/")).unlink(missing_ok=True)

    def csrf_token(self):
        page = self.client.get("/content/article-studio").get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    def reviewer_client(self, username):
        client = self.app.test_client()
        page = client.get("/content/content-manager").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        response = client.post("/content/content-manager", data={
            "csrf_token": token, "username": username, "password": "New2P@ss"
        })
        self.assertEqual(response.status_code, 302)
        return client

    def approve_as_all_reviewers(self, kind, slug):
        for index, username in enumerate(("charles.yung", "francis.lau")):
            client = self.reviewer_client(username)
            page = client.get(f"/content/{kind}").get_data(as_text=True)
            token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
            response = client.post(f"/content/{kind}/{slug}/approve", data={"csrf_token": token})
            self.assertEqual(response.status_code, 302)
            if index == 0:
                public_path = f"/courses/{slug}/" if kind == "courses" else f"/articles/{slug}/"
                if kind != "news":
                    self.assertEqual(client.get(public_path).status_code, 404)

    def article_data(self, action):
        return {
            "csrf_token": self.csrf_token(),
            "action": action,
            "original_slug": self.slug if action == "post" else "",
            "title": "Article Studio automated test",
            "slug": self.slug,
            "category": "AI 與教會",
            "author": "CAIM",
            "date": "2026-07-13",
            "meta_title": "Article Studio automated test",
            "lead": "Database-backed article studio test.",
            "body": "First paragraph.\n\nSecond paragraph.",
            "topics": "所有文章,AI 與教會",
            "description": "Article Studio integration test.",
            "scheduled_posting_at": "2026-07-13T09:00",
            "reviewer_ids": self.reviewer_ids,
        }

    def test_authentication_and_publish_workflow(self):
        self.assertEqual(self.app.config["SESSION_COOKIE_NAME"], "caim_session")
        service = (
            Path(__file__).resolve().parents[1]
            / "deploy"
            / "systemd"
            / "doxax-caim-web.service"
        ).read_text(encoding="utf-8")
        self.assertIn("--limit-request-field_size 32768", service)
        apache_http = (
            Path(__file__).resolve().parents[1]
            / "deploy"
            / "apache"
            / "caim.doxaxsolutions.com.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("Redirect permanent / https://caim.doxaxsolutions.com/", apache_http)
        self.assertNotIn("ProxyPass /", apache_http)
        anonymous = self.app.test_client().get("/content/content-dashboard")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/content/content-manager", anonymous.location)
        self.assertNotIn("?next=", anonymous.location)

        response = self.client.post(
            "/content/article-studio", data=self.article_data("save")
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(f"/articles/{self.slug}/").status_code, 404)

    def test_course_and_news_management_workflows(self):
        token = self.csrf_token()
        course = {
            "csrf_token": token, "action": "post", "code": "TST901", "slug": self.course_slug,
            "content_type": "event", "sort_order": "99", "title": "Content Manager Workshop",
            "description": "Workshop managed from the course studio.", "image": "/assets/courses-training-courses.png",
            "alt": "Workshop", "cta_label": "Details", "eyebrow": "WORKSHOP", "subtitle": "Managed event",
            "body": "Workshop first paragraph.\n\nWorkshop second paragraph.", "scheduled_posting_at": "2026-01-01T09:00",
            "reviewer_ids": self.reviewer_ids,
        }
        course["course_image"] = (BytesIO(b"test-course-image"), "course-test.jpg")
        response = self.client.post("/content/course-studio", data=course, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(f"/courses/{self.course_slug}/").status_code, 404)
        self.approve_as_all_reviewers("courses", self.course_slug)
        public_course = self.client.get(f"/courses/{self.course_slug}/")
        self.assertEqual(public_course.status_code, 200)
        self.assertIn("Workshop second paragraph.", public_course.get_data(as_text=True))

        news = {
            "csrf_token": token, "action": "post", "slug": self.news_slug, "content_type": "news",
            "event_date": "2026-01-01", "date_label": "JAN. 01, 2026", "title": "Content Manager News Test",
            "content": "News migrated and managed in the normalized news table.", "scheduled_posting_at": "2026-01-01T09:00",
            "reviewer_ids": self.reviewer_ids,
        }
        response = self.client.post("/content/news-studio", data=news)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("Content Manager News Test", self.client.get("/").get_data(as_text=True))
        self.approve_as_all_reviewers("news", self.news_slug)
        home = self.client.get("/").get_data(as_text=True)
        with self.app.app_context():
            from app.content import get_news_items
            self.assertIn(self.news_slug, {item["slug"] for item in get_news_items()})
        self.assertLessEqual(home.count('class="news-item reveal"'), 5)
        dashboard = self.client.get("/content/content-dashboard").get_data(as_text=True)
        self.assertIn("Courses & Workshops", dashboard)
        self.assertIn("News & Events", dashboard)
        saved = self.client.get("/content/articles").get_data(as_text=True)
        self.assertIn(self.slug, saved)
        self.assertIn("Saved", saved)
        loaded = self.client.get(
            f"/content/article-studio?slug={self.slug}"
        ).get_data(as_text=True)
        self.assertIn("First paragraph.", loaded)
        self.assertIn("Database-backed article studio test.", loaded)

        response = self.client.post(
            "/content/article-studio", data=self.article_data("post")
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(f"/articles/{self.slug}/").status_code, 404)

    def test_new_content_appends_and_duplicate_keys_never_overwrite(self):
        from app.db import fetch_one

        article_base = self.article_data("save")
        for number, slug in enumerate(self.append_slugs[:2], 1):
            data = dict(article_base, original_slug="", slug=slug, title=f"Append Article {number}")
            self.assertEqual(self.client.post("/content/article-studio", data=data).status_code, 302)
        duplicate = dict(article_base, original_slug="", slug=self.append_slugs[0], title="Overwritten Article")
        response = self.client.post("/content/article-studio", data=duplicate)
        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists", response.get_data(as_text=True))

        course_base = {
            "csrf_token": self.csrf_token(), "action": "save", "original_slug": "", "content_type": "course",
            "sort_order": "100", "description": "Append protection course.", "image": "/assets/courses-training-courses.png",
            "alt": "Course", "cta_label": "Details", "body": "Course detail", "scheduled_posting_at": "2026-07-13T09:00",
        }
        for number, slug in enumerate(self.append_slugs[2:4], 1):
            data = dict(course_base, slug=slug, code=f"APP90{number}", title=f"Append Course {number}")
            self.assertEqual(self.client.post("/content/course-studio", data=data).status_code, 302)
        duplicate = dict(course_base, slug="different-course-slug", code="APP901", title="Overwritten Course")
        response = self.client.post("/content/course-studio", data=duplicate)
        self.assertEqual(response.status_code, 200)
        self.assertIn("course code", response.get_data(as_text=True))

        news_base = {
            "csrf_token": self.csrf_token(), "action": "save", "original_slug": "", "content_type": "news",
            "event_date": "2026-07-13", "date_label": "JUL. 13, 2026", "content": "Append protection news.",
            "scheduled_posting_at": "2026-07-13T09:00",
        }
        for number, slug in enumerate(self.append_slugs[4:], 1):
            data = dict(news_base, slug=slug, title=f"Append News {number}")
            self.assertEqual(self.client.post("/content/news-studio", data=data).status_code, 302)
        duplicate = dict(news_base, slug=self.append_slugs[4], title="Overwritten News")
        response = self.client.post("/content/news-studio", data=duplicate)
        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists", response.get_data(as_text=True))

        with self.app.app_context():
            self.assertEqual(fetch_one("SELECT COUNT(*) total FROM articles WHERE slug LIKE %s", ("append-article-%",))["total"], 2)
            self.assertEqual(fetch_one("SELECT title FROM articles WHERE slug=%s", (self.append_slugs[0],))["title"], "Append Article 1")
            self.assertEqual(fetch_one("SELECT COUNT(*) total FROM courses WHERE slug LIKE %s", ("append-course-%",))["total"], 2)
            self.assertEqual(fetch_one("SELECT title FROM courses WHERE slug=%s", (self.append_slugs[2],))["title"], "Append Course 1")
            self.assertEqual(fetch_one("SELECT COUNT(*) total FROM news WHERE slug LIKE %s", ("append-news-%",))["total"], 2)
            self.assertEqual(fetch_one("SELECT title FROM news WHERE slug=%s", (self.append_slugs[4],))["title"], "Append News 1")
        self.approve_as_all_reviewers("articles", self.slug)
        public = self.client.get(f"/articles/{self.slug}/")
        self.assertEqual(public.status_code, 200)
        self.assertIn("Second paragraph.", public.get_data(as_text=True))

        response = self.client.post(f"/content/articles/{self.slug}/status",
            data={"csrf_token": self.csrf_token(), "status": "deleted"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(f"/articles/{self.slug}/").status_code, 404)


class ContentSessionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "session-test-secret"})
        self.client = self.app.test_client()
        page = self.client.get("/content/content-manager").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        self.client.post("/content/content-manager", data={
            "csrf_token": token, "username": "admin", "password": "New2P@ss"
        })

    def test_content_pages_have_logout_and_default_schedule_now(self):
        dashboard = self.client.get("/content/content-dashboard").get_data(as_text=True)
        self.assertGreaterEqual(dashboard.count(">Logout<"), 2)
        page = self.client.get("/content/course-studio").get_data(as_text=True)
        self.assertIn(">Logout<", page)
        scheduled = re.search(r'name="scheduled_posting_at"[^>]*value="([^"]+)"', page).group(1)
        self.assertRegex(scheduled, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
        self.assertIn('name="course_image"', page)

    def test_idle_session_expires_after_sixty_minutes(self):
        with self.client.session_transaction() as session:
            session["last_activity"] = time.time() - 3601
        response = self.client.get("/content/content-dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/content/content-manager", response.location)

    def test_restart_epoch_invalidates_existing_session(self):
        with self.client.session_transaction() as session:
            session["session_epoch"] = "previous-service-invocation"
        response = self.client.get("/content/content-dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/content/content-manager", response.location)

    def test_only_other_user_is_default_reviewer(self):
        from app.approval import reviewer_options
        with patch("app.approval.available_reviewers", return_value=[{"id": 22, "username": "other.user"}]):
            options = reviewer_options(11)
        self.assertEqual(options, [{"id": 22, "username": "other.user", "selected": True}])

    def test_validation_error_preserves_news_fields(self):
        page = self.client.get("/content/news-studio").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        response = self.client.post("/content/news-studio", data={
            "csrf_token": token,
            "action": "post",
            "content_type": "event",
            "event_date": "2026-08-15",
            "title": "Preserve this unsaved event",
            "slug": "preserve-unsaved-event",
            "date_label": "AUG. 15, 2026",
            "content": "This entered content must remain after reviewer validation fails.",
            "scheduled_posting_at": "2026-08-15T14:30",
        })
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Select at least one active reviewer", body)
        self.assertIn('value="Preserve this unsaved event"', body)
        self.assertIn("This entered content must remain", body)
        self.assertIn('value="2026-08-15T14:30"', body)
        self.assertRegex(body, r'<option value="event"[^>]*selected')

    def test_admin_is_excluded_and_francis_defaults_for_charles(self):
        client = self.app.test_client()
        login = client.get("/content/content-manager").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', login).group(1)
        client.post("/content/content-manager", data={
            "csrf_token": token, "username": "charles.yung", "password": "New2P@ss"
        })
        page = client.get("/content/article-studio").get_data(as_text=True)
        reviewer_section = re.search(r'<fieldset class="reviewer-picker.*?</fieldset>', page, re.S).group(0)
        self.assertNotIn(">admin<", reviewer_section)
        self.assertRegex(reviewer_section, r'name="reviewer_ids"[^>]*checked[^>]*>francis\.lau')


if __name__ == "__main__":
    unittest.main()
