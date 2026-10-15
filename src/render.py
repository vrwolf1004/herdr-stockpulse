"""Terminal rendering for StockPulse quotes."""

from __future__ import annotations

import unicodedata

from quotes import Quote

# herdr allows at most 16 Agents-sidebar rows. With the standard feedbag rows,
# five two-line quotes plus the overflow row remain within that limit.
MAX_SIDEBAR_QUOTES = 5
MAX_SIDEBAR_NAME_WIDTH = 28


def trend_label(quote: Quote) -> str:
    change = quote.change
    if change is None:
        return "—"
    if change > 0:
        return "▲"
    if change < 0:
        return "▼"
    return "•"


def format_quote(quote: Quote) -> str:
    currency = f" {quote.currency}" if quote.currency else ""
    title = f"{quote.symbol} ({quote.name})" if quote.name else quote.symbol
    price = f"{quote.price:,.2f}{currency}"
    if quote.change is None or quote.change_percent is None:
        change = "change unavailable"
    else:
        change = f"{trend_label(quote)} {quote.change:+,.2f} ({quote.change_percent:+.2f}%)"
    return f"{title}\n  {price}  {change}\n  Source: {quote.source} · Updated: {quote.updated_at:%Y-%m-%d %H:%M UTC}"


def _display_width(value: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in value)


def _sidebar_name(quote: Quote) -> str:
    name = quote.name or quote.symbol
    if _display_width(name) <= MAX_SIDEBAR_NAME_WIDTH:
        return name
    shortened = ""
    for char in name:
        if _display_width(shortened + char + "...") > MAX_SIDEBAR_NAME_WIDTH:
            break
        shortened += char
    return shortened + "..."


def sidebar_quote_tokens(quotes: list[Quote]) -> dict[str, str]:
    """Build one Agents-sidebar token per quote so narrow sidebars do not truncate them."""
    tokens = {}
    for index, quote in enumerate(quotes[:MAX_SIDEBAR_QUOTES], start=1):
        currency = f"{quote.currency} " if quote.currency else ""
        if quote.change_percent is None:
            value = f"{currency}{quote.price:,.2f}"
        else:
            value = f"{trend_label(quote)} {currency}{quote.price:,.2f} {quote.change_percent:+.2f}%"
        tokens[f"sp_quote_{index}_name"] = _sidebar_name(quote)
        tokens[f"sp_quote_{index}_price"] = value
    remaining = len(quotes) - MAX_SIDEBAR_QUOTES
    if remaining > 0:
        tokens["sp_quote_more"] = f"+{remaining} more symbols"
    return tokens
