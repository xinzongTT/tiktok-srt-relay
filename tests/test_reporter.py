import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_reporter_module():
    spec = importlib.util.spec_from_file_location("reporter_under_test", ROOT / "scripts" / "reporter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReporterTests(unittest.TestCase):
    def test_build_streams_from_mediamtx_paths(self):
        reporter = load_reporter_module()
        api_payload = {
            "items": [
                {
                    "name": "phone",
                    "source": {"type": "srtConn"},
                    "readers": [{"type": "srtConn"}],
                    "inboundFramesInError": 2,
                },
                {
                    "name": "music",
                    "source": None,
                    "readers": [],
                    "inboundFramesInError": 0,
                },
            ]
        }

        streams = reporter.build_streams(api_payload, {}, {}, {})

        self.assertEqual(streams[0]["name"], "phone")
        self.assertTrue(streams[0]["publishing"])
        self.assertEqual(streams[0]["readers"], 1)
        self.assertEqual(streams[0]["frames_error"], 2)
        self.assertEqual(streams[0]["last_event"], "publishing")
        self.assertEqual(streams[1]["name"], "music")
        self.assertFalse(streams[1]["publishing"])
        self.assertEqual(streams[1]["readers"], 0)
        self.assertEqual(streams[1]["last_event"], "idle")

    def test_reporter_can_send_report_token(self):
        source = (ROOT / "scripts" / "reporter.py").read_text(encoding="utf-8")

        self.assertIn('os.environ.get("REPORT_TOKEN"', source)
        self.assertIn('"X-Report-Token"', source)


if __name__ == "__main__":
    unittest.main()
