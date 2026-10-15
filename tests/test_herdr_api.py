from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import herdr_api
from herdr_api import HerdrError, request, try_request


def fake_exchange(response_line):
    def exchange(path, payload):
        exchange.payload = payload
        return response_line
    exchange.payload = None
    return exchange


class RequestTests(unittest.TestCase):
    def test_returns_result_from_response(self):
        exchange = fake_exchange(b'{"result": {"ok": true}}\n')
        with mock.patch.object(herdr_api, "IS_WINDOWS", False), \
                mock.patch.object(herdr_api, "_exchange_unix", exchange):
            self.assertEqual(request("pane.report_agent", {"pane_id": "p1"}), {"ok": True})

        sent = exchange.payload.decode("utf-8")
        self.assertIn('"method": "pane.report_agent"', sent)
        self.assertTrue(sent.endswith("\n"))

    def test_empty_response_returns_empty_result(self):
        exchange = fake_exchange(b"")
        with mock.patch.object(herdr_api, "IS_WINDOWS", False), \
                mock.patch.object(herdr_api, "_exchange_unix", exchange):
            self.assertEqual(request("pane.release_agent", {}), {})

    def test_error_response_raises_herdr_error(self):
        exchange = fake_exchange(b'{"error": "unknown pane"}\n')
        with mock.patch.object(herdr_api, "IS_WINDOWS", False), \
                mock.patch.object(herdr_api, "_exchange_unix", exchange):
            with self.assertRaisesRegex(HerdrError, "unknown pane"):
                request("pane.report_agent", {})

    def test_transport_failure_raises_herdr_error(self):
        def broken(path, payload):
            raise OSError("socket missing")

        with mock.patch.object(herdr_api, "IS_WINDOWS", False), \
                mock.patch.object(herdr_api, "_exchange_unix", broken):
            with self.assertRaisesRegex(HerdrError, "socket missing"):
                request("pane.report_agent", {})

    def test_try_request_returns_false_instead_of_raising(self):
        def broken(path, payload):
            raise OSError("socket missing")

        with mock.patch.object(herdr_api, "IS_WINDOWS", False), \
                mock.patch.object(herdr_api, "_exchange_unix", broken):
            self.assertFalse(try_request("pane.report_agent", {}))

    def test_try_request_returns_true_on_success(self):
        with mock.patch.object(herdr_api, "IS_WINDOWS", False), \
                mock.patch.object(herdr_api, "_exchange_unix", fake_exchange(b"{}\n")):
            self.assertTrue(try_request("pane.report_agent", {}))


if __name__ == "__main__":
    unittest.main()
