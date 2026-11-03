"""Tests for the installable skill: scripts, file format, doctor, PROMPT.md and the installer."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill"
sys.path.insert(0, str(SKILL / "scripts"))

import contrast  # noqa: E402
import skillfmt  # noqa: E402
import sql_check  # noqa: E402


def run(*args, stdin=None):
    return subprocess.run([sys.executable, *map(str, args)], input=stdin, capture_output=True, text=True, timeout=60)


class ContrastTests(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(contrast.ratio("#000000", "#ffffff"), 21.0, places=2)

    def test_short_hex_and_order_independent(self):
        self.assertAlmostEqual(contrast.ratio("#fff", "#000"), contrast.ratio("#000", "#fff"))

    def test_known_failing_grey(self):
        self.assertIn("AA normal text (>=4.5): FAIL", contrast.check("#777777", "#ffffff"))

    def test_bad_input_returns_message_not_exception(self):
        self.assertIn("not a valid hex color", contrast.check("nope", "#fff"))
        self.assertIn("not a valid hex color", contrast.check("#gggggg", "#fff"))

    def test_cli_exit_codes(self):
        self.assertEqual(run(SKILL / "scripts" / "contrast.py", "#000", "#fff").returncode, 0)
        self.assertEqual(run(SKILL / "scripts" / "contrast.py", "x", "#fff").returncode, 2)


class SqlCheckTests(unittest.TestCase):
    def test_valid_schema(self):
        out = sql_check.validate("CREATE TABLE a(id INTEGER PRIMARY KEY); CREATE TABLE b(a_id INTEGER REFERENCES a(id));")
        self.assertTrue(out.startswith("Valid SQL"))
        self.assertIn("a, b", out)

    def test_syntax_error(self):
        self.assertIn("SQL error", sql_check.validate("CREAT TABLE x("))

    def test_foreign_key_to_missing_table_is_caught(self):
        self.assertIn("does not exist", sql_check.validate("CREATE TABLE b(a_id INTEGER REFERENCES nope(id));"))

    def test_attach_rejected(self):
        self.assertIn("Rejected", sql_check.validate("ATTACH DATABASE 'x.db' AS x;"))

    def test_runaway_statement_is_stopped(self):
        out = sql_check.validate("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT count(*) FROM c;")
        self.assertIn("SQL error", out)

    def test_cli_reads_stdin(self):
        r = run(SKILL / "scripts" / "sql_check.py", stdin="CREATE TABLE t(id INTEGER);")
        self.assertEqual(r.returncode, 0)


class FormatTests(unittest.TestCase):
    def test_frontmatter_and_sections(self):
        meta, body = skillfmt.parse_frontmatter('---\nid: x\nlabel: "A: B"\n---\n## One\nhello\n```\n## not a heading\n```\n## Two\nbye')
        self.assertEqual(meta, {"id": "x", "label": "A: B"})
        sections = skillfmt.split_sections(body)
        self.assertEqual(list(sections), ["One", "Two"])
        self.assertIn("## not a heading", sections["One"])

    def test_csv(self):
        self.assertEqual(skillfmt.csv("a, b,,c "), ["a", "b", "c"])
        self.assertEqual(skillfmt.csv(""), [])


class RepoTests(unittest.TestCase):
    def test_doctor_passes(self):
        r = run(ROOT / "scripts" / "doctor.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_prompt_md_is_current(self):
        r = run(ROOT / "scripts" / "build_prompt.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_prompt_md_contains_every_advisor_and_ends_with_project_marker(self):
        text = (ROOT / "PROMPT.md").read_text(encoding="utf-8")
        for name in ("ux", "db", "sec", "devops", "qa"):
            self.assertIn(f"references/advisors/{name}.md", text)
        self.assertTrue(text.rstrip().endswith("MY PROJECT:"))

    def test_web_prompts_exist_for_every_stack_and_are_complete(self):
        stacks = sorted(p.stem for p in (SKILL / "references" / "stacks").glob("*.md"))
        self.assertGreaterEqual(len(stacks), 5)
        for sid in stacks + ["generic"]:
            path = ROOT / "prompts" / f"web-{sid}.md"
            self.assertTrue(path.exists(), sid)
            text = path.read_text(encoding="utf-8")
            for part in ("references/sdlc.md", "references/workflows/build.md", "references/workflows/ship.md",
                         "references/workflows/maintain.md", "references/web-quality.md", "references/advisors/sec.md"):
                self.assertIn(f"`{part}`", text, f"{sid}: {part}")
            self.assertIn("Problem (who has it", text)
            self.assertIn("never claim you ran", text.lower())
            if sid != "generic":
                self.assertIn(f"references/stacks/{sid}.md", text)
                others = [o for o in stacks if o != sid]
                self.assertFalse(any(f"references/stacks/{o}.md" in text for o in others), "only its own stack notes are included")
        self.assertTrue((ROOT / "PROMPT.md").read_text(encoding="utf-8").rstrip().endswith("MY PROJECT:"))

    def test_install_roundtrip_and_backup_outside_skills_folder(self):
        import os
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, AI_DEV_OFFICE_HOME=home)
            def go(*a):
                return subprocess.run([sys.executable, str(ROOT / "scripts" / "install.py"), *a], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(go("--dest", tmp).returncode, 0)
            self.assertFalse((Path(tmp) / "ai-dev-office").exists(), "preview must not install")
            self.assertEqual(go("--dest", tmp, "--apply").returncode, 0)
            installed = Path(tmp) / "ai-dev-office"
            self.assertTrue((installed / "SKILL.md").exists())
            self.assertEqual(run(ROOT / "scripts" / "doctor.py", "--path", installed).returncode, 0)
            self.assertEqual(go("--dest", tmp, "--apply").returncode, 0)
            self.assertEqual(len(list((Path(home) / "backups").glob("ai-dev-office-*"))), 1)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["ai-dev-office"], "no stray folders (a second SKILL.md would confuse assistants)")

    def test_install_with_unreviewed_profile_is_refused_but_own_skill_installs(self):
        import os
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, AI_DEV_OFFICE_HOME=home)
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "install.py"), "--dest", tmp, "--profile", "core", "--apply"],
                               capture_output=True, text=True, env=env, timeout=60)
            lock = __import__("json").loads((ROOT / "dependencies.lock.json").read_text(encoding="utf-8"))
            if any(not p.get("reviewed") for p in lock["packages"] if "core" in p["profiles"]):
                self.assertEqual(r.returncode, 2)
                self.assertIn("Refusing", r.stdout)
                self.assertEqual([p.name for p in Path(tmp).iterdir()], ["ai-dev-office"])

    def test_doctor_detects_a_broken_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            run(ROOT / "scripts" / "install.py", "--dest", tmp, "--apply")
            (Path(tmp) / "ai-dev-office" / "references" / "advisors" / "qa.md").unlink()
            self.assertEqual(run(ROOT / "scripts" / "doctor.py", "--path", Path(tmp) / "ai-dev-office").returncode, 1)


if __name__ == "__main__":
    unittest.main()
