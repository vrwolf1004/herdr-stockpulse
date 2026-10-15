from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quotes import Quote, fetch_yahoo
from render import format_quote, sidebar_quotes, trend_label


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

    def test_creates_a_compact_sidebar_token(self):
        quotes = [
            Quote("UP", 101, 100, "USD", None, "Yahoo Finance", datetime.now(timezone.utc)),
            Quote("DOWN", 99, 100, "USD", None, "Yahoo Finance", datetime.now(timezone.utc)),
        ]

        self.assertEqual(sidebar_quotes(quotes), "▲ UP 101.00 +1.00% | ▼ DOWN 99.00 -1.00%")


if __name__ == "__main__":
    unittest.main()
