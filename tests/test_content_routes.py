import re
import unittest

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

    def test_requested_article_contains_migrated_body(self):
        self.assert_page_contains(
            "/articles/human-machine-coexistence-ai-tools-vs-ai-risk/",
            "AI進步的速度讓我感到驚訝",
        )

    def test_unknown_database_content_returns_404(self):
        self.assertEqual(self.client.get("/courses/not-a-course/").status_code, 404)
        self.assertEqual(self.client.get("/articles/not-an-article/").status_code, 404)


class ArticleStudioTests(unittest.TestCase):
    slug = "article-studio-automated-test"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "article-studio-test-secret",
        })
        cls.client = cls.app.test_client()
        login_page = cls.client.get("/article-dashboard/login/").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', login_page).group(1)
        response = cls.client.post("/article-dashboard/login/", data={"csrf_token": token, "username": "admin", "password": "New2P@ss"})
        assert response.status_code == 302

    @classmethod
    def tearDownClass(cls):
        from app.content import delete_studio_article
        with cls.app.app_context():
            delete_studio_article(cls.slug)

    def csrf_token(self):
        page = self.client.get("/article-studio/").get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

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
        }

    def test_authentication_and_publish_workflow(self):
        self.assertEqual(self.app.config["SESSION_COOKIE_NAME"], "caim_session")
        anonymous = self.app.test_client().get("/article-dashboard/")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/article-dashboard/login/", anonymous.location)
        self.assertNotIn("?next=", anonymous.location)

        response = self.client.post(
            "/article-studio/", data=self.article_data("save")
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(f"/articles/{self.slug}/").status_code, 404)
        saved = self.client.get("/article-dashboard/").get_data(as_text=True)
        self.assertIn(self.slug, saved)
        self.assertIn("Saved", saved)
        loaded = self.client.get(
            f"/article-studio/?slug={self.slug}"
        ).get_data(as_text=True)
        self.assertIn("First paragraph.", loaded)
        self.assertIn("Database-backed article studio test.", loaded)

        response = self.client.post(
            "/article-studio/", data=self.article_data("post")
        )
        self.assertEqual(response.status_code, 302)
        public = self.client.get(f"/articles/{self.slug}/")
        self.assertEqual(public.status_code, 200)
        self.assertIn("Second paragraph.", public.get_data(as_text=True))

        response = self.client.post(f"/article-dashboard/articles/{self.slug}/status/",
            data={"csrf_token": self.csrf_token(), "status": "deleted"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(f"/articles/{self.slug}/").status_code, 404)


if __name__ == "__main__":
    unittest.main()
