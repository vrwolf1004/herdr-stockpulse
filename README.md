# herdr-stockpulse

[**English**](README.md) | [한국어](README.ko.md)

🌐 UI languages: 🇺🇸 English (en) · 🇰🇷 한국어 (ko) · 🇷🇺 Русский (ru) · 🇫🇷 Français (fr) · 🇪🇸 Español (es) · 🇩🇪 Deutsch (de) · 🇯🇵 日本語 (ja)

Show live stock prices and daily trends in a herdr dashboard and the Agents sidebar. Yahoo Finance is used by default; iTick is an optional fallback.

## Dashboard design

The dashboard shows configured symbols, prices, timestamps, and colored `▲`/`▼` daily trends. It refreshes every 60 seconds.

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
