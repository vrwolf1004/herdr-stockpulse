from pathlib import Path
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["HERDR_STOCKPULSE_LANG"] = "en"  # 테스트의 기대 문구는 영어 기준이다. i18n 을 읽기 전에 고정한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import panel


class ReportSidebarTests(unittest.TestCase):
    def test_skips_reporting_without_pane(self):
        with mock.patch.object(panel.herdr_api, "try_request") as try_request:
            panel.report_sidebar(None, {"sp_quote_1_name": "AAA"})
        try_request.assert_not_called()

    def test_reports_agent_and_tokens_for_pane(self):
        with mock.patch.object(panel.herdr_api, "try_request") as try_request:
            panel.report_sidebar("p1", {"sp_quote_1_name": "AAA"})

        methods = [call.args[0] for call in try_request.call_args_list]
        self.assertEqual(methods, ["pane.report_agent", "pane.report_metadata"])
        metadata = try_request.call_args_list[1].args[1]
        self.assertEqual(metadata["tokens"], {"sp_quote_1_name": "AAA"})
        self.assertEqual(metadata["ttl_ms"], panel.TOKEN_TTL_MS)


class ConfigErrorTests(unittest.TestCase):
    def test_configuration_error_clears_sidebar_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(json.dumps({"symbols": []}), encoding="utf-8")
            with mock.patch.object(sys, "argv", ["stockpulse-panel", "--config", str(config), "--once"]), \
                    mock.patch.object(panel, "report_sidebar") as report, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                exit_code = panel.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Configuration error", output.getvalue())
        report.assert_called_once_with(None, {})


class RefreshScheduleTest(unittest.TestCase):
    def test_slow_render_shortens_the_wait_instead_of_adding_to_it(self):
        clock = {"now": 100.0}
        sleeps = []

        def slow_render(_config):
            clock["now"] += 20.0  # 요청이 20초 걸렸다
            return "contents", {}

        def fake_sleep(seconds):
            sleeps.append(seconds)
            raise KeyboardInterrupt  # 두 번째 바퀴로 가지 않도록 한 번만 돌린다

        with mock.patch.object(panel, "render_once", side_effect=slow_render), \
                mock.patch.object(panel.time, "monotonic", side_effect=lambda: clock["now"]), \
                mock.patch.object(panel.time, "sleep", side_effect=fake_sleep), \
                mock.patch.object(sys, "argv", ["stockpulse-panel"]), \
                contextlib.redirect_stdout(io.StringIO()):
            panel.main()
        self.assertEqual(sleeps, [panel.REFRESH_SECONDS - 20.0])


class KeepAtBottomTest(unittest.TestCase):
    def run_with(self, workspaces):
        with mock.patch.object(panel.herdr_api, "request", return_value={"workspaces": workspaces}),                 mock.patch.object(panel.herdr_api, "try_request") as try_request:
            panel.keep_at_bottom()
        return try_request

    def test_moves_dock_to_the_end_when_it_is_not_last(self):
        try_request = self.run_with([
            {"workspace_id": "wM", "label": panel.DOCK_LABEL},
            {"workspace_id": "w4", "label": "app"},
        ])
        try_request.assert_called_once_with("workspace.move", {"workspace_id": "wM", "insert_index": 2})

    def test_does_nothing_when_dock_is_already_last(self):
        try_request = self.run_with([
            {"workspace_id": "w4", "label": "app"},
            {"workspace_id": "wM", "label": panel.DOCK_LABEL},
        ])
        try_request.assert_not_called()

    def test_does_nothing_without_dock(self):
        try_request = self.run_with([{"workspace_id": "w4", "label": "app"}])
        try_request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
