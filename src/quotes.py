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
    """A quote provider could not return a valid quote.

    kind 은 화면 문구를 고르는 범주다: "blocked" (요청 제한, 접근 거부), "bad_format" (응답 구조가 다름), 그 밖은 None.
    """

    def __init__(self, message="", kind=None):
        super().__init__(message)
        self.kind = kind


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
        blocked = error.code in (403, 429)  # 요청 제한이나 접근 거부는 차단으로 본다 (429 는 재시도도 한다)
        error_type = TransientQuoteError if error.code == 429 or error.code >= 500 else QuoteError
        if blocked:
            raise error_type(t("quote.blocked"), kind="blocked") from error
        raise error_type(t("quote.provider_error")) from error
    except (URLError, TimeoutError) as error:
        raise TransientQuoteError(t("quote.provider_error")) from error
    except ValueError as error:  # JSON 이 아닌 응답은 형식 오류
        raise QuoteError(t("quote.bad_format"), kind="bad_format") from error


def _retry_once_when_transient(fetch: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return fetch()
    except TransientQuoteError:
        time.sleep(RETRY_DELAY_SECONDS)
        return fetch()


def _as_dict(value: Any) -> dict[str, Any]:
    """딕셔너리면 그대로, 아니면 빈 딕셔너리. 예상과 다른 응답 구조를 AttributeError 없이 넘기기 위해 쓴다."""
    return value if isinstance(value, dict) else {}


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
    if not isinstance(payload, dict):
        raise QuoteError(t("quote.bad_response", symbol=symbol))
    chart = _as_dict(payload.get("chart"))
    results = chart.get("result")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        # Yahoo 의 error.description 은 영어 원문이라 화면에 그대로 쓰지 않는다. 결과 구조가 없으면 형식 오류로 본다.
        raise QuoteError(t("quote.bad_format"), kind="bad_format")

    meta = _as_dict(results[0].get("meta"))
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
            raise QuoteError(t("quote.yahoo_failed", symbol=symbol, yahoo_error=yahoo_error),
                             kind=yahoo_error.kind) from yahoo_error
        try:
            return fetch_itick(symbol, itick_token)
        except QuoteError as itick_error:
            raise QuoteError(
                t("quote.both_failed", symbol=symbol, yahoo_error=yahoo_error, itick_error=itick_error)
            ) from itick_error
