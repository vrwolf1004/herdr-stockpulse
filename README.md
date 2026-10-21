# herdr-stockpulse

[**English**](README.md) | [한국어](README.ko.md)

UI languages: English · Korean · Russian · French · Spanish · German · Japanese

Show live stock prices and daily trends in a herdr dashboard and the Agents sidebar. Yahoo Finance is used by default; iTick is an optional fallback.

The dashboard opens in the shared `herdr-dock` workspace, placed in its 2×2
pane grid rather than splitting the currently focused workspace. The dock stays
at the bottom of the workspace list; when three plugin blocks occupy the grid,
an introduction pane fills the remaining cell. See the [usage guide](docs/usage.md)
for placement and configuration-error behavior.

## Dashboard design

Agents sidebar:

```text
 ● Apple Inc.
   ▲ $189.84 +1.24%
 ● Microsoft
   ▼ $420.72 -0.36%
```

Dashboard:

```text
╭──────────────────────────────────────────────────────────────╮
│                  🐺  herdr-stockpulse  🌕                   │
├──────────────────────────────────────────────────────────────┤
│ AAPL (Apple Inc.)                                            │
│   189.84 USD  ▲ +2.31 (+1.23%)                               │
│   2025-03-08 15:30 UTC                                       │
├──────────────────────────────────────────────────────────────┤
│ MSFT (Microsoft Corporation)                                 │
│   420.72 USD  ▼ -1.52 (-0.36%)                               │
│   2025-03-08 15:30 UTC                                       │
├──────────────────────────────────────────────────────────────┤
│ Yahoo Finance   Refreshes every 60 seconds   Ctrl+C to close │
╰──────────────────────────────────────────────────────────────╯
```

The values and timestamp above are illustrative; the dashboard shows the
configured symbols and their latest provider data.

## Installation

```sh
herdr plugin install vrwolf1004/herdr-stockpulse
```

## Actions

| Action | What it does |
| --- | --- |
| `open` | Open the stock dashboard |
| `quote` | Refresh configured quotes once in the plugin command log |

On Windows, append `-windows` to each action ID. See the [usage guide](docs/usage.md) to configure symbols and sidebar rows.

## Requirements

- Windows, Linux, or macOS
- herdr 0.9.0 or later
- Python 3.8 or later; standard library only

## Documentation

- [Usage and setup](docs/usage.md)
- [Architecture](docs/architecture.md)
- [TODO](docs/todo.md)

## Development

```sh
python -m unittest discover -s tests
```

## Support the project

If this project is useful to you, consider buying the developer a coffee.

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
