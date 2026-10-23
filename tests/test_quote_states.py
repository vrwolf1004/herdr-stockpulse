import json
import os
import sys
import threading
import time
import unittest
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

os.environ["HERDR_STOCKPULSE_LANG"] = "en"  # 기대 문구는 영어 기준이다. i18n 을 읽기 전에 고정한다.
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import panel  # noqa: E402
import quotes  # noqa: E402
from i18n import t  # noqa: E402
from quotes import Quote, QuoteError, TransientQuoteError  # noqa: E402

LOCALES = sorted((SRC / "locales").glob("*.json"))
NEW_KEYS = ("quote.stale", "quote.pending", "quote.blocked", "quote.bad_format", "quote.hint_itick")


def quote_for(symbol, price=100.0):
    return Quote(symbol=symbol, price=price, previous_close=99.0, currency="USD", name=symbol,
                 source="Yahoo Finance", updated_at=datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc))


def plain(text):
    return panel.ANSI_RE.sub("", text)


class DeadlineTest(unittest.TestCase):
    """한 종목이 기한을 넘기면 한 바퀴는 마감에 맞춰 끝나고, 그 종목은 직전 값 (지연) 이나 대기 중으로 보인다."""

    def setUp(self):
        self.release = threading.Event()
        self.addCleanup(self.release.set)  # 테스트가 끝나면 멈춘 조회 스레드를 풀어 준다
        patches = [
            mock.patch.object(panel, "QUOTE_DEADLINE_SECONDS", 0.3),
            mock.patch.object(panel, "fetch_quote", side_effect=self.fake_fetch),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def fake_fetch(self, symbol, itick_token=""):
        if symbol == "SLOW":
            self.release.wait(10)  # 기한을 훨씬 넘긴다 (테스트가 끝날 때까지 풀리지 않는 것과 같다)
            return quote_for("SLOW", 555.0)
        return quote_for(symbol, 1.0)

    def test_round_ends_at_the_deadline_and_shows_the_last_value_as_delayed(self):
        last = {"SLOW": quote_for("SLOW", 42.0)}
        started = time.monotonic()
        contents, tokens = panel.dashboard(["FAST", "SLOW"], "tok", last)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 5.0)  # 마감 0.3초 + 여유. 느린 종목 (10초 대기) 을 기다리지 않는다
        text = plain(contents)
        self.assertIn("FAST", text)
        self.assertIn("SLOW", text)
        self.assertIn(t("quote.stale"), text)
        self.assertIn("42", text)  # 직전 값이 보인다
        self.assertNotIn("555", text)  # 기한 뒤에 도착한 값은 쓰지 않는다
        sidebar = " ".join(f"{key} {value}" for key, value in tokens.items())
        self.assertIn("FAST", sidebar)
        self.assertNotIn("42", sidebar)  # 사이드바에는 이번 바퀴에 받은 값만 올린다 (직전 값은 올리지 않는다)

    def test_delayed_symbol_is_remembered_for_the_next_round(self):
        last = {}
        panel.dashboard(["FAST", "SLOW"], "tok", last)
        self.assertIn("FAST", last)
        self.assertNotIn("SLOW", last)  # 기한 안에 못 받은 종목은 기억에 넣지 않는다 (직전 값이 없다)

    def test_without_a_previous_value_the_symbol_shows_waiting(self):
        contents, _ = panel.dashboard(["FAST", "SLOW"], "tok", {})
        text = plain(contents)
        self.assertIn(t("quote.pending"), text)
        self.assertNotIn(t("quote.stale"), text)

    def test_stale_marker_is_not_added_to_a_fresh_symbol(self):
        contents, _ = panel.dashboard(["FAST"], "tok", {"FAST": quote_for("FAST", 5.0)})
        self.assertNotIn(t("quote.stale"), plain(contents))


