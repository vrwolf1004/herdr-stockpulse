"""Persistent StockPulse dashboard pane."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait
import os
import re
import time
import unicodedata

import herdr_api
from quotes import QuoteError, fetch_quote
from i18n import t
from render import format_quote, sidebar_quote_tokens, trend_label
from stockpulse import config_path, read_config, symbols_from

PLUGIN_ID = "herdr-stockpulse"
SOURCE = f"plugin:{PLUGIN_ID}"
AGENT_ID = "stockpulse"
DOCK_LABEL = "herdr-dock"  # 공용 도크 workspace. 맨 아래에 있어야 사이드바 블록이 위로 밀리지 않는다
TOKEN_TTL_MS = 90_000
REFRESH_SECONDS = 60
QUOTE_DEADLINE_SECONDS = 45  # 한 바퀴에서 종목 조회를 기다리는 최대 시간. REFRESH_SECONDS 보다 짧아야 한다. 넘긴 종목은 직전 값으로 보인다.
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


def error_lines(symbol, error, itick_token):
    lines = [_style(symbol, "1;97"), _style(f"  {t('quote.error', error=error)}", "31")]
    if not itick_token:  # 토큰이 없으면 대체 조회를 쓸 수 있다는 것을 알려 준다
        lines.append(_style(f"  {t('quote.hint_itick')}", "90"))
    return lines


def dashboard(symbols, itick_token, last_quotes=None):
    """last_quotes: 종목 → 마지막으로 받은 시세. 이번 바퀴에 기한 안에 못 받은 종목은 여기서 직전 값을 가져온다."""
    if last_quotes is None:
        last_quotes = {}
    sections = []
    quotes = []
    # 병렬로 받되 한 바퀴는 QUOTE_DEADLINE_SECONDS 를 넘기지 않는다. 기한 안에 끝나지 않은 조회는 버리고 다음 바퀴에서 다시 한다.
    pool = ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS)
    futures = {symbol: pool.submit(_fetch_or_error, symbol, itick_token) for symbol in symbols}
    done, _ = wait(list(futures.values()), timeout=QUOTE_DEADLINE_SECONDS)
    for future in futures.values():
        future.cancel()  # 아직 시작하지 않은 조회는 취소한다 (이미 도는 것은 끝까지 두고 결과만 버린다)
    pool.shutdown(wait=False)
    for symbol in symbols:  # 화면 순서는 설정 순서를 지킨다
        future = futures[symbol]
        if future in done:
            result = future.result()
            if isinstance(result, QuoteError):
                sections.append(error_lines(symbol, result, itick_token))
            else:
                last_quotes[symbol] = result
                quotes.append(result)
                sections.append(quote_lines(result))
        elif symbol in last_quotes:
            sections.append(quote_lines(last_quotes[symbol]) + [_style(f"  {t('quote.stale')}", "33")])
        else:
            sections.append([_style(symbol, "1;97"), _style(f"  {t('quote.pending')}", "90")])
    sources = sorted({quote.source for quote in quotes})
    footer = f"{t('panel.source', sources=' · '.join(sources))}   " if sources else ""
    sections.append([footer + t("panel.refresh", seconds=REFRESH_SECONDS) + "   " + _style(t("panel.close"), "2")])
    return box(sections), sidebar_quote_tokens(quotes)


def render_once(explicit_config, last_quotes=None):
    config = read_config(config_path(explicit_config))
    symbols = symbols_from(config, [])
    return dashboard(symbols, str(config.get("itick_token", "")), last_quotes)


def keep_at_bottom():
    """도크 workspace 를 목록 맨 아래로 옮긴다. 다른 블록이 없어도 도크가 위로 밀리지 않게 한다 (radio·timekit 과 같은 규칙)."""
    try:
        workspaces = herdr_api.request("workspace.list", {}).get("workspaces", [])
    except (herdr_api.HerdrError, ValueError):
        return
    ids = [w["workspace_id"] for w in workspaces]
    dock = next((w["workspace_id"] for w in workspaces if w.get("label") == DOCK_LABEL), None)
    if dock is None or not ids or ids[-1] == dock:
        return
    herdr_api.try_request("workspace.move", {"workspace_id": dock, "insert_index": len(ids)})


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
    last_quotes = {}  # 종목 → 마지막으로 받은 시세. 바퀴가 바뀌어도 유지되어 지연 표시에 쓴다.
    try:
        while True:
            started = time.monotonic()  # 다음 갱신은 이 시각부터 REFRESH_SECONDS 뒤다 (요청 시간을 포함)
            try:
                contents, sidebar_value = render_once(args.config, last_quotes)
                report_sidebar(args.pane, sidebar_value)
                keep_at_bottom()
            except ValueError as error:
                contents = box([[t("panel.config_error", error=error)], [_style(t("panel.close"), "2")]])
                report_sidebar(args.pane, {})  # clear quotes from the last good refresh instead of letting them linger until TTL
            except Exception as error:  # noqa: BLE001 - keep the docked pane alive; retry next round
                contents = box([[t("panel.refresh_failed", kind=type(error).__name__, error=error)],
                                [t("panel.retrying", seconds=REFRESH_SECONDS) + "   " + _style(t("panel.close"), "2")]])
            print("\033[2J\033[H" + contents, flush=True)
            if args.once:
                return 0
            time.sleep(max(0.0, started + REFRESH_SECONDS - time.monotonic()))
    except KeyboardInterrupt:
        return 0  # Ctrl+C 로 멈춘 것이므로 트레이스백 없이 끝나고, pane 은 원래 셸로 돌아간다
    finally:
        if args.pane:
            herdr_api.try_request("pane.release_agent", {"pane_id": args.pane, "source": SOURCE, "agent": AGENT_ID})


if __name__ == "__main__":
    raise SystemExit(main())
