"""Persistent StockPulse dashboard pane."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
import re
import time
import unicodedata

import herdr_api
from quotes import QuoteError, fetch_quote
from render import format_quote, sidebar_quote_tokens, trend_label
from stockpulse import config_path, read_config, symbols_from

PLUGIN_ID = "herdr-stockpulse"
SOURCE = f"plugin:{PLUGIN_ID}"
AGENT_ID = "stockpulse"
TOKEN_TTL_MS = 90_000
REFRESH_SECONDS = 60
MAX_PARALLEL_REQUESTS = 8
TITLE = "🐺  herdr-stockpulse  🌕"
MIN_BOX_INNER = 44
MAX_BOX_INNER = 70
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _fetch_or_error(symbol, itick_token):
    try:
        return fetch_quote(symbol, itick_token)
    except QuoteError as error:
        return error


def _style(text, sgr):
    return f"\x1b[{sgr}m{text}\x1b[0m"


def _display_width(value):
    value = ANSI_RE.sub("", value)  # 색 코드는 칸 수에서 뺀다
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in value)


def box(sections, title=TITLE):
    """테두리 상자에 담는다. 섹션 사이는 가로줄로 나눈다 (herdr-radio 의 panel 과 같은 모양)."""
    rows = []
    for index, section in enumerate(sections):
        if index:
            rows.append(None)
        for line in section:
            rows.extend(line.splitlines() or [""])
    widths = [_display_width(row) for row in rows if row is not None] + [_display_width(title)]
    inner = min(MAX_BOX_INNER, max([MIN_BOX_INNER] + [width + 2 for width in widths]))
    left = max(0, (inner - _display_width(title)) // 2)
    lines = [
        "╭" + "─" * inner + "╮",
        "│" + " " * left + title + " " * (inner - left - _display_width(title)) + "│",
        "├" + "─" * inner + "┤",
    ]
    for row in rows:
        if row is None:
            lines.append("├" + "─" * inner + "┤")
        else:
            lines.append("│ " + row + " " * (inner - 1 - _display_width(row)) + "│")
    lines.append("╰" + "─" * inner + "╯")
    return "\n".join(lines)


def quote_lines(quote):
    """시세 한 종목의 줄. 상승은 초록, 하락은 빨강으로 강조한다 (devrun 대시보드와 같은 색)."""
    name, price, _ = format_quote(quote).splitlines()
    sgr = {"▲": "32", "▼": "31"}.get(trend_label(quote), "37")
    updated = f"{quote.updated_at:%Y-%m-%d %H:%M UTC}"
    return [_style(name, "1;97"), _style(price, sgr), _style(f"  {updated}", "90")]


def dashboard(symbols, itick_token):
    sections = []
    quotes = []
    # Fetch in parallel so one slow symbol cannot push the refresh past its interval; results keep configured order.
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as pool:
        results = list(pool.map(lambda symbol: _fetch_or_error(symbol, itick_token), symbols))
    for symbol, result in zip(symbols, results):
        if isinstance(result, QuoteError):
            sections.append([_style(symbol, "1;97"), _style(f"  Error: {result}", "31")])
        else:
            quotes.append(result)
            sections.append(quote_lines(result))
    sources = sorted({quote.source for quote in quotes})
    footer = f"Source: {' · '.join(sources)}   " if sources else ""
    sections.append([footer + f"Refreshes {REFRESH_SECONDS} s   " + _style("[Ctrl+C] close", "2")])
    return box(sections), sidebar_quote_tokens(quotes)


def render_once(explicit_config):
    config = read_config(config_path(explicit_config))
    symbols = symbols_from(config, [])
    return dashboard(symbols, str(config.get("itick_token", "")))


def report_sidebar(pane_id, tokens):
    if not pane_id:
        return
    herdr_api.try_request("pane.report_agent", {
        "pane_id": pane_id,
        "source": SOURCE,
        "agent": AGENT_ID,
        "state": "idle",
    })
    herdr_api.try_request("pane.report_metadata", {
        "pane_id": pane_id,
        "source": SOURCE,
        "display_agent": AGENT_ID,
        "tokens": tokens,
        "ttl_ms": TOKEN_TTL_MS,
    })


def main():
    parser = argparse.ArgumentParser(prog="stockpulse-panel")
    parser.add_argument("--config", help="Path to a configuration JSON file")
    parser.add_argument("--pane", help="Pane ID to report the sidebar agent on")
    parser.add_argument("--once", action="store_true", help="Render once and exit")
    args = parser.parse_args()
    try:
        while True:
            try:
                contents, sidebar_value = render_once(args.config)
                report_sidebar(args.pane, sidebar_value)
            except ValueError as error:
                contents = box([[f"Configuration error: {error}"], [_style("[Ctrl+C] close", "2")]])
                report_sidebar(args.pane, {})  # clear quotes from the last good refresh instead of letting them linger until TTL
            except Exception as error:  # noqa: BLE001 - keep the docked pane alive; retry next round
                contents = box([[f"Refresh failed: {type(error).__name__}: {error}"], [f"Retrying in {REFRESH_SECONDS}s   " + _style("[Ctrl+C] close", "2")]])
            print("\033[2J\033[H" + contents, flush=True)
            if args.once:
                return 0
            time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        return 0  # Ctrl+C 로 멈춘 것이므로 트레이스백 없이 끝나고, pane 은 원래 셸로 돌아간다
    finally:
        if args.pane:
            herdr_api.try_request("pane.release_agent", {"pane_id": args.pane, "source": SOURCE, "agent": AGENT_ID})


if __name__ == "__main__":
    raise SystemExit(main())