class ErrorKindTest(unittest.TestCase):
    def test_403_is_blocked_and_not_retried(self):
        error = HTTPError("https://example.test", 403, "Forbidden", None, None)
        with mock.patch.object(quotes, "urlopen", side_effect=error):
            with self.assertRaises(QuoteError) as caught:
                quotes._get_json("https://example.test")
        self.assertNotIsInstance(caught.exception, TransientQuoteError)
        self.assertEqual(caught.exception.kind, "blocked")
        self.assertEqual(str(caught.exception), t("quote.blocked"))

    def test_429_is_blocked_and_still_transient_for_retry(self):
        error = HTTPError("https://example.test", 429, "Too Many", None, None)
        with mock.patch.object(quotes, "urlopen", side_effect=error):
            with self.assertRaises(TransientQuoteError) as caught:
                quotes._get_json("https://example.test")
        self.assertEqual(caught.exception.kind, "blocked")
        self.assertEqual(str(caught.exception), t("quote.blocked"))

    def test_server_error_keeps_the_generic_provider_text(self):
        error = HTTPError("https://example.test", 500, "Server", None, None)
        with mock.patch.object(quotes, "urlopen", side_effect=error):
            with self.assertRaises(TransientQuoteError) as caught:
                quotes._get_json("https://example.test")
        self.assertIsNone(caught.exception.kind)
        self.assertEqual(str(caught.exception), t("quote.provider_error"))

    def test_non_json_response_is_a_format_error(self):
        class Response(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        with mock.patch.object(quotes, "urlopen", return_value=Response(b"<html>not json</html>")):
            with self.assertRaises(QuoteError) as caught:
                quotes._get_json("https://example.test")
        self.assertEqual(caught.exception.kind, "bad_format")
        self.assertEqual(str(caught.exception), t("quote.bad_format"))

    def test_empty_result_list_is_a_format_error(self):
        with self.assertRaises(QuoteError) as caught:
            quotes.fetch_yahoo("AAA", get_json=lambda url: {"chart": {"result": []}})
        self.assertEqual(caught.exception.kind, "bad_format")

    def test_fallback_keeps_the_kind_of_the_yahoo_error(self):
        blocked = QuoteError(t("quote.blocked"), kind="blocked")
        with mock.patch.object(quotes, "fetch_yahoo", side_effect=blocked):
            with self.assertRaises(QuoteError) as caught:
                quotes.fetch_quote("AAA", "")
        self.assertEqual(caught.exception.kind, "blocked")

    def test_dashboard_shows_the_blocked_text_not_the_raw_error(self):
        blocked = QuoteError(t("quote.blocked"), kind="blocked")
        with mock.patch.object(panel, "fetch_quote", side_effect=blocked):
            contents, _ = panel.dashboard(["AAA"], "tok", {})
        self.assertIn(t("quote.blocked"), plain(contents))


class ItickHintTest(unittest.TestCase):
    def dashboard_with_failure(self, token):
        failure = QuoteError("Yahoo Finance failed")
        with mock.patch.object(panel, "fetch_quote", side_effect=failure):
            contents, _ = panel.dashboard(["AAA"], token, {})
        return plain(contents)

    def test_hint_is_shown_when_there_is_no_token_and_the_provider_failed(self):
        self.assertIn(t("quote.hint_itick"), self.dashboard_with_failure(""))

    def test_hint_is_hidden_when_a_token_is_configured(self):
        self.assertNotIn(t("quote.hint_itick"), self.dashboard_with_failure("tok"))

    def test_hint_is_not_shown_for_a_good_quote(self):
        with mock.patch.object(panel, "fetch_quote", return_value=quote_for("AAA")):
            contents, _ = panel.dashboard(["AAA"], "", {})
        self.assertNotIn(t("quote.hint_itick"), plain(contents))


class LocaleKeysTest(unittest.TestCase):
    def test_every_language_has_the_new_keys_and_the_same_key_set(self):
        key_sets = {}
        for path in LOCALES:
            data = json.loads(path.read_text(encoding="utf-8"))
            key_sets[path.name] = set(data)
            for key in NEW_KEYS:
                self.assertTrue(data.get(key), f"{path.name} 에 {key} 가 없다")
        reference = key_sets["en.json"]
        for name, keys in key_sets.items():
            self.assertEqual(keys, reference, name)
        self.assertEqual(len(LOCALES), 7)


if __name__ == "__main__":
    unittest.main()
