"""Stock quote providers used by herdr-stockpulse.

Yahoo Finance is the default because it requires no API key. iTick is tried only
after a Yahoo Finance failure and only when an iTick token is configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote as url_quote
from urllib.request import Request, urlopen

from i18n import t

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
ITICK_TICK_URL = "https://api.itick.org/stock/tick?region={region}&code={code}"
REQUEST_TIMEOUT_SECONDS = 10
RETRY_DELAY_SECONDS = 1


class QuoteError(Exception):
    """A quote provider could not return a valid quote."""


class TransientQuoteError(QuoteError):
    """A provider failure that may succeed on retry: rate limit, server error, or network error."""


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    previous_close: Optional[float]
    currency: Optional[str]
    name: Optional[str]
    source: str
    updated_at: datetime

    @property
    def change(self) -> Optional[float]:
        if self.previous_close is None:
            return None
        return self.price - self.previous_close

    @property
    def change_percent(self) -> Optional[float]:
        if self.previous_close in (None, 0):
            return None
        return (self.price - self.previous_close) / self.previous_close * 100


def _get_json(url: str, headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "herdr-stockpulse", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        error_type = TransientQuoteError if error.code == 429 or error.code >= 500 else QuoteError
        raise error_type(str(error)) from error
    except (URLError, TimeoutError) as error:
        raise TransientQuoteError(str(error)) from error
    except ValueError as error:
        raise QuoteError(str(error)) from error


def _retry_once_when_transient(fetch: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return fetch()
    except TransientQuoteError:
        time.sleep(RETRY_DELAY_SECONDS)
        return fetch()


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_yahoo(symbol: str, get_json: Callable[..., dict[str, Any]] = _get_json) -> Quote:
    """Fetch a quote from the Yahoo chart endpoint used by the Chrome extension."""
    url = YAHOO_CHART_URL.format(symbol=url_quote(symbol, safe=""))
    payload = _retry_once_when_transient(lambda: get_json(url))
    chart = payload.get("chart") or {}
    results = chart.get("result") or []
    if not results:
        message = (chart.get("error") or {}).get("description", "No quote data returned")
        raise QuoteError(str(message))

    meta = results[0].get("meta") or {}
    price = _as_float(meta.get("regularMarketPrice"))
    if price is None:
        raise QuoteError(t("quote.no_price_yahoo", symbol=symbol))

    timestamp = _as_float(meta.get("regularMarketTime"))
    updated_at = datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else datetime.now(timezone.utc)
    return Quote(
        symbol=symbol.upper(),
        price=price,
        previous_close=_as_float(meta.get("chartPreviousClose")),
        currency=meta.get("currency"),
        name=meta.get("longName") or meta.get("shortName"),
        source="Yahoo Finance",
        updated_at=updated_at,
    )


def _itick_params(symbol: str) -> tuple[str, str]:
    normalized = symbol.upper()
    if normalized[:6].isdigit() and len(normalized) in (6, 9) and (
        len(normalized) == 6 or normalized[6:] in (".KS", ".KQ", ".XKRX", ".XKOS")
    ):
        return "KR", normalized[:6]
    return "US", normalized.split(".", 1)[0]


def fetch_itick(symbol: str, token: str, get_json: Callable[..., dict[str, Any]] = _get_json) -> Quote:
    """Fetch an iTick fallback quote. iTick does not supply a prior close here."""
    region, code = _itick_params(symbol)
    url = ITICK_TICK_URL.format(region=region, code=url_quote(code, safe=""))
    payload = get_json(url, headers={"token": token})
    tick = payload.get("data") or payload
    price = _as_float(tick.get("ld") if isinstance(tick, dict) else None)
    if price is None:
        raise QuoteError(t("quote.no_price_itick", symbol=symbol))
    return Quote(
        symbol=symbol.upper(),
        price=price,
        previous_close=None,
        currency=None,
        name=None,
        source="iTick",
        updated_at=datetime.now(timezone.utc),
    )


def fetch_quote(symbol: str, itick_token: str = "") -> Quote:
    """Fetch Yahoo Finance first, then iTick if a configured fallback is available."""
    try:
        return fetch_yahoo(symbol)
    except QuoteError as yahoo_error:
        if not itick_token:
            raise QuoteError(t("quote.yahoo_failed", symbol=symbol, yahoo_error=yahoo_error)) from yahoo_error
        try:
            return fetch_itick(symbol, itick_token)
        except QuoteError as itick_error:
            raise QuoteError(
                t("quote.both_failed", symbol=symbol, yahoo_error=yahoo_error, itick_error=itick_error)
            ) from itick_error
