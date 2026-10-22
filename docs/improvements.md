# 개선 문서

- 작성 기준: 2026-10-22, 커밋 `207f920` (`git log -1 --format=%h`)
- 공용 도크 모듈: `src/dock_layout.py` 는 복사본. `load_dock_layout()`(`src/stockpulse.py:22`)이 설치된 herdr-dock-grid 원본을 먼저 찾고, 없으면 이 복사본을 쓴다. 복사본은 herdr-dock-grid 0.7.1 원본과 내용이 같다(diff 확인).
- 할 일 목록: [todo.md](todo.md). 이미 적힌 항목은 옮기지 않고 거기서 관리한다.
- 표기: "확인됨" = 현재 코드에서 직접 본 내용. "확인 필요" = 코드로 추정만 했고 실행해 보지 않음.

## 개선 항목

- **[중간] `herdr_cli()` 에 시간 제한이 없음** (확인 필요)
  - 근거: `src/stockpulse.py:97-98`(`herdr_cli()`). 호출 위치: `:114`(`pane layout`), `:132`(`pane split`), `:138-139`(`agent list`, `pane list`), `:150-151`(`pane rename`, `pane run`).
  - herdr 가 응답하지 않으면 도크 칸을 만드는 단계가 멈춘다. 같은 문제가 `src/herdr_api.py:42`, `:140` 에도 있다(공용 모듈 항목). 고칠 때는 herdr-dock-grid 원본을 먼저 바꾸고 복사본을 맞춘다.

- **[낮음] 공용 소개 칸 파일 동기화를 도구로 확인할 수 있음** (확인됨, 개선 여지)
  - 근거: `tools/sync_dock_intro.py:16`(`PLUGINS` 목록), `tests/test_intro_sync.py:27-33`
  - 기준 파일은 이 저장소의 `src/intro.py` 이고 복사본은 herdr-radio, herdr-ai-feedbag, herdr-timekit, herdr-simple-git 에 있다. 현재 네 복사본은 기준 파일과 같다(diff 확인). 도구는 형제 저장소 폴더가 있어야 동작하므로, 저장소 하나만 받은 환경에서는 테스트가 건너뛰어진다는 점을 문서에 적는다.

## 관련 기존 항목 (todo.md)

- 한국 종목 시세 실패 안내: [todo.md](todo.md) 의 "한국 종목 시세 실패 시 안내 개선"
- 첫 실행 직후 에이전트가 안 보임, 소개 칸이 두 번 생길 수 있음: [todo.md](todo.md) 의 "실행 확인에서 찾은 개선점" 절
- 블록 제거 명령(`close`): [todo.md](todo.md) 의 "실행 확인에서 찾은 개선점" 절
