"""Terminal rendering for StockPulse quotes."""

from __future__ import annotations

from quotes import Quote


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


def sidebar_quotes(quotes: list[Quote]) -> str:
    """Build the single StockPulse token rendered in the Agents sidebar."""
    values = []
    for quote in quotes[:3]:
        price = f"{quote.price:,.2f}"
        if quote.change_percent is None:
            values.append(f"{quote.symbol} {price}")
        else:
            values.append(f"{trend_label(quote)} {quote.symbol} {price} {quote.change_percent:+.2f}%")
    if len(quotes) > 3:
        values.append(f"+{len(quotes) - 3}")
    return " | ".join(values) or "No quotes configured"
