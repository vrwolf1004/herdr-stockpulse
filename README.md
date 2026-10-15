# herdr-stockpulse

Live stock prices with clear up/down trend indicators for herdr.

Enter stock symbols such as `AAPL` or `005930.KS` to see the latest price,
daily change, and a `▲`/`▼` trend indicator. The dashboard runs in the shared
`herdr-dock` workspace and reports a compact summary through the Agents
sidebar. Yahoo Finance is used by default without an API key; iTick is an
optional fallback.

```sh
herdr plugin install vrwolf1004/herdr-stockpulse
```

See [Usage](docs/usage.md) for installation, configuration, the docked
dashboard, and Agents sidebar setup. See [Architecture](docs/architecture.md)
for provider and reporting behavior.

## Development

```sh
python -m unittest discover -s tests
```
