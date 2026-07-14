"""Build the checked-in UTF-8 catalog for fixed v3 page copy.

This is a maintenance command, not a runtime dependency. Existing hand-reviewed
translations in app.i18n override generated values when the app loads.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "app" / "static_translations.json"
LOCALES = {"en": "en", "fr": "fr", "es": "es"}
CJK = re.compile(r"[\u3400-\u9fff]")


def template_strings():
    strings = set()
    paths = list((ROOT / "templates" / "pages").glob("*.html"))
    paths += list((ROOT / "templates" / "articles").glob("*.html"))
    for path in paths:
        source = path.read_text(encoding="utf-8")
        strings.update(re.findall(r"t\('([^']+)'\)", source))
        strings.update(re.findall(r"\('([^']*[\u3400-\u9fff][^']*)'", source))
    return sorted(text for text in strings if CJK.search(text))


def translate(text, target):
    query = urlencode({"client": "gtx", "sl": "zh-TW", "tl": target, "dt": "t", "q": text})
    request = Request(
        f"https://translate.googleapis.com/translate_a/single?{query}",
        headers={"User-Agent": "CAIM translation catalog builder"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return "".join(part[0] for part in payload[0] if part[0])


def main():
    existing = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    result = {locale: dict(existing.get(locale, {})) for locale in LOCALES}
    for locale, target in LOCALES.items():
        pending = [source for source in template_strings() if source not in result[locale]]
        with ThreadPoolExecutor(max_workers=8) as executor:
            requests = {executor.submit(translate, source, target): source for source in pending}
            for request in as_completed(requests):
                result[locale][requests[request]] = request.result()
        result[locale] = dict(sorted(result[locale].items()))
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
