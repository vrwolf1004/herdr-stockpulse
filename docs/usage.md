# Usage

## Requirements

- herdr 0.9.0 or later
- Python 3.8 or later; no third-party packages are required

Install the plugin:

```sh
herdr plugin install vrwolf1004/herdr-stockpulse
```

For local development:

```sh
herdr plugin link C:\work\app\herdr-stockpulse
```

## Configure stock symbols

Create `config.json` in the directory identified by `HERDR_PLUGIN_CONFIG_DIR`. If
that variable is not set, use:

- Windows: `%APPDATA%\herdr\plugins\config\herdr-stockpulse\config.json`
- Linux/macOS: `$XDG_CONFIG_HOME/herdr/plugins/config/herdr-stockpulse/config.json`
  (defaults to `~/.config` when `XDG_CONFIG_HOME` is not set)

```json
{
  "symbols": ["AAPL", "MSFT", "005930.KS", "035420.KS"]
}
```

- Use Yahoo Finance symbols. Korean KOSPI shares use `.KS`; KOSDAQ shares use
  `.KQ`. For example, Samsung Electronics is `005930.KS`.
- The plugin uses Yahoo Finance first and calculates the trend from its previous
  close. It shows `▲` for a rise, `▼` for a fall, and `•` when unchanged.

## Open the dashboard

Run **StockPulse: open dashboard** from herdr's action menu. The dashboard
always opens in the shared `herdr-dock` workspace, regardless of the currently
focused pane or workspace. It occupies a cell in the dock's 2×2 pane grid; it
does not split the currently focused workspace or open a separate window. It
reuses a free dock pane when available; otherwise it creates a pane in an
available grid cell. The dashboard is drawn in a box,
with colored `▲`/`▼` daily movement, quote timestamps, and the provider source
in its footer. Prices refresh automatically every 60 seconds.
Press `Ctrl+C` to stop the dashboard and return to the shell prompt; the pane
itself stays open.

- The shared `herdr-dock` workspace is kept at the bottom of the workspace
  list, where dock-style plugins such as `herdr-ai-feedbag` appear in the
  Agents sidebar.
- If three plugin blocks occupy the dock grid and its fourth cell is not
  already in use, StockPulse fills that cell with a plugin introduction pane.
  It leaves an existing empty cell available for a later block.
- Only one `stockpulse` agent is opened. Running the action again while it is
  already present does nothing.
- If creating or locating the dock workspace fails, the action reports the
  error in the action's stderr and does not open a partial dashboard.

You can also invoke the dashboard action directly:

```sh
herdr plugin action invoke open --plugin herdr-stockpulse
```

On Windows, use the platform-specific action ID:

```powershell
herdr plugin action invoke open-windows --plugin herdr-stockpulse
```

### Reopen after Ctrl+C

After Ctrl+C, run **StockPulse: open dashboard** again from the herdr action
menu, or invoke the action using one of the commands above. The previous
dashboard releases its agent registration; its sidebar quote rows expire
within about 90 seconds. Typing just `open` in a shell does not invoke the
plugin action. Put the action id first and the plugin in `--plugin`;
`herdr plugin action invoke herdr-stockpulse open-windows` fails with
`unknown option`.

**StockPulse: refresh configured quotes** remains available when you want a
one-time refresh in the herdr plugin command log.

## Show quotes in the Agents sidebar

The docked dashboard reports itself as a `stockpulse` agent. Add the following
rows to `[ui.sidebar.agents]` in herdr's `config.toml`, then reload the config:

```toml
[ui.sidebar.agents]
rows = [
  ["state_icon", "machine", "workspace", "tab"],
  ["agent"],
  [{ token = "$sp_quote_1_name", fg = "#c9d1d9", bold = true }],
  [{ token = "$sp_quote_1_price", fg = "#58a6ff" }],
  [{ token = "$sp_quote_2_name", fg = "#c9d1d9", bold = true }],
  [{ token = "$sp_quote_2_price", fg = "#58a6ff" }],
  [{ token = "$sp_quote_3_name", fg = "#c9d1d9", bold = true }],
  [{ token = "$sp_quote_3_price", fg = "#58a6ff" }],
  [{ token = "$sp_quote_4_name", fg = "#c9d1d9", bold = true }],
  [{ token = "$sp_quote_4_price", fg = "#58a6ff" }],
  [{ token = "$sp_quote_5_name", fg = "#c9d1d9", bold = true }],
  [{ token = "$sp_quote_5_price", fg = "#58a6ff" }],
  [{ token = "$sp_quote_more", fg = "#8b949e" }],
]
```

Preserve any existing rows, including `herdr-ai-feedbag` rows; append the
`$sp_quote_*` rows to the current `rows` array instead of replacing it. A row
is shown only when that quote exists on the StockPulse dashboard pane. Each
quote uses two rows: a bold company name followed by currency, current price,
and daily `▲`/`▼` percentage change. Long company names are shortened to keep
the name readable. If a provider does not return a company name, the stock
symbol is used instead. The first five successful quotes are shown in configured order; additional
successful quotes are summarized in the `$sp_quote_more` row. A symbol whose
quote fails is shown as an error in the dashboard and does not take a sidebar
quote slot.

The row remains visible while the pane is refreshing. If an unexpected refresh
failure occurs, the dashboard shows its error and retries after 60 seconds.
Invalid or unreadable configuration is shown as a configuration error in the
dashboard, and any sidebar quote tokens from the last successful refresh are
cleared; correct the file and wait for the next refresh.

```sh
herdr server reload-config
```

For an ad-hoc symbol without configuration:

```sh
python -X utf8 src/stockpulse.py quote AAPL 005930.KS
```

## Optional iTick fallback

If Yahoo Finance is unavailable, the plugin can use iTick when a token is set:

```json
{
  "symbols": ["005930.KS"],
  "itick_token": "your-iTick-token"
}
```

Keep the token in your personal plugin configuration. Do not commit it to a
repository. iTick's fallback response does not include the prior close used by
this plugin, so the price is displayed but its daily trend is unavailable.
