import unittest
import re
import json
import html
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.content import get_content_translation, save_content_translation
from app.db import get_db
from app.translation import translate_payload
from app.i18n import CATALOG
from scripts.build_static_translations import template_strings


class PublicLocaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app({"TESTING": True, "SECRET_KEY": "locale-test"})
        cls.client = cls.app.test_client()

    def test_homepage_renders_all_enabled_locales_as_utf8(self):
        expected = {
            "zh-Hant": "辨識．轉化．同行",
            "zh-Hans": "辨识．转化．同行",
            "en": "Discern. Transform.",
            "fr": "Discerner. Transformer.",
            "es": "Discernir. Transformar.",
        }
        for locale, heading in expected.items():
            with self.subTest(locale=locale):
                response = self.client.get(f"/?lang={locale}")
                body = response.data.decode("utf-8", errors="strict")
                self.assertEqual(response.status_code, 200)
                self.assertIn(f'<html lang="{locale}">', body)
                self.assertIn(heading, body)
                self.assertNotIn("\ufffd", body)

    def test_language_selector_is_available_on_detail_and_error_pages(self):
        for path in ("/courses/mt101/?lang=en", "/articles/not-an-article/?lang=zh-Hans"):
            with self.subTest(path=path):
                body = self.client.get(path).get_data(as_text=True)
                self.assertIn("English", body)
                self.assertIn("简体中文", body)
                self.assertNotIn("Français", body)
                self.assertNotIn("Español", body)

    def test_header_cta_is_short_in_western_languages(self):
        expected = {"en": "Book"}
        for locale, label in expected.items():
            with self.subTest(locale=locale):
                body = self.client.get(f"/?lang={locale}").get_data(as_text=True)
                self.assertIn(f'class="header-cta"', body)
                self.assertIn(f">{label}</a>", body)

    def test_public_header_matches_v3_fixed_position(self):
        from pathlib import Path

        stylesheet = (Path(__file__).resolve().parents[1] / "static" / "css" / "v3" / "components.css").read_text(encoding="utf-8")
        header_rule = stylesheet.split(".site-header {", 1)[1].split("}", 1)[0]
        self.assertIn("position: fixed", header_rule)

    def test_public_selector_hides_french_and_spanish_in_requested_order(self):
        body = self.client.get("/?lang=zh-Hant").get_data(as_text=True)
        selector = re.search(r'<div class="language-picker".*?</div></div>', body, re.S).group(0)
        self.assertNotIn('lang="fr"', selector)
        self.assertNotIn('lang="es"', selector)
        self.assertLess(selector.index('lang="en"'), selector.index('lang="zh-Hant"'))
        self.assertLess(selector.index('lang="zh-Hant"'), selector.index('lang="zh-Hans"'))

    def test_v3_static_copy_catalog_is_complete_utf8(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "app" / "static_translations.json").read_text(encoding="utf-8"))
        required = set(template_strings())
        for locale in ("en", "fr", "es"):
            with self.subTest(locale=locale):
                self.assertFalse(required - set(catalog[locale]))
                self.assertTrue(all("\ufffd" not in value for value in catalog[locale].values()))
                self.assertFalse([
                    source for source in required
                    if re.search(r"[\u3400-\u9fff]", CATALOG[locale].get(source, ""))
                ])
        for path in list((root / "templates").rglob("*.html")) + [root / "app" / "static_translations.json"]:
            path.read_bytes().decode("utf-8", errors="strict")

    def test_v3_static_pages_have_no_untranslated_visible_chinese(self):
        paths = ("/", "/about/", "/dx-sermon/", "/dx-sermon/pricing/", "/church-ai-transformation/")
        for locale in ("en", "fr", "es"):
            for path in paths:
                with self.subTest(locale=locale, path=path):
                    body = self.client.get(f"{path}?lang={locale}").get_data(as_text=True)
                    body = re.sub(r"<header.*?</header>|<footer.*?</footer>", " ", body, flags=re.S)
                    if path == "/":
                        body = re.sub(r'<section class="section news-section".*?</section>', " ", body, flags=re.S)
                    visible = html.unescape(re.sub(r"<[^>]+>", " ", body))
                    self.assertIsNone(re.search(r"[\u3400-\u9fff]", visible))

    def test_v3_static_pages_render_simplified_chinese_tiles(self):
        expected = {
            "/": ("辨识．转化．同行", "神学辨识", "伦理治理", "事工创新"),
            "/about/": ("认识 CAIM", "教会AI转型支援"),
            "/dx-sermon/": ("甚么是 DX Sermon？", "历史背景", "神学反思"),
            "/dx-sermon/pricing/": ("DX Sermon 收费计划", "基本版", "专业版"),
            "/church-ai-transformation/": ("教会AI转型", "使命辨识", "流程落地"),
        }
        for path, phrases in expected.items():
            with self.subTest(path=path):
                response = self.client.get(f"{path}?lang=zh-Hans")
                body = response.data.decode("utf-8", errors="strict")
                self.assertEqual(response.status_code, 200)
                self.assertIn('<html lang="zh-Hans">', body)
                self.assertNotIn("\ufffd", body)
                for phrase in phrases:
                    self.assertIn(phrase, body)

    def test_opencc_preserves_nested_payload_and_converts_chinese(self):
        translated = translate_payload(
            {"title": "繁體中文與教會", "detail": {"paragraphs": ["人工智能時代"]}},
            "zh-Hant",
            "zh-Hans",
        )
        self.assertEqual(translated["title"], "繁体中文与教会")
        self.assertEqual(translated["detail"]["paragraphs"], ["人工智能时代"])

    def test_untranslated_public_content_falls_back_to_approved_original(self):
        slug = "human-machine-coexistence-ai-tools-vs-ai-risk"
        traditional = self.client.get(f"/articles/{slug}/?lang=zh-Hant").get_data(as_text=True)
        original_title = "人機共生：從AI工具論與AI危險論走向信仰的對話"
        self.assertIn(original_title, traditional)
        for locale in ("en", "zh-Hans"):
            with self.subTest(locale=locale):
                response = self.client.get(f"/articles/{slug}/?lang={locale}")
                self.assertEqual(response.status_code, 200)
                self.assertIn(original_title, response.get_data(as_text=True))


