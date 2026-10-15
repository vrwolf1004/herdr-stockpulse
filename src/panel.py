"""Persistent StockPulse dashboard pane."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
import time

import herdr_api
from quotes import QuoteError, fetch_quote
from render import format_quote, sidebar_quote_tokens
from stockpulse import config_path, read_config, symbols_from

PLUGIN_ID = "herdr-stockpulse"
SOURCE = f"plugin:{PLUGIN_ID}"
AGENT_ID = "stockpulse"
TOKEN_TTL_MS = 90_000
REFRESH_SECONDS = 60
MAX_PARALLEL_REQUESTS = 8


def _fetch_or_error(symbol, itick_token):
    try:
        return fetch_quote(symbol, itick_token)
    except QuoteError as error:
        return error


def dashboard(symbols, itick_token):
    lines = ["StockPulse  Live prices", ""]
    quotes = []
    # Fetch in parallel so one slow symbol cannot push the refresh past its interval; results keep configured order.
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as pool:
        results = list(pool.map(lambda symbol: _fetch_or_error(symbol, itick_token), symbols))
    for symbol, result in zip(symbols, results):
        if isinstance(result, QuoteError):
            lines.extend([symbol, f"  Error: {result}"])
        else:
            quotes.append(result)
            lines.extend(format_quote(result).splitlines())
        lines.append("")
    lines.append(f"Refreshes every {REFRESH_SECONDS} seconds · Ctrl+C to close")
    return "\n".join(lines), sidebar_quote_tokens(quotes)


def render_once(explicit_config):
    config = read_config(config_path(explicit_config))
    symbols = symbols_from(config, [])
    return dashboard(symbols, str(config.get("itick_token", "")))


def report_sidebar(tokens):
    pane_id = os.environ.get("HERDR_PANE_ID")
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
    parser.add_argument("--once", action="store_true", help="Render once and exit")
    args = parser.parse_args()
    try:
        while True:
            try:
                contents, sidebar_value = render_once(args.config)
                report_sidebar(sidebar_value)
            except ValueError as error:
                contents = f"StockPulse\n\nConfiguration error: {error}\n\nCtrl+C to close"
                report_sidebar({})  # clear quotes from the last good refresh instead of letting them linger until TTL
            except Exception as error:  # noqa: BLE001 - keep the docked pane alive; retry next round
                contents = f"StockPulse\n\nRefresh failed: {type(error).__name__}: {error}\n\nRetrying in {REFRESH_SECONDS}s · Ctrl+C to close"
            print("\033[2J\033[H" + contents, flush=True)
            if args.once:
                return 0
            time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        return 0
    finally:
        pane_id = os.environ.get("HERDR_PANE_ID")
        if pane_id:
            herdr_api.try_request("pane.release_agent", {"pane_id": pane_id, "source": SOURCE, "agent": AGENT_ID})


if __name__ == "__main__":
    raise SystemExit(main())
