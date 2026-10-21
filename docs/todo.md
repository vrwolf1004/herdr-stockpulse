# TODO

개선 사항 목록. 우선순위는 체감 영향과 위험도 기준이며, 항목별로 관련 파일을 적어 둔다.

## 높음

- [ ] **공급자 응답 구조 검증**
  - Yahoo 응답의 중첩 필드가 없거나 예상 형식이 아니면 `IndexError`/`AttributeError`가 발생할 수 있다. 명확한 공급자 오류로 변환하고 부분·잘못된 JSON 테스트를 보강한다.
- [ ] **60초 갱신 간격을 요청 시간 포함 기준으로 유지**
  - 현재 렌더 이후 60초를 더 기다리므로 요청 시간이 주기만큼 추가된다. monotonic deadline 기준으로 다음 갱신을 예약하고 느린 요청 테스트를 추가한다.

- [x] **Windows named pipe 읽기에 타임아웃이 없음** (`src/herdr_api.py` `_exchange_pipe`)
  - Unix 소켓에만 `SOCKET_TIMEOUT_SECONDS`가 적용되어, herdr가 응답하지 않으면 패널 루프가 멈출 수 있다.
  - 개선: 오버랩 I/O 또는 별도 스레드 + join 타임아웃으로 상한을 둔다.
- [x] **iTick 토큰이 URL 쿼리와 헤더에 동시에 들어감** (`src/quotes.py` `ITICK_TICK_URL`, `fetch_itick`)
  - 토큰이 URL에 남으면 예외 메시지(`URLError` 문자열 등)와 로그에 노출될 수 있다.
  - 처리: 토큰을 헤더 인증으로만 보내도록 바꿨다. `HTTPError`/`URLError` 문자열에는 URL이 들어가지 않아 예외 메시지 정리는 따로 하지 않았다.
- [x] **종목을 순차 조회하여 갱신 주기가 길어질 수 있음** (`src/panel.py` `dashboard`)
  - 종목 N개 × 최대 10초 타임아웃으로 60초 주기를 넘길 수 있다.
  - 개선: `concurrent.futures.ThreadPoolExecutor`로 병렬 조회하고, 결과 순서는 설정 순서대로 유지한다.

## 중간

- [x] **설정 오류 시 사이드바 토큰이 TTL(90초)까지 남음** (`src/panel.py` `main`)
  - 설정 오류 분기에서는 `report_sidebar`를 호출하지 않아 이전 시세가 최대 90초 동안 그대로 보인다.
  - 처리: 설정 오류 시 빈 토큰(`{}`)을 보고해 이전 시세 행을 즉시 비운다.
- [x] **테스트 범위 확대** (`tests/`)
  - 현재 `test_quotes.py`만 있다. `render.py`는 일부, `stockpulse.py`의 `symbols_from`/`_itick_params`, `herdr_api.py`의 응답 파싱, `panel.py`의 토큰 보고 로직은 테스트가 없다.
  - 처리: `test_stockpulse.py`, `test_herdr_api.py`, `test_panel.py`를 추가했다. 소켓 호출은 `_exchange_unix`를 fake로 바꿔 검증한다. `herdr_cli`(`stockpulse.py`)는 아직 테스트하지 않았다.
- [x] **Python 3.8 지원 주장 검증** (`docs/usage.md`)
  - 문서에 3.8 이상을 명시했으나 실제 실행 확인은 3.12(`__pycache__`)만 보인다.
  - 처리: `uv python install 3.8`(3.8.20)로 로컬에서 전체 테스트를 통과했다. 3.12에서도 통과했다.
- [ ] **CI 없음** — 워크플로 추가 완료, 푸시 후 실제 실행 결과 확인 필요
  - 처리: `.github/workflows/test.yml`에 Windows/Linux/macOS × Python 3.8/3.12 매트릭스를 추가했다.
- [x] **Yahoo Finance 비공식 엔드포인트 의존에 대한 대응** (`src/quotes.py`)
  - 공식 API가 아니어서 차단이나 응답 형식 변경에 취약하다.
  - 처리: User-Agent를 `herdr-stockpulse`로 바꿔 버전 불일치를 없앴다.
  - 처리: 429·5xx·네트워크 오류(`TransientQuoteError`)에 한해 1초 뒤 한 번 재시도한다. 영구 오류(404 등)는 재시도하지 않는다.
  - 캐시는 넣지 않았다. 패널이 60초마다 갱신하므로 캐시 이득이 거의 없다고 판단했다.

## 낮음

- [ ] **`open` 액션의 중복 실행 경쟁** (`src/stockpulse.py` `open_dashboard`)
  - 에이전트 존재 확인과 패널 생성 사이에 간격이 있어, 연속 실행 시 패널이 두 번 열릴 수 있다.
- [ ] **Windows 소켓 경로 기본값 확인** (`src/herdr_api.py` `socket_path`)
  - `APPDATA` 미설정 시 빈 경로로 연결을 시도한다. 누락 시 명확한 오류를 내도록 한다.
- [ ] **`_exchange_pipe` 핸들 누수 가능성** (`src/herdr_api.py`)
  - `os.fdopen` 실패 경로에서 핸들이 닫히지 않을 수 있다. `try/finally`로 정리한다.
- [ ] **`dashboard` 예외 처리 범위** (`src/panel.py` `main`)
  - `except Exception`으로 전부 삼키고 있다. 재시도 가능한 오류와 설정 오류를 더 명확히 나눈다.
- [ ] **문서 정리** (`docs/usage.md`)
  - "Reopen after Ctrl+C" 절의 설명이 장황하다. 명령 예시를 먼저 두고 주의 사항을 뒤에 적는다.
  - 개발용 경로 `C:\work\app\herdr-stockpulse`가 하드코딩되어 있다. 일반 경로 예시로 바꾼다.
- [ ] **한국 종목 시세 실패 시 안내 개선** (`src/quotes.py`)
  - iTick 폴백은 전일 종가가 없어 등락을 표시하지 못한다. 가능하면 다른 제공자의 전일 종가를 찾아보거나, 현재 표시 문구를 더 분명히 한다.
