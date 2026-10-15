from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unittest import mock

import panel
from quotes import Quote, QuoteError, fetch_itick, fetch_yahoo
from render import MAX_SIDEBAR_QUOTES, format_quote, sidebar_quote_tokens, trend_label


class YahooQuoteTests(unittest.TestCase):
    def test_parses_price_and_previous_close(self):
        payload = {
            "chart": {
                "result": [{
                    "meta": {
                        "regularMarketPrice": 201.5,
                        "chartPreviousClose": 200,
                        "regularMarketTime": 1_700_000_000,
                        "longName": "Example Corp.",
                        "currency": "USD",
                    }
                }]
            }
        }

        quote = fetch_yahoo("EXM", lambda _url: payload)

        self.assertEqual(quote.symbol, "EXM")
        self.assertEqual(quote.price, 201.5)
        self.assertEqual(quote.previous_close, 200)
        self.assertEqual(quote.updated_at, datetime.fromtimestamp(1_700_000_000, tz=timezone.utc))
        self.assertEqual(quote.change_percent, 0.75)

    def test_renders_up_down_and_flat_indicators(self):
        def quote(price):
            return fetch_yahoo(
                "EXM",
                lambda _url: {
                    "chart": {
                        "result": [{
                            "meta": {"regularMarketPrice": price, "chartPreviousClose": 100}
                        }]
                    }
                },
            )

        self.assertEqual(trend_label(quote(101)), "▲")
        self.assertEqual(trend_label(quote(99)), "▼")
        self.assertEqual(trend_label(quote(100)), "•")
        self.assertIn("▲ +1.00 (+1.00%)", format_quote(quote(101)))

    def test_creates_one_sidebar_token_per_quote(self):
        quotes = [
            Quote("UP", 101, 100, "USD", "Upward Company", "Yahoo Finance", datetime.now(timezone.utc)),
            Quote("DOWN", 99, 100, "USD", "Downward Company", "Yahoo Finance", datetime.now(timezone.utc)),
        ]

        self.assertEqual(sidebar_quote_tokens(quotes), {
            "sp_quote_1_name": "Upward Company",
            "sp_quote_1_price": "▲ USD 101.00 +1.00%",
            "sp_quote_2_name": "Downward Company",
            "sp_quote_2_price": "▼ USD 99.00 -1.00%",
        })

    def test_truncates_a_long_company_name_in_the_sidebar(self):
        quote = Quote(
            "LONG",
            100,
            100,
            "USD",
            "A Very Long Example Company Name",
            "Yahoo Finance",
            datetime.now(timezone.utc),
        )

        tokens = sidebar_quote_tokens([quote])
        self.assertEqual(tokens["sp_quote_1_name"], "A Very Long Example Compa...")
        self.assertEqual(tokens["sp_quote_1_price"], "• USD 100.00 +0.00%")

    def test_reports_a_remainder_after_sidebar_quote_limit(self):
        quote = Quote("EXM", 100, 100, "USD", None, "Yahoo Finance", datetime.now(timezone.utc))
        tokens = sidebar_quote_tokens([quote] * (MAX_SIDEBAR_QUOTES + 2))

        self.assertEqual(len([name for name in tokens if name.startswith("sp_quote_")]), MAX_SIDEBAR_QUOTES * 2 + 1)
        self.assertEqual(tokens["sp_quote_more"], "+2 more symbols")


class ITickQuoteTests(unittest.TestCase):
    def test_sends_token_in_header_and_not_in_url(self):
        calls = []

        def fake_get_json(url, headers=None):
            calls.append((url, headers))
            return {"data": {"ld": 10}}

        quote = fetch_itick("005930.KS", "secret-token", fake_get_json)

        url, headers = calls[0]
        self.assertNotIn("secret-token", url)
        self.assertEqual(headers, {"token": "secret-token"})
        self.assertEqual(quote.price, 10)


class DashboardTests(unittest.TestCase):
    def test_keeps_configured_order_and_reports_per_symbol_errors(self):
        def fake_fetch(symbol, _token):
            if symbol == "BAD":
                return QuoteError(f"{symbol}: no data")
            return Quote(symbol, 100, 100, "USD", None, "Yahoo Finance", datetime.now(timezone.utc))

        with mock.patch.object(panel, "fetch_quote", side_effect=fake_fetch):
            contents, tokens = panel.dashboard(["AAA", "BAD", "CCC"], "")

        self.assertLess(contents.index("AAA"), contents.index("BAD"))
        self.assertLess(contents.index("BAD"), contents.index("CCC"))
        self.assertIn("BAD\n  Error: BAD: no data", contents)
        self.assertEqual(tokens["sp_quote_1_name"], "AAA")
        self.assertEqual(tokens["sp_quote_2_name"], "CCC")


if __name__ == "__main__":
    unittest.main()
