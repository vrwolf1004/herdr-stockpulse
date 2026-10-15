# Architecture

`herdr-stockpulse` is a small Python plugin with no third-party dependencies.
The `open` action ensures a single `stockpulse` agent is running, then creates
its split dashboard pane in the shared `herdr-dock` workspace. The pane reads
configured symbols, requests their current prices, renders one block per
symbol, and refreshes every 60 seconds.

```text
herdr open action
  -> src/stockpulse.py
       -> find or create the herdr-dock workspace
       -> do nothing when the stockpulse agent already exists
       -> herdr plugin pane open
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

The action finds the last non-sidebar pane in the `herdr-dock` workspace and
splits the StockPulse dashboard below it. If the workspace does not exist, it
creates it without changing focus.

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

The dashboard refresh interval is 60 seconds. Individual provider failures are
rendered beside their affected symbol. Configuration errors and unexpected
refresh errors remain visible in the pane, and the latter are retried on the
next interval.

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
