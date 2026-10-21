"""herdr-stockpulse command entry point."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Optional

from quotes import QuoteError, fetch_quote
from i18n import t
from render import format_quote

PLUGIN_ID = "herdr-stockpulse"


def config_path(explicit_path: Optional[str]) -> Path:
    if explicit_path:
        return Path(explicit_path)
    config_dir = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    if config_dir:
        return Path(config_dir) / "config.json"
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "herdr" / "plugins" / "config" / "herdr-stockpulse" / "config.json"


def read_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(t("config.read_error", path=path, error=error)) from error
    if not isinstance(loaded, dict):
        raise ValueError(t("config.not_object", path=path))
    return loaded


def symbols_from(config: dict[str, Any], supplied: list[str]) -> list[str]:
    values = supplied or config.get("symbols", [])
    if not isinstance(values, list) or not all(isinstance(symbol, str) and symbol.strip() for symbol in values):
        raise ValueError(t("config.bad_symbols"))
    symbols = [symbol.strip().upper() for symbol in values]
    if not symbols:
        raise ValueError(t("config.no_symbols"))
    return symbols


def run_quote(symbols: list[str], itick_token: str) -> int:
    failures = 0
    for index, symbol in enumerate(symbols):
        if index:
            print()
        try:
            print(format_quote(fetch_quote(symbol, itick_token)))
        except QuoteError as error:
            failures += 1
            print(f"{symbol}\n  {t('quote.error', error=error)}", file=sys.stderr)
    return 1 if failures else 0


# Shared bottom workspace (see herdr-ai-feedbag docs/architecture.md, "herdr-dock 공용 규칙").
# Blocks living here are listed together at the bottom of the Agents sidebar.
DOCK_LABEL = "herdr-dock"
AGENT_ID = "stockpulse"
SIDEBAR_TOKEN_PREFIX = "herdr-sidebar"
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PANEL_PATH = os.path.join(SRC_DIR, "panel.py")
# 도크 블록이 3개일 때 빈 4번째 칸에 띄우는 소개 pane 의 이름. 이름이 있으면 소개 칸이 이미 있는 것이다.
INTRO_LABEL = "herdr-dock-intro"
INTRO_SCRIPT = os.path.join(SRC_DIR, "intro.py")


def herdr_cli(*args: str) -> dict[str, Any]:
    completed = subprocess.run(
        [os.environ.get("HERDR_BIN_PATH", "herdr"), *args],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stdout + completed.stderr).strip() or f"herdr {' '.join(args)} failed")
    output = completed.stdout.strip().lstrip("﻿")
    return json.loads(output).get("result", {}) if output else {}


def is_sidebar(pane: dict[str, Any]) -> bool:
    return any(name.startswith(SIDEBAR_TOKEN_PREFIX) for name in (pane.get("tokens") or {}))


def dock_workspace() -> str:
    """herdr-dock workspace 의 id. 없으면 만든다."""
    workspaces = herdr_cli("workspace", "list").get("workspaces", [])
    dock = next((w["workspace_id"] for w in workspaces if w.get("label") == DOCK_LABEL), None)
    if dock is None:
        created = herdr_cli("workspace", "create", "--label", DOCK_LABEL, "--no-focus")
        dock = created["workspace"]["workspace_id"]
    return dock


def grid_split(anchor: str, cwd: str) -> str:
    """dock 을 2x2 로 나눈다. 자리는 왼쪽 위, 오른쪽 위, 왼쪽 아래, 오른쪽 아래 순서이고 빈 자리는 빈 채로 둔다 (feedbag 과 같은 규칙)."""
    layout = herdr_cli("pane", "layout", "--pane", anchor)["layout"]
    area = layout["area"]
    corners = {}
    for pane in layout["panes"]:
        rect = pane["rect"]
        corners[(0 if rect["x"] <= area["x"] else 1, 0 if rect["y"] <= area["y"] else 1)] = pane["pane_id"]
    top_left, top_right = corners.get((0, 0)), corners.get((1, 0))
    bottom_left, bottom_right = corners.get((0, 1)), corners.get((1, 1))
    if top_left and not top_right:
        target, direction = top_left, "right"
    elif top_left and not bottom_left:
        target, direction = top_left, "down"
    elif top_right and not bottom_right:
        target, direction = top_right, "down"
    elif bottom_left and not bottom_right:
        target, direction = bottom_left, "right"
    else:
        target, direction = anchor, "down"
    split = herdr_cli("pane", "split", target, "--direction", direction, "--cwd", cwd, "--no-focus")
    return split["pane"]["pane_id"]


def ensure_intro(dock: str, new_pane: str) -> None:
    """도크 블록이 3개이고 소개 칸이 없으면 빈 4번째 칸에 소개 문구를 띄운다. 이미 있으면 아무것도 하지 않는다."""
    agent_panes = {a["pane_id"] for a in herdr_cli("agent", "list").get("agents", [])}
    panes = [p for p in herdr_cli("pane", "list").get("panes", [])
             if p["workspace_id"] == dock and not is_sidebar(p)]
    if any(p.get("label") == INTRO_LABEL for p in panes):
        return
    blocks = [p for p in panes if p["pane_id"] in agent_panes or p["pane_id"] == new_pane]
    if len(blocks) != 3:
        return
    if any(not p.get("label") and not p.get("tokens") and p["pane_id"] not in agent_panes and p["pane_id"] != new_pane
           for p in panes):
        return  # 빈 칸이 이미 있으면 그 칸은 나중 블록이 쓴다
    pane_id = grid_split(blocks[0]["pane_id"], SRC_DIR)
    herdr_cli("pane", "rename", pane_id, INTRO_LABEL)
    herdr_cli("pane", "run", pane_id, sys.executable, "-X", "utf8", INTRO_SCRIPT)


def open_dashboard() -> int:
    agents = herdr_cli("agent", "list").get("agents", [])
    if any(agent.get("agent") == AGENT_ID for agent in agents):
        return 0  # already docked
    # 대시보드는 dock 의 2x2 격자 안에 들어간다. 빈 pane 이 있으면 쓰고, 없으면 격자로 나눈다.
    # 대시보드가 끝나면(Ctrl+C) 그 셸 프롬프트가 그대로 남는다.
    try:
        dock = dock_workspace()
        panes = [p for p in herdr_cli("pane", "list").get("panes", [])
                 if p["workspace_id"] == dock and not is_sidebar(p)]
        if not panes:
            raise RuntimeError(t("dock.no_pane", workspace=dock))
        agent_panes = {a["pane_id"] for a in agents}
        free = [p for p in panes if not p.get("tokens") and p["pane_id"] not in agent_panes
                and (not p.get("label") or p.get("label") == INTRO_LABEL)]
        if free:
            pane_id = free[0]["pane_id"]
            if free[0].get("label") == INTRO_LABEL:
                herdr_cli("pane", "rename", pane_id, "--clear")  # 소개 칸을 블록이 쓰므로 이름을 지운다
        else:
            pane_id = grid_split(panes[0]["pane_id"], SRC_DIR)
        herdr_cli("pane", "run", pane_id, sys.executable, "-X", "utf8", PANEL_PATH, "--pane", pane_id)
        ensure_intro(dock, pane_id)
    except (RuntimeError, ValueError, KeyError) as error:
        print(f"StockPulse: {error}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="stockpulse",
        description="Display live stock prices and up/down movement from the prior close.",
    )
    parser.add_argument("action", choices=["quote", "panel"])
    parser.add_argument("symbols", nargs="*", help="Symbols such as AAPL or 005930.KS")
    parser.add_argument("--config", help="Path to a configuration JSON file")
    args = parser.parse_args()

    if args.action == "panel":
        return open_dashboard()

    try:
        config = read_config(config_path(args.config))
        return run_quote(symbols_from(config, args.symbols), str(config.get("itick_token", "")))
    except ValueError as error:
        print(f"StockPulse: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
