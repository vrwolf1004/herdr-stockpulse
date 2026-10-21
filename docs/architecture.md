# Architecture

`herdr-stockpulse` is a small Python plugin with no third-party dependencies.
The `open` action ensures a single `stockpulse` agent is running, then splits a
dashboard pane below the current pane. If there is no current pane, it finds or
creates the shared `herdr-dock` workspace and splits from one of its
non-sidebar panes. The dashboard reads configured symbols, requests their
current prices, renders a boxed, colored view, and refreshes every 60 seconds.

```text
herdr open action
  -> src/stockpulse.py
       -> use current pane, or find/create herdr-dock when no pane is available
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

When invoked from a pane, the action splits the dashboard below that pane (so
it shares the dock only when that pane belongs to `herdr-dock`). If there is no
current pane, it finds or creates `herdr-dock` and splits below its last
non-sidebar pane. The dashboard command runs in the new pane's shell;
Ctrl+C stops the command, releases the agent registration, and returns to the
shell prompt without closing the pane.

The dashboard uses herdr's socket API to:

1. Register its pane as the idle `stockpulse` agent.
2. Report one `$sp_quote_N` token for each visible quote with a 90-second TTL.
3. Release the agent registration when the dashboard stops.

The first five quotes in configured order are reported as two rows each:
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
