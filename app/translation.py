import os

import httpx
from opencc import OpenCC

LOCALE_CODES = {"zh-Hant": "zh-TW", "zh-Hans": "zh-CN", "en": "en", "fr": "fr", "es": "es"}


def _translate_text(text, source_locale, target_locale):
    if not text or source_locale == target_locale:
        return text
    if target_locale == "zh-Hans" and source_locale == "zh-Hant":
        return OpenCC("t2s").convert(text)
    if target_locale == "zh-Hant" and source_locale == "zh-Hans":
        return OpenCC("s2t").convert(text)
    endpoint = os.getenv("TRANSLATION_API_URL", "").strip()
    if not endpoint:
        raise ValueError("TRANSLATION_API_URL is required for English, French, and Spanish translation.")
    headers = {}
    api_key = os.getenv("TRANSLATION_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    response = httpx.post(endpoint, json={
        "q": text,
        "source": LOCALE_CODES[source_locale],
        "target": LOCALE_CODES[target_locale],
        "format": "text",
        "api_key": api_key or None,
    }, headers=headers, timeout=60)
    response.raise_for_status()
    payload = response.json()
    translated = payload.get("translatedText") or payload.get("translation")
    if not translated:
        raise ValueError("The translation service returned no translated text.")
    return translated


def translate_payload(value, source_locale, target_locale):
    if isinstance(value, str):
        return _translate_text(value, source_locale, target_locale)
    if isinstance(value, list):
        return [translate_payload(item, source_locale, target_locale) for item in value]
    if isinstance(value, dict):
        return {key: translate_payload(item, source_locale, target_locale) for key, item in value.items()}
    return value
