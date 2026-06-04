import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class InstallMonitorScriptTests(unittest.TestCase):
    def test_install_monitor_script_exists_and_wires_systemd_reporter(self):
        script = (ROOT / "install-monitor.sh").read_text(encoding="utf-8")

        self.assertIn("DEFAULT_HUB=\"http://23.238.118.221:9988/api/report\"", script)
        self.assertIn("ENV_FILE=\"/etc/tiktok-srt-reporter.env\"", script)
        self.assertIn("SERVICE_FILE=\"/etc/systemd/system/tiktok-srt-reporter.service\"", script)
        self.assertIn("ExecStart=/bin/bash /opt/tiktok-srt-relay/scripts/reporter-start.sh", script)
        self.assertIn("systemctl enable tiktok-srt-reporter", script)
        self.assertIn("systemctl restart tiktok-srt-reporter", script)
        self.assertIn("HUB=\"${HUB:-$DEFAULT_HUB}\"", script)
        self.assertIn("MTX_API=\"${MTX_API:-http://127.0.0.1:9997/v3/paths/list}\"", script)
        self.assertIn("MTX_AUTH=\"${MTX_AUTH:-admin:monitor}\"", script)
        self.assertIn("REPORT_INTERVAL=\"${REPORT_INTERVAL:-5}\"", script)
        self.assertIn("REPORT_TOKEN=\"${REPORT_TOKEN:-}\"", script)
        self.assertIn("REPORT_TOKEN=$REPORT_TOKEN", script)

    def test_readme_documents_domain_reverse_proxy_usage(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("install-monitor.sh", readme)
        self.assertIn("HUB=https://你的域名/api/report", readme)
        self.assertIn("REPORT_TOKEN=", readme)
        self.assertIn("tiktok-srt-reporter", readme)


if __name__ == "__main__":
    unittest.main()
