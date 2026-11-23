import re
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app import create_app


POLICY_URL = "/resources/ai-policy/"
CRM_URL = "http://127.0.0.1:8000/api/v1/public/activity-registration"
DOCUMENTS = {
    "en": "caim-church-ai-policy-english.docx",
    "zh-Hant": "caim-church-ai-policy-traditional-chinese.docx",
    "zh-Hans": "caim-church-ai-policy-simplified-chinese.docx",
}


class AIPolicyTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "policy-test-key"})
        self.client = self.app.test_client()

    def policy_form(self, language="en"):
        response = self.client.get(f"{POLICY_URL}?lang={language}")
        token = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)).group(1)
        return {"csrf_token": token, "email": "reader@example.com", "language": language}

    def test_navigation_and_page_render_in_all_five_locales(self):
        labels = {
            "en": ("Resources", "AI Policy", "AI Use Policy for Churches", "Document language"),
            "zh-Hant": ("資源", "AI 使用守則", "教會人工智能使用守則", "文件語言"),
            "zh-Hans": ("资源", "AI 使用守则", "教会人工智能使用守则", "文件语言"),
            "fr": ("Ressources", "Politique d’IA", "Politique d’utilisation de l’IA pour les Églises", "Langue du document"),
            "es": ("Recursos", "Política de IA", "Política de uso de la IA para iglesias", "Idioma del documento"),
        }
        for locale, (resources, policy, title, language_label) in labels.items():
            with self.subTest(locale=locale):
                landing = self.client.get(f"/resources/?lang={locale}").get_data(as_text=True)
                self.assertIn(f"<h1>{resources}</h1>", landing)
                self.assertIn(f'href="{POLICY_URL}?lang={locale}">{policy}</a>', landing)
                response = self.client.get(f"{POLICY_URL}?lang={locale}")
                self.assertIn("charset=utf-8", response.content_type)
                page = response.get_data(as_text=True)
                self.assertIn(f"<h1>{title}</h1>", page)
                self.assertIn(language_label, page)
                default_language = locale if locale in DOCUMENTS else "en"
                self.assertIn(f'lang="{default_language}" selected', page)

    def test_crm_confirmation_unlocks_only_the_selected_original_file(self):
        for language, filename in DOCUMENTS.items():
            with self.subTest(language=language):
                form = self.policy_form(language)
                file_url = f"{POLICY_URL}download/{language}/"
                anonymous = self.app.test_client()
                self.assertEqual(anonymous.get(file_url).status_code, 302)
                self.assertEqual(anonymous.get(f"/static/{filename}").status_code, 404)

                with patch.dict("os.environ", {
                    "APP_ENV": "development",
                    "CRM_POLICY_REGISTRATION_URL": CRM_URL,
                    "CRM_ACTIVITY_TOKEN": "test-token",
                }), patch("app.crm.httpx.post", return_value=httpx.Response(
                    201, json={"activity_id": None, "registration_id": 42, "contact_id": 12},
                )) as post:
                    response = self.client.post(POLICY_URL, data=form)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(post.call_args.args[0], CRM_URL)
                self.assertEqual(post.call_args.kwargs["headers"]["X-Activity-Token"], "test-token")
                payload = post.call_args.kwargs["json"]
                self.assertEqual(payload["email"], form["email"])
                self.assertEqual(payload["questionnaire"], {"document_language": language})
                self.assertEqual(payload["activity_type"], "resource_download")
                self.assertEqual(payload["activity_key"], "caim-church-ai-policy-download")
                self.assertNotIn("activity_id", payload)

                ready = self.client.get(response.location).get_data(as_text=True)
                self.assertIn(f'href="{file_url}"', ready)
                self.assertNotIn(form["email"], ready)
                for other_language in DOCUMENTS.keys() - {language}:
                    self.assertEqual(self.client.get(f"{POLICY_URL}download/{other_language}/").status_code, 302)
                self.assertEqual(anonymous.get(file_url).status_code, 302)
                with self.client.get(file_url) as download:
                    self.assertEqual(download.status_code, 200)
                    self.assertIn(f"attachment; filename={filename}", download.headers["Content-Disposition"])
                    self.assertTrue(download.cache_control.no_store)
                    path = Path(__file__).resolve().parents[1] / "docs" / filename
                    self.assertEqual(download.data, path.read_bytes())

    def test_invalid_submission_does_not_call_crm(self):
        form = self.policy_form()
        for fields in ({"email": "invalid"}, {"language": "fr"}, {"csrf_token": "incorrect"}):
            with self.subTest(fields=fields), patch("app.crm.httpx.post") as post:
                response = self.client.post(POLICY_URL, data={**form, **fields})
                self.assertEqual(response.status_code, 400)
                self.assertIn('role="alert"', response.get_data(as_text=True))
                post.assert_not_called()

    def test_unconfirmed_contact_keeps_download_locked(self):
        form = self.policy_form()
        for result in (httpx.Response(500), httpx.Response(201, json={"registration_id": 42})):
            with self.subTest(status=result.status_code), patch("app.crm.httpx.post", return_value=result):
                response = self.client.post(POLICY_URL, data=form)
                self.assertEqual(response.status_code, 503)
                page = response.get_data(as_text=True)
                self.assertIn("The download is temporarily unavailable", page)
                self.assertIn('value="reader@example.com"', page)
                self.assertEqual(self.client.get(f"{POLICY_URL}download/en/").status_code, 302)

    def test_dev_default_does_not_use_production_course_url(self):
        form = self.policy_form()
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "CRM_ACTIVITY_REGISTRATION_URL": "https://dxcrm.doxaxsolutions.com/api/v1/public/activity-registration",
        }) as env, patch("app.crm.httpx.post", return_value=httpx.Response(503)) as post:
            env.pop("CRM_POLICY_REGISTRATION_URL", None)
            self.client.post(POLICY_URL, data=form)
        self.assertEqual(post.call_args.args[0], CRM_URL)
