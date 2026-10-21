from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["HERDR_STOCKPULSE_LANG"] = "en"  # 테스트의 기대 문구는 영어 기준이다. i18n 을 읽기 전에 고정한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stockpulse import read_config, symbols_from
import stockpulse
from quotes import _itick_params


class SymbolsFromTests(unittest.TestCase):
    def test_uses_supplied_symbols_before_configured_ones(self):
        self.assertEqual(symbols_from({"symbols": ["MSFT"]}, ["aapl"]), ["AAPL"])

    def test_normalizes_configured_symbols(self):
        self.assertEqual(symbols_from({"symbols": [" 005930.ks "]}, []), ["005930.KS"])

    def test_rejects_non_string_entries(self):
        with self.assertRaisesRegex(ValueError, "non-empty array"):
            symbols_from({"symbols": ["AAPL", 3]}, [])

    def test_rejects_empty_symbol_list(self):
        with self.assertRaisesRegex(ValueError, "at least one symbol"):
            symbols_from({"symbols": []}, [])

    def test_rejects_missing_symbols(self):
        with self.assertRaisesRegex(ValueError, "at least one symbol"):
            symbols_from({}, [])


class ReadConfigTests(unittest.TestCase):
    def test_missing_file_returns_empty_config(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_config(Path(directory) / "missing.json"), {})

    def test_reads_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"symbols": ["AAPL"]}), encoding="utf-8")
            self.assertEqual(read_config(path), {"symbols": ["AAPL"]})

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot read configuration"):
                read_config(path)

    def test_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("[1, 2]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must contain a JSON object"):
                read_config(path)


class ITickParamsTests(unittest.TestCase):
    def test_korean_six_digit_code_uses_kr_region(self):
        self.assertEqual(_itick_params("005930"), ("KR", "005930"))

    def test_korean_suffixed_code_uses_kr_region(self):
        self.assertEqual(_itick_params("005930.KQ"), ("KR", "005930"))

    def test_us_symbol_uses_us_region(self):
        self.assertEqual(_itick_params("aapl"), ("US", "AAPL"))


class OpenLockTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.directory = tempfile.TemporaryDirectory()
        self.lock = os.path.join(self.directory.name, "open.lock")
        self.patch_lock = mock.patch.object(stockpulse, "OPEN_LOCK_PATH", self.lock)
        self.patch_lock.start()

    def tearDown(self):
        self.patch_lock.stop()
        self.directory.cleanup()

    def test_fresh_lock_skips_second_open(self):
        open(self.lock, "w").close()
        with mock.patch.object(stockpulse, "herdr_cli") as cli:
            self.assertEqual(stockpulse.open_dashboard(), 0)
        cli.assert_not_called()
        self.assertTrue(os.path.exists(self.lock))  # 다른 실행의 락은 지우지 않는다

    def test_lock_is_released_after_open(self):
        def fake_cli(*args):
            self.assertTrue(os.path.exists(self.lock))  # 여는 동안에는 락이 있다
            return {"agents": [{"agent": stockpulse.AGENT_ID}]}  # 이미 도킹되어 바로 끝난다

        with mock.patch.object(stockpulse, "herdr_cli", side_effect=fake_cli):
            self.assertEqual(stockpulse.open_dashboard(), 0)
        self.assertFalse(os.path.exists(self.lock))


if __name__ == "__main__":
    unittest.main()
