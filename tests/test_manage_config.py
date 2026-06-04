import importlib.util
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


if __name__ == "__main__":
    unittest.main()
