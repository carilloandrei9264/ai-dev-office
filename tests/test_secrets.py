"""Tests for skill/scripts/secrets_scan.py. Token-shaped test strings are assembled at runtime so this file
itself never contains something a scanner would flag."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "scripts"))
import secrets_scan as ss  # noqa: E402

AWS = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
GH = "gh" + "p_" + "a" * 36
PEM = "-----BEGIN " + "RSA PRIVATE KEY-----"


def scan(root):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ss.main(["--root", str(root)])
    return code, buf.getvalue()


class Scan(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text):
        (self.root / name).write_text(text, encoding="utf-8")

    def test_finds_known_formats_and_masks_them(self):
        self.write("a.py", f'x = "{AWS}"\ny = "{GH}"\n{PEM}\n')
        code, out = scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("AWS access key id", out)
        self.assertIn("GitHub token", out)
        self.assertIn("Private key block", out)
        self.assertNotIn(AWS, out)
        self.assertNotIn(GH, out)

    def test_hardcoded_credential_but_not_env_lookups_or_placeholders(self):
        self.write("a.py", 'password = "hunter2hunter2"\nok = os.environ["API_KEY"]\napi_key = "your_api_key_here"\nsecret = "<put secret here>"\n')
        _, out = scan(self.root)
        self.assertIn("a.py:1: Hard-coded credential", out)
        self.assertEqual(out.count("Hard-coded credential"), 1)

    def test_ignore_marker(self):
        self.write("a.py", f'x = "{AWS}"  # secretscan:ignore\n')
        self.assertEqual(scan(self.root)[0], 0)

    def test_env_file_secret_and_gitignore_warning(self):
        self.write(".env", "STRIPE_SECRET=abcd1234efgh5678\nDEBUG=true\n")
        code, out = scan(self.root)
        self.assertEqual(code, 1)
        self.assertIn("Secret in env file", out)
        self.assertIn(".gitignore does not ignore", out)

    def test_env_example_is_fine_and_ignored_env_is_not_warned(self):
        self.write(".env.example", "STRIPE_SECRET=abcd1234efgh5678\n")
        self.write(".gitignore", ".env\n")
        self.write("README.md", "hello\n")
        self.assertEqual(scan(self.root)[0], 0)

    def test_skips_binary_and_vendor_dirs(self):
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "x.js").write_text(f'k = "{AWS}"', encoding="utf-8")
        (self.root / "img.bin").write_bytes(b"\0\0" + AWS.encode())
        self.assertEqual(scan(self.root)[0], 0)


if __name__ == "__main__":
    unittest.main()
