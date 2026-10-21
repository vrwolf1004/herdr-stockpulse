from pathlib import Path
import io
import sys
import unittest
from contextlib import redirect_stdout

ROOT_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_TESTS / "src"))
sys.path.insert(0, str(ROOT_TESTS / "tools"))

import intro  # noqa: E402
import sync_dock_intro  # noqa: E402


class IntroBoxTests(unittest.TestCase):
    def test_lists_three_plugins_and_search_footer(self):
        output = io.StringIO()
        with redirect_stdout(output):
            intro.main()
        text = output.getvalue()
        for name in ("herdr-timekit", "herdr-radio", "herdr-talk"):
            self.assertIn(name, text)
        self.assertIn('Search "vrwolf1004"', text)
        self.assertNotIn("herdr-simple-git", text)


class IntroSyncTests(unittest.TestCase):
    def test_copies_match_canonical_when_present(self):
        # 다른 플러그인 저장소가 없는 환경에서는 건너뛴다.
        present = [path for path in sync_dock_intro.targets() if path.parent.parent.is_dir()]
        if not present:
            self.skipTest("plugin repositories not found")
        self.assertEqual(sync_dock_intro.check(), 0)


if __name__ == "__main__":
    unittest.main()
