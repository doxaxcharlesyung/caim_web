"""Build the checked-in UTF-8 catalog for fixed v3 page copy.

This is a maintenance command, not a runtime dependency. Existing hand-reviewed
translations in app.i18n override generated values when the app loads.
"""

import json
import re
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "app" / "static_translations.json"
LOCALES = {"en": "en", "fr": "fr", "es": "es"}
CJK = re.compile(r"[\u3400-\u9fff]")
STATIC_COLLECTIONS = {
    "dxTools",
    "leaders",
    "oneKeyTools",
    "pillars",
    "services",
    "site",
    "testimonials",
    "toolbox",
}


def cjk_strings(value):
    if isinstance(value, str):
        if CJK.search(value):
            yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from cjk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from cjk_strings(item)


def template_strings():
    strings = set()
    paths = list((ROOT / "templates" / "pages").glob("*.html"))
    paths += list((ROOT / "templates" / "articles").glob("*.html"))
    for path in paths:
        source = path.read_text(encoding="utf-8")
        strings.update(re.findall(r"t\('([^']+)'\)", source))
        # Jinja data structures often put tile copy in later tuple/list fields.
        strings.update(re.findall(r"'([^']*[\u3400-\u9fff][^']*)'", source))
    data_tree = ast.parse((ROOT / "app" / "data.py").read_text(encoding="utf-8"))
    strings.update(
        node.value for node in ast.walk(data_tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and CJK.search(node.value)
    )
    snapshot = json.loads((ROOT / "scripts" / "content_snapshot.json").read_text(encoding="utf-8"))
    for row in snapshot["page_content"]:
        strings.update(cjk_strings(row.get("title")))
        strings.update(cjk_strings(row.get("subtitle")))
        sections = row.get("sections", [])
        strings.update(cjk_strings(json.loads(sections) if isinstance(sections, str) else sections))
    for row in snapshot["content_items"]:
        if row["collection_name"] not in STATIC_COLLECTIONS:
            continue
        item = row["item_data"]
        strings.update(cjk_strings(json.loads(item) if isinstance(item, str) else item))
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
