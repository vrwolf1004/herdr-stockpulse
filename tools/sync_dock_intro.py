"""도크 소개 칸의 intro.py 를 기준 파일에서 각 플러그인으로 복사하거나, 같은지 확인한다.

기준 파일은 herdr-stockpulse/src/intro.py 이다. 복사본은 아래 플러그인의 src/intro.py 이다.

  python tools/sync_dock_intro.py          기준 파일을 각 플러그인에 복사한다
  python tools/sync_dock_intro.py --check  복사본이 기준과 다르면 목록을 보여 주고 1로 끝난다
"""

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 플러그인 저장소들이 있는 폴더 (예: C:\work\app)
CANONICAL = Path(__file__).resolve().parents[1] / "src" / "intro.py"
PLUGINS = ["herdr-radio", "herdr-ai-feedbag", "herdr-timekit", "herdr-simple-git"]


def targets():
    return [ROOT / name / "src" / "intro.py" for name in PLUGINS]


def check():
    source = CANONICAL.read_bytes()
    stale = [path for path in targets() if not path.is_file() or path.read_bytes() != source]
    for path in stale:
        print(f"다름: {path}")
    return 1 if stale else 0


def sync():
    for path in targets():
        shutil.copyfile(CANONICAL, path)
        print(f"복사: {path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="dock intro.py 동기화")
    parser.add_argument("--check", action="store_true", help="복사하지 않고 같은지만 확인한다")
    args = parser.parse_args(argv)
    return check() if args.check else sync()


if __name__ == "__main__":
    sys.exit(main())
