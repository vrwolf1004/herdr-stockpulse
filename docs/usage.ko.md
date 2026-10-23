# 사용법

[English](usage.md) | [**한국어**](usage.ko.md)

## 요구 사항

- herdr 0.9.0 이상
- Python 3.8 이상. 제3자 패키지는 필요 없습니다.

플러그인 설치:

```sh
herdr plugin install vrwolf1004/herdr-stockpulse
```

로컬 개발용으로 연결하려면:

```sh
herdr plugin link C:\work\app\herdr-stockpulse
```

## 종목 설정

`HERDR_PLUGIN_CONFIG_DIR` 환경 변수가 가리키는 폴더에 `config.json`을 만듭니다.
이 변수가 설정되지 않았다면 다음 경로를 사용합니다.

- Windows: `%APPDATA%\herdr\plugins\config\herdr-stockpulse\config.json`
- Linux/macOS: `$XDG_CONFIG_HOME/herdr/plugins/config/herdr-stockpulse/config.json`
  (`XDG_CONFIG_HOME`이 설정되지 않으면 `~/.config` 사용)

```json
{
  "symbols": ["AAPL", "MSFT", "005930.KS", "035420.KS"]
}
```

- Yahoo Finance 심볼을 사용합니다. 한국 KOSPI 종목에는 `.KS`, KOSDAQ 종목에는
  `.KQ`를 붙입니다. 예를 들어 삼성전자는 `005930.KS`입니다.
- 같은 종목은 여러 번 적어도 한 번만 쓰입니다. 대소문자와 앞뒤 공백은 무시하고, 처음 나온 순서를 유지합니다.
- 플러그인은 Yahoo Finance를 먼저 조회하고, 전일 종가로 추세를 계산합니다.
  상승은 `▲`, 하락은 `▼`, 변동 없음은 `•`로 표시합니다.

## 대시보드 열기

herdr 액션 메뉴에서 **StockPulse: open dashboard**를 실행합니다. 현재 포커스된
pane이나 workspace와 관계없이 대시보드는 항상 공유 `herdr-dock` workspace에
열립니다. 대시보드는 도크의 2×2 pane 그리드에서 한 칸을 차지하며, 현재 포커스된
workspace를 나누거나 별도 창을 여는 동작이 아닙니다. 사용 가능한 빈 도크 pane이
있으면 재사용하고, 없으면 비어 있는 그리드 칸에 pane을 만듭니다. 대시보드는 상자
안에 그려지며, 일일 등락의 `▲`/`▼`는 색으로 표시하고 하단에는 시세 시각과 제공자를
보여 줍니다. 시세는 60초마다 자동으로 갱신됩니다. 45초 안에 받지 못한 종목은 직전 값에 `지연`을 붙여 보이고, 직전 값이 없으면 `시세 대기 중`을 보입니다. `Ctrl+C`를 누르면 대시보드가
끝나고 pane은 셸 프롬프트로 돌아갑니다. pane 자체는 그대로 열려 있습니다.

- 공유 `herdr-dock` workspace는 workspace 목록 맨 아래에 유지됩니다. Agents
  사이드바에서 `herdr-ai-feedbag` 같은 도크형 플러그인이 나타나는 위치입니다.
- 도크 그리드의 세 칸에 플러그인 블록이 있고 네 번째 칸이 사용 중이 아니면,
  StockPulse는 그 칸에 플러그인 소개 pane을 표시합니다. 이미 비어 있는 칸이 있으면
  나중 블록이 쓸 수 있도록 그대로 둡니다.
- `stockpulse` agent는 하나만 열립니다. 이미 떠 있는 상태에서 액션을 다시 실행하면
  아무 일도 하지 않습니다.
- 도크 workspace를 찾거나 만드는 데 실패하면 액션 stderr에 오류를 표시하고, 일부만
  만들어진 대시보드는 열지 않습니다.

액션을 명령줄에서 직접 실행할 수도 있습니다.

```sh
herdr plugin action invoke open --plugin herdr-stockpulse
```

