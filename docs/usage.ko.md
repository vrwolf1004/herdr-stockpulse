# 사용법

[English](usage.md) | [**한국어**](usage.ko.md)

## 설치 및 종목 설정

```sh
herdr plugin install vrwolf1004/herdr-stockpulse
```

`HERDR_PLUGIN_CONFIG_DIR` 환경 변수가 지정된 경우 그 폴더에 `config.json`을
만듭니다. 지정되지 않았다면 기본 경로는 다음과 같습니다.

- Windows: `%APPDATA%\herdr\plugins\config\herdr-stockpulse\config.json`
- Linux/macOS: `$XDG_CONFIG_HOME/herdr/plugins/config/herdr-stockpulse/config.json`
  (`XDG_CONFIG_HOME`이 설정되지 않으면 `~/.config` 사용)

```json
{
  "symbols": ["AAPL", "MSFT", "005930.KS", "035420.KS"]
}
```

Yahoo Finance 심볼을 사용합니다. 한국 KOSPI 종목에는 `.KS`, KOSDAQ 종목에는
`.KQ`를 붙입니다. Yahoo Finance를 먼저 조회하며, `itick_token`을 설정한 경우
Yahoo 조회에 실패하면 iTick을 대체 제공자로 사용합니다.

## 대시보드 열기

herdr 액션 메뉴에서 **StockPulse: open dashboard**를 실행합니다. 현재 포커스된
pane이나 workspace와 관계없이 대시보드는 공유 `herdr-dock` workspace에 열립니다.
사용 가능한 빈 pane이 있으면 재사용하고, 없으면 도크의 2×2 레이아웃에 pane을
추가합니다. 대시보드는 60초마다 갱신되며, 개별 종목 오류는 해당 종목 아래에
표시되고 다른 종목의 갱신은 계속됩니다.

Windows에서는 액션 ID에 `-windows`를 붙입니다.

```sh
herdr plugin action invoke open --plugin herdr-stockpulse
```

```powershell
herdr plugin action invoke open-windows --plugin herdr-stockpulse
```

`Ctrl+C`를 누르면 대시보드 실행이 끝나고 pane은 셸 프롬프트로 돌아갑니다.
다시 열려면 액션을 다시 실행하세요. 동시에 하나의 `stockpulse` agent만 열립니다.
한 번만 시세를 조회하려면 **StockPulse: refresh configured quotes** 액션을
실행합니다. Windows 액션 ID는 `quote-windows`입니다.

## Agents 사이드바에 시세 표시

대시보드 pane은 `stockpulse` agent로 등록되고 `$sp_quote_*` 토큰을 보고합니다.
herdr `config.toml`의 `[ui.sidebar.agents]` 아래 `rows`에 토큰 행을 추가하고
`herdr server reload-config`를 실행해야 표시됩니다. 기존 행을 유지하고 필요한
`$sp_quote_*` 행을 추가하세요. 자세한 TOML 예시는 [영문 사용법](usage.md#show-quotes-in-the-agents-sidebar)을
참고하세요.

성공한 시세 중 설정 순서상 처음 다섯 개까지 회사명과 가격 행이 표시됩니다.
추가 성공 시세는 `$sp_quote_more` 행에 요약됩니다. 조회에 실패한 종목은 대시보드에
오류로 표시되며 사이드바 시세 슬롯을 차지하지 않습니다. iTick 응답에는 전일 종가가
없으므로 해당 종목의 일일 등락은 표시되지 않습니다.

## iTick 토큰

iTick을 대체 제공자로 사용하려면 개인 플러그인 설정의 `config.json`에 토큰을
추가합니다. 토큰을 저장소에 커밋하지 마세요.

```json
{
  "symbols": ["005930.KS"],
  "itick_token": "your-iTick-token"
}
```
