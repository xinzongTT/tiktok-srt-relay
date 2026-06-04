import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_manage_module(base_dir):
    spec = importlib.util.spec_from_file_location("manage_under_test", ROOT / "scripts" / "manage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE_DIR = base_dir
    module.MEDIAMTX_FILE = base_dir / "mediamtx.yml"
    module.TEMPLATE_FILE = base_dir / "mediamtx.yml.template"
    module.ENV_FILE = base_dir / ".env"
    module.DOCKER_COMPOSE_FILE = base_dir / "docker-compose.yml"
    return module


class ManageConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        shutil.copy2(ROOT / "mediamtx.yml.template", self.base / "mediamtx.yml.template")
        (self.base / ".env").write_text(
            "\n".join(
                [
                    "PUBLIC_HOST=127.0.0.1",
                    "STREAM_PATH=phone",
                    "SRT_PORT=8890",
                    "SRT_PUBLISH_LATENCY=400",
                    "SRT_READ_LATENCY=500000",
                    "SRT_PUBLISH_PASSPHRASE=AAAAAAAAAAAAAAAAAAAA",
                    "SRT_READ_PASSPHRASE=BBBBBBBBBBBBBBBBBBBB",
                    "MUSIC_PATH=music",
                    "MUSIC_PUBLISH_PASSPHRASE=CCCCCCCCCCCCCCCCCCCC",
                    "MUSIC_READ_PASSPHRASE=DDDDDDDDDDDDDDDDDDDD",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.manage = load_manage_module(self.base)
        self.assertTrue(self.manage.init_from_template())

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_stream_adds_auth_permissions(self):
        parsed = self.manage.parse_yml()
        ok, result = self.manage.add_stream("zs1", parsed, self.manage.load_env())

        self.assertTrue(ok, result)
        text = (self.base / "mediamtx.yml").read_text(encoding="utf-8")
        self.assertIn("  zs1:", text)
        self.assertIn("      - action: publish\n        path: zs1", text)
        self.assertIn("      - action: read\n        path: zs1", text)

    def test_delete_stream_removes_auth_permissions(self):
        parsed = self.manage.parse_yml()
        ok, result = self.manage.add_stream("zs1", parsed, self.manage.load_env())
        self.assertTrue(ok, result)

        parsed = self.manage.parse_yml()
        ok, message = self.manage.delete_stream("zs1", parsed)

        self.assertTrue(ok, message)
        text = (self.base / "mediamtx.yml").read_text(encoding="utf-8")
        self.assertNotIn("  zs1:", text)
        self.assertNotIn("path: zs1", text)

    def test_manage_menu_uses_reporter_not_old_monitor(self):
        source = (ROOT / "scripts" / "manage.py").read_text(encoding="utf-8")

        self.assertIn("reporter_control", source)
        self.assertIn("configure_reporter", source)
        self.assertIn("reporter-start.sh", source)
        self.assertIn("tiktok-srt-reporter", source)
        self.assertIn("/etc/tiktok-srt-reporter.env", source)
        self.assertIn("systemctl", source)
        self.assertIn("REPORT_TOKEN", source)
        self.assertIn("连接中控台 reporter", source)
        self.assertNotIn("monitor-start.sh", source)
        self.assertNotIn("python3.*monitor.py", source)
        self.assertNotIn("Web 监控", source)

    def test_setup_no_longer_starts_old_monitor(self):
        source = (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")

        self.assertNotIn("monitor-start.sh", source)
        self.assertNotIn("ufw allow 9988/tcp", source)
        self.assertIn("/usr/local/bin/tkm", source)

    def test_update_scripts_preserves_local_changes(self):
        source = (ROOT / "scripts" / "manage.py").read_text(encoding="utf-8")

        self.assertNotIn('"checkout", "--"', source)
        self.assertNotIn("git checkout", source)
        self.assertIn('"stash", "push"', source)
        self.assertIn('"--ff-only"', source)

    def test_normalize_reporter_hub_input(self):
        self.assertEqual(
            self.manage.normalize_reporter_hub("23.238.118.221"),
            "http://23.238.118.221:9988/api/report",
        )
        self.assertEqual(
            self.manage.normalize_reporter_hub("live.example.com"),
            "https://live.example.com/api/report",
        )
        self.assertEqual(
            self.manage.normalize_reporter_hub("https://live.example.com"),
            "https://live.example.com/api/report",
        )
        self.assertEqual(
            self.manage.normalize_reporter_hub("http://23.238.118.221:9988/api/report"),
            "http://23.238.118.221:9988/api/report",
        )

    def test_render_config_preserves_extra_streams(self):
        parsed = self.manage.parse_yml()
        ok, result = self.manage.add_stream("zs1", parsed, self.manage.load_env())
        self.assertTrue(ok, result)

        template = (self.base / "mediamtx.yml.template").read_text(encoding="utf-8")
        env = self.manage.load_env()
        for src, dst in {
            "__STREAM_PATH__": env["STREAM_PATH"],
            "__SRT_PORT__": env["SRT_PORT"],
            "__SRT_PUBLISH_PASSPHRASE__": env["SRT_PUBLISH_PASSPHRASE"],
            "__SRT_READ_PASSPHRASE__": env["SRT_READ_PASSPHRASE"],
            "__MUSIC_PATH__": env["MUSIC_PATH"],
            "__MUSIC_PUBLISH_PASSPHRASE__": env["MUSIC_PUBLISH_PASSPHRASE"],
            "__MUSIC_READ_PASSPHRASE__": env["MUSIC_READ_PASSPHRASE"],
        }.items():
            template = template.replace(src, dst)

        # Match render-config behavior: a rendered template should be merged
        # with extra tkm-managed paths from the existing mediamtx.yml.
        merged = self.manage.merge_extra_paths(
            template,
            (self.base / "mediamtx.yml").read_text(encoding="utf-8"),
            {env["STREAM_PATH"], env["MUSIC_PATH"]},
        )

        self.assertIn("  zs1:", merged)
        self.assertIn("path: zs1", merged)


if __name__ == "__main__":
    unittest.main()