class TranslationPersistenceTests(unittest.TestCase):
    key = "multilingual-persistence-test"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app({"TESTING": True, "SECRET_KEY": "translation-db-test"})

    def tearDown(self):
        with self.app.app_context():
            with get_db().cursor() as cursor:
                cursor.execute(
                    "DELETE FROM content_translations WHERE content_type='articles' AND content_key=%s",
                    (self.key,),
                )

    def test_each_language_has_independent_status_and_unicode_payload(self):
        with self.app.app_context():
            save_content_translation(
                "articles", self.key, "zh-Hans", "zh-Hant",
                {"title": "简体中文标题", "detail": {"body": "内容正确显示。"}}, "posted",
            )
            save_content_translation(
                "articles", self.key, "fr", "zh-Hant",
                {"title": "Titre français", "detail": {"body": "En révision."}}, "saved",
            )
            simplified = get_content_translation("articles", self.key, "zh-Hans")
            french = get_content_translation("articles", self.key, "fr")
            self.assertEqual(simplified["status"], "posted")
            self.assertEqual(french["status"], "saved")
            self.assertEqual(simplified["payload"]["title"], "简体中文标题")
            self.assertEqual(french["payload"]["title"], "Titre français")


class TranslateAllWorkflowTests(unittest.TestCase):
    slug = "human-machine-coexistence-ai-tools-vs-ai-risk"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app({"TESTING": True, "SECRET_KEY": "translate-all-test"})
        cls.client = cls.app.test_client()
        page = cls.client.get("/content/content-manager").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        cls.client.post("/content/content-manager", data={
            "csrf_token": token, "username": "admin", "password": "New2P@ss",
        })

    def tearDown(self):
        with self.app.app_context():
            with get_db().cursor() as cursor:
                cursor.execute(
                    "DELETE FROM content_approvals WHERE content_type='articles' AND content_key=%s AND locale<>'zh-Hant'",
                    (self.slug,),
                )
                cursor.execute(
                    "DELETE FROM content_translations WHERE content_type='articles' AND content_key=%s",
                    (self.slug,),
                )

    def test_one_click_creates_every_other_language_in_review(self):
        studio = self.client.get(f"/content/article-studio?slug={self.slug}").get_data(as_text=True)
        self.assertIn("Translate all languages", studio)
        self.assertIn("Language review status", studio)
        self.assertIn("<th>Language</th><th>Generated</th><th>Status</th>", studio)
        self.assertRegex(studio, r'Original language<input[^>]+readonly')
        self.assertIn("Not generated", studio)
        edit_tabs = re.search(r'<div class="field span-2 content-language-tabs">.*?</div>', studio, re.S).group(0)
        self.assertNotIn("English</a>", edit_tabs)
        token = re.search(r'name="csrf_token" value="([^"]+)"', studio).group(1)

        def fake_translate(payload, _source, target):
            translated = dict(payload)
            translated["title"] = f"{target} translated title"
            return translated

        with patch("app.content_manager.translate_payload", side_effect=fake_translate):
            response = self.client.post(
                f"/content/articles/{self.slug}/translate",
                data={"csrf_token": token},
            )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            from app.db import fetch_all
            rows = fetch_all(
                "SELECT locale,status FROM content_translations WHERE content_type='articles' AND content_key=%s ORDER BY locale",
                (self.slug,),
            )
            approvals = fetch_all(
                "SELECT locale,status FROM content_approvals WHERE content_type='articles' AND content_key=%s AND locale<>'zh-Hant' ORDER BY locale",
                (self.slug,),
            )
        self.assertEqual({row["locale"] for row in rows}, {"en", "fr", "es", "zh-Hans"})
        self.assertTrue(all(row["status"] == "review" for row in rows))
        self.assertTrue(all(row["status"] == "pending" for row in approvals))

        studio = self.client.get(f"/content/article-studio?slug={self.slug}&lang=en").get_data(as_text=True)
        self.assertIn("en translated title", studio)
        self.assertNotIn("Translate all languages", studio)
        self.assertIn('<span class="status status-review">Review</span>', studio)

    def test_course_and_news_studios_show_language_status_tables(self):
        with self.app.app_context():
            from app.db import fetch_one
            news_slug = fetch_one("SELECT slug FROM news WHERE status='posted' ORDER BY id LIMIT 1")["slug"]
        for path in ("/content/course-studio?slug=mt101", f"/content/news-studio?slug={news_slug}"):
            with self.subTest(path=path):
                body = self.client.get(path).get_data(as_text=True)
                self.assertIn("Language review status", body)
                self.assertIn("<th>Language</th><th>Generated</th><th>Status</th>", body)
                self.assertRegex(body, r'Original language<input[^>]+readonly')


if __name__ == "__main__":
    unittest.main()
