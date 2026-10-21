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
       -> find/create herdr-dock and reuse a free pane or create a grid pane
       -> do nothing when the stockpulse agent already exists
       -> pane.split + pane.run
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

The action always finds or creates `herdr-dock`, reusing a free pane or
splitting the dock's 2×2 layout. The current pane does not affect placement.
The dashboard command runs in the selected pane's shell;
Ctrl+C stops the command, releases the agent registration, and returns to the
shell prompt without closing the pane.

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
