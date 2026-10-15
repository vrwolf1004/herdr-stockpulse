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
        raise ValueError(f"Cannot read configuration {path}: {error}") from error
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration {path} must contain a JSON object")
    return loaded


def symbols_from(config: dict[str, Any], supplied: list[str]) -> list[str]:
    values = supplied or config.get("symbols", [])
    if not isinstance(values, list) or not all(isinstance(symbol, str) and symbol.strip() for symbol in values):
        raise ValueError('"symbols" must be a non-empty array of stock symbols')
    symbols = [symbol.strip().upper() for symbol in values]
    if not symbols:
        raise ValueError("Provide at least one symbol or configure \"symbols\"")
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
            print(f"{symbol}\n  Error: {error}", file=sys.stderr)
    return 1 if failures else 0


# Shared bottom workspace (see herdr-ai-feedbag docs/architecture.md, "herdr-dock 공용 규칙").
# Blocks living here are listed together at the bottom of the Agents sidebar.
DOCK_LABEL = "herdr-dock"
AGENT_ID = "stockpulse"
SIDEBAR_TOKEN_PREFIX = "herdr-sidebar"


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


def dock_anchor() -> str:
    """Find or create the herdr-dock workspace and return a pane to split the dashboard from."""
    workspaces = herdr_cli("workspace", "list").get("workspaces", [])
    dock = next((w["workspace_id"] for w in workspaces if w.get("label") == DOCK_LABEL), None)
    if dock is None:
        created = herdr_cli("workspace", "create", "--label", DOCK_LABEL, "--no-focus")
        dock = created["workspace"]["workspace_id"]
    panes = [p for p in herdr_cli("pane", "list").get("panes", []) if p["workspace_id"] == dock]
    candidates = [p["pane_id"] for p in panes if not is_sidebar(p)]
    if not candidates:
        raise RuntimeError(f"workspace {dock} has no pane")
    return candidates[-1]


def open_dashboard() -> int:
    agents = herdr_cli("agent", "list").get("agents", [])
    if any(agent.get("agent") == AGENT_ID for agent in agents):
        return 0  # already docked
    entrypoint = "dashboard-windows" if os.name == "nt" else "dashboard"
    try:
        anchor = dock_anchor()
    except (RuntimeError, ValueError, KeyError) as error:
        print(f"StockPulse: {error}", file=sys.stderr)
        return 1
    command = [
        os.environ.get("HERDR_BIN_PATH", "herdr"),
        "plugin", "pane", "open",
        "--plugin", PLUGIN_ID,
        "--entrypoint", entrypoint,
        "--placement", "split",
        "--direction", "down",
        "--target-pane", anchor,
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


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
