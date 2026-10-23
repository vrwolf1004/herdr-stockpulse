import json
import os
import sys
import unittest
from pathlib import Path

os.environ["HERDR_STOCKPULSE_LANG"] = "en"  # 기대 문구는 영어 기준이다. i18n 을 읽기 전에 고정한다.
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from i18n import t  # noqa: E402
from quotes import QuoteError, fetch_yahoo  # noqa: E402

RAW_DESCRIPTION = "Symbol SECRET123 not found"
LOCALES = sorted((SRC / "locales").glob("*.json"))


def failing_fetch(payload):
    return lambda url: payload


class ProviderMessageTest(unittest.TestCase):
    def test_provider_error_description_is_not_shown_raw(self):
        payload = {"chart": {"result": None, "error": {"code": "Not Found", "description": RAW_DESCRIPTION}}}
        with self.assertRaises(QuoteError) as caught:
            fetch_yahoo("AAA", get_json=failing_fetch(payload))
        message = str(caught.exception)
        self.assertEqual(message, t("quote.bad_format"))  # 결과 구조가 없으면 형식 오류 (kind bad_format)
        self.assertEqual(caught.exception.kind, "bad_format")
        self.assertNotIn(RAW_DESCRIPTION, message)
        self.assertNotIn("Symbol", message)

    def test_missing_result_without_description_uses_the_same_translated_text(self):
        with self.assertRaises(QuoteError) as caught:
            fetch_yahoo("AAA", get_json=failing_fetch({"chart": {"result": None}}))
        self.assertEqual(str(caught.exception), t("quote.bad_format"))
        self.assertNotIn("No quote data returned", str(caught.exception))


class LocaleKeysTest(unittest.TestCase):
    def test_every_language_has_the_same_keys_including_provider_error(self):
        key_sets = {}
        for path in LOCALES:
            data = json.loads(path.read_text(encoding="utf-8"))
            key_sets[path.name] = set(data)
            self.assertTrue(data.get("quote.provider_error"), f"{path.name} 에 quote.provider_error 가 없다")
        reference = key_sets["en.json"]
        for name, keys in key_sets.items():
            self.assertEqual(keys, reference, name)
        self.assertEqual(len(LOCALES), 7)


if __name__ == "__main__":
    unittest.main()
