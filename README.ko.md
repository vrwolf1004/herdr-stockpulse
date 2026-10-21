# herdr-stockpulse

[English](README.md) | [**한국어**](README.ko.md)

지원 언어: 영어 · 한국어 · 러시아어 · 프랑스어 · 스페인어 · 독일어 · 일본어

herdr 대시보드와 Agents 사이드바에서 주식 현재가와 전일 대비 추세를 보여 줍니다. 기본 제공자는 Yahoo Finance이며 iTick은 선택형 대체 제공자입니다.

## 대시보드 디자인

설정한 종목의 가격, 시각, 등락을 표시합니다. 상승 `▲`은 초록색, 하락 `▼`은 빨간색으로 표시하며 60초마다 갱신합니다.

## 설치

```sh
herdr plugin install vrwolf1004/herdr-stockpulse
```

## 액션

| 액션 | 기능 |
| --- | --- |
| `open` | 주식 대시보드 열기 |
| `quote` | 설정한 종목 시세를 플러그인 명령 로그에서 한 번 갱신 |

Windows에서는 각 액션 ID 뒤에 `-windows`를 붙입니다. 종목과 사이드바 줄 설정은 [사용법](docs/usage.md)을 참고하세요 (영문).

## 요구 사항

- Windows, Linux, macOS
- herdr 0.9.0 이상
- Python 3.8 이상, 표준 라이브러리만 사용

## 문서

- [사용법 (영문)](docs/usage.md)
- [구조 (영문)](docs/architecture.md)
- [TODO (영문)](docs/todo.md)

## 개발

```sh
python -m unittest discover -s tests
```

## 프로젝트 응원하기

프로젝트가 도움이 되셨다면 커피 한 잔으로 개발을 응원해 주세요.

[![Ko-fi에서 응원하기](https://img.shields.io/badge/Ko--fi-%EC%9D%91%EC%9B%90%ED%95%98%EA%B8%B0-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