Windows에서는 플랫폼별 액션 ID를 사용합니다.

```powershell
herdr plugin action invoke open-windows --plugin herdr-stockpulse
```

### Ctrl+C 후 다시 열기

Ctrl+C 후에는 herdr 액션 메뉴에서 **StockPulse: open dashboard**를 다시 실행하거나,
위의 명령 중 하나로 액션을 실행합니다. 이전 대시보드의 agent 등록은 해제되며, 사이드바의
시세 행은 약 90초 안에 사라집니다. 셸에 `open`만 입력하면 플러그인 액션이 실행되지
않습니다. 액션 id를 먼저 쓰고 `--plugin`으로 플러그인을 지정해야 합니다.
`herdr plugin action invoke herdr-stockpulse open-windows`는 `unknown option` 오류로
실패합니다.

한 번만 갱신하고 싶다면 **StockPulse: refresh configured quotes** 액션을 실행합니다.
결과는 herdr 플러그인 명령 로그에 나타납니다.

## Agents 사이드바에 시세 표시

도크에 열린 대시보드는 `stockpulse` agent로 등록되고 `$sp_quote_*` 토큰을
보고합니다. herdr `config.toml`의 `[ui.sidebar.agents]` 아래 `rows`에 다음 행을
추가한 뒤 설정을 다시 불러와야 합니다.

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

기존 행, `herdr-ai-feedbag` 행을 포함해 모두 유지하고, `$sp_quote_*` 행은 현재
`rows` 배열에 덧붙이세요. 배열을 통째로 바꾸면 안 됩니다. 행은 StockPulse 대시보드
pane에 해당 시세가 있을 때만 표시됩니다. 시세 하나는 두 행을 씁니다. 굵은 회사 이름
행과, 통화·현재가·일일 `▲`/`▼` 등락률을 보여 주는 행입니다. 긴 회사 이름은 읽을 수
있도록 줄여서 표시합니다. 제공자가 회사 이름을 주지 않으면 종목 심볼을 대신 씁니다.
설정 순서대로 성공한 시세 처음 다섯 개를 표시하고, 추가로 성공한 시세는
`$sp_quote_more` 행에 요약합니다. 조회에 실패한 종목은 대시보드에 오류로 표시되며
사이드바 시세 슬롯을 차지하지 않습니다. 요청이 제공처에 막히면(요청 제한 또는 접근 거부) `시세 제공처가 요청을 막았습니다`로, 응답 형식이 예상과 다르면 `시세 제공처 응답 형식이 예상과 다릅니다`로 보입니다. 제공처의 원문 오류는 화면에 나오지 않습니다.

pane이 갱신되는 동안에도 행은 계속 보입니다. 예상하지 못한 갱신 실패가 생기면
대시보드에 오류를 표시하고 60초 뒤에 다시 시도합니다. 설정이 잘못되었거나 읽을 수
없으면 대시보드에 설정 오류로 표시되고, 마지막 성공 갱신에서 올린 사이드바 시세
토큰은 지웁니다. 파일을 고치면 다음 갱신에서 다시 읽습니다.

```sh
herdr server reload-config
```

설정 파일 없이 임시로 종목 하나를 조회하려면:

```sh
python -X utf8 src/stockpulse.py quote AAPL 005930.KS
```

## iTick 선택형 대체 제공자

Yahoo Finance를 쓸 수 없을 때 토큰을 설정하면 iTick을 사용할 수 있습니다. 토큰이 없으면 시세 조회가 실패했을 때 `iTick 토큰을 설정하면 대체 조회를 쓸 수 있습니다`라는 안내 한 줄이 보이고, 토큰이 있으면 이 안내는 보이지 않습니다.

```json
{
  "symbols": ["005930.KS"],
  "itick_token": "your-iTick-token"
}
```

토큰은 개인 플러그인 설정에만 두고, 저장소에 커밋하지 마세요. iTick의 대체 응답에는
이 플러그인이 쓰는 전일 종가가 없으므로, 현재가는 표시되지만 일일 등락은 표시되지
않습니다.
