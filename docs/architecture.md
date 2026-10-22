# Architecture

`herdr-stockpulse` is a small Python plugin with no third-party dependencies.
The `open` action ensures a single `stockpulse` agent is running, then opens the
dashboard in the shared `herdr-dock` workspace, regardless of the current
pane. It reuses a free non-sidebar dock pane or creates a pane in the dock's
2×2 layout. The dashboard reads configured symbols, requests their current
prices, renders a boxed, colored view, and refreshes every 60 seconds.

```text
herdr open action
  -> src/stockpulse.py
       -> ensure_dock_pane("herdr-stockpulse") from herdr-dock-grid (or the local copy)
       -> do nothing when the stockpulse agent already exists
       -> place dashboard in a cell of the dock's 2×2 pane grid, then pane.run
       -> add the introduction pane when three blocks occupy the grid
            -> src/panel.py
                 -> config.json: symbols and optional iTick token
                 -> src/quotes.py
                      -> Yahoo Finance chart API
                      -> iTick API only after a Yahoo failure
                 -> src/render.py
                      -> detail blocks and compact sidebar summary
                 -> src/herdr_api.py
                      -> report stockpulse agent and $sp_quotes token
```

## herdr docking and reporting

> `herdr-dock-grid` 연결은 선택입니다. 설치되어 있지 않으면 `src/dock_layout.py` 복사본으로 동작합니다.

The action always places the dashboard in the shared `herdr-dock` workspace's
2×2 pane grid through `ensure_dock_pane("herdr-stockpulse")`, reusing its own
pane when available. When the grid is full, the next `herdr-dock2`, `herdr-dock3`
... workspace is used. This is placement within the shared dock, not a split of
the currently focused workspace or a separate window. If three plugin blocks occupy the grid and the
fourth cell is not already in use, the action fills it with the introduction
pane; an existing empty cell is left available for a later block. The dock
workspace is moved to the bottom of the workspace list during dashboard
refreshes. The pane runs `stockpulse dock-host`, which runs the panel and then calls
`release_dock_pane("herdr-stockpulse")` when the panel exits. Ctrl+C in the
panel therefore releases the slot as well. If the pane is closed by force, the
process ends before that call; the allocation and the `herdr-stockpulse.dock`
marker are then removed by the next `ensure_dock_pane` call (or by `reset`).

The dashboard uses herdr's socket API to:

1. Register its pane as the idle `stockpulse` agent.
2. Report one `$sp_quote_N` token for each visible quote with a 90-second TTL.
3. Release the agent registration when the dashboard stops.

The first five successful quotes in configured order are reported as two rows each:
`$sp_quote_N_name` contains the company name and `$sp_quote_N_price` contains
the trend marker, currency, price, and daily percentage. Long names are
shortened; the symbol is used only when a provider has no company name. Any
remaining configured symbols are represented by `$sp_quote_more` as
`+N more symbols`. The Agents sidebar displays tokens only when its layout
includes the matching `$sp_quote_*` rows.

The dashboard refresh interval is 60 seconds. Each quote shows its name, price
and update time; daily rises and falls are colored, and the footer lists quote
providers in use. Individual provider failures are rendered beside their
affected symbol. Configuration errors and unexpected refresh errors remain
visible in the pane, and the latter are retried on the next interval.

## Providers

The provider order matches the previous Chrome StockPulse extension:

1. Yahoo Finance's chart endpoint is used first and needs no API key. It returns
   `regularMarketPrice` and `chartPreviousClose`, which produce the daily
   direction and percentage.
2. iTick is tried only if Yahoo Finance fails and the user configured
   `itick_token`. It is primarily useful for Korean symbols, but the basic tick
   response does not provide a previous close, so no direction is inferred.

Provider or malformed-response failures are surfaced for each individual symbol.
One failing symbol does not stop the remaining configured symbols from refreshing.

## Source layout

| Path | Responsibility |
| --- | --- |
| `src/stockpulse.py` | Command-line entry point and configuration validation |
| `src/panel.py` | Refreshing docked dashboard, agent registration, and token reporting |
| `src/quotes.py` | Provider requests, JSON parsing, normalization, and fallback |
| `src/render.py` | Detail presentation and compact sidebar summary |
| `src/herdr_api.py` | Cross-platform herdr socket client for pane metadata |
| `herdr-plugin.toml` | herdr plugin metadata and platform-specific actions |
