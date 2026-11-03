"""Tests for skill/scripts/ctx.py (project memory)."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "scripts"))
import ctx  # noqa: E402


def run(root, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ctx.main(["--root", str(root), *args])
    return code, buf.getvalue()


PLAN = """# Plan
## 5. Implementation Steps
1. **Set up** the project
2. Booking form `with` validation
   - nested detail is ignored
3. Admin list
## 6. Risks
1. not a slice
"""


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def status(self):
        return (self.root / ".ai-dev-office" / "STATUS.md").read_text(encoding="utf-8")


class PlanParsing(unittest.TestCase):
    def test_top_level_items_under_implementation_heading_only(self):
        self.assertEqual(ctx.plan_slices(PLAN), ["Set up the project", "Booking form with validation", "Admin list"])

    def test_bullets_and_other_heading_names(self):
        self.assertEqual(ctx.plan_slices("## Roadmap\n- one\n- two\n"), ["one", "two"])

    def test_no_heading_means_no_slices(self):
        self.assertEqual(ctx.plan_slices("# Plan\n1. a\n2. b\n"), [])

    def test_capped(self):
        text = "## Implementation\n" + "\n".join(f"{i}. step {i}" for i in range(1, 60))
        self.assertEqual(len(ctx.plan_slices(text)), ctx.MAX_SLICES)


class Init(Base):
    def test_init_creates_files_and_never_overwrites(self):
        code, out = run(self.root, "init")
        self.assertEqual(code, 0)
        proj = self.root / ".ai-dev-office" / "PROJECT.md"
        proj.write_text("# mine\n", encoding="utf-8")
        _, out = run(self.root, "init")
        self.assertIn("kept", out)
        self.assertEqual(proj.read_text(encoding="utf-8"), "# mine\n")

    def test_init_from_plan(self):
        (self.root / "PLAN.md").write_text(PLAN, encoding="utf-8")
        _, out = run(self.root, "init", "--from-plan", "PLAN.md")
        self.assertIn("added  3 slices", out)
        self.assertIn("| 2 | Booking form with validation |", self.status())
        self.assertIn("Phase: design", self.status())
        _, out = run(self.root, "init", "--from-plan", "PLAN.md")
        self.assertIn("already has slices", out)

    def test_missing_plan_is_reported(self):
        code, out = run(self.root, "init", "--from-plan", "nope.md")
        self.assertEqual(code, 1)
        self.assertIn("not found", out)

    def test_commands_without_init_give_a_hint(self):
        code, out = run(self.root, "status")
        self.assertEqual(code, 1)
        self.assertIn("ctx init", out)
        code, out = run(self.root, "resume")
        self.assertEqual(code, 0)
        self.assertIn("No .ai-dev-office/", out)


class StatusFlow(Base):
    def setUp(self):
        super().setUp()
        (self.root / "PLAN.md").write_text(PLAN, encoding="utf-8")
        run(self.root, "init", "--from-plan", "PLAN.md")
        for n in (1, 2, 3):
            run(self.root, "set", str(n), "todo", "--acceptance", f"Slice {n} works for a user")

    def test_building_and_verified_require_an_acceptance_sentence(self):
        run(self.root, "add", "Emails")
        code, out = run(self.root, "set", "4", "building")
        self.assertEqual(code, 1)
        self.assertIn("no acceptance sentence", out)
        code, _ = run(self.root, "set", "4", "verified", "--evidence", "ok")
        self.assertEqual(code, 1)
        self.assertEqual(run(self.root, "set", "4", "building", "--acceptance", "A guest gets an email")[0], 0)

    def test_verified_requires_evidence(self):
        code, out = run(self.root, "set", "1", "verified")
        self.assertEqual(code, 1)
        self.assertIn("evidence", out)
        code, out = run(self.root, "set", "1", "verified", "--evidence", "pytest: 3 passed | clean")
        self.assertEqual(code, 0)
        self.assertIn("1/3 verified", out)
        self.assertIn("pytest: 3 passed / clean", self.status())  # pipe is sanitized so the table stays intact

    def test_unknown_state_and_slice(self):
        self.assertEqual(run(self.root, "set", "1", "done")[0], 2)
        self.assertEqual(run(self.root, "set", "9", "todo")[0], 1)

    def test_second_building_warns(self):
        run(self.root, "set", "1", "building")
        _, out = run(self.root, "set", "2", "building")
        self.assertIn("already 'building'", out)

    def test_resume_header_follows_progress(self):
        run(self.root, "set", "1", "verified", "--evidence", "ok")
        _, out = run(self.root, "status")
        self.assertIn("Next: #2", out)
        self.assertIn("Resume: Continue with #2", out)
        for n in ("2", "3"):
            run(self.root, "set", n, "verified", "--evidence", "ok")
        _, out = run(self.root, "status")
        self.assertIn("3/3 verified", out)
        self.assertIn("ship mode", out)

    def test_add_slice(self):
        _, out = run(self.root, "add", "Emails", "--acceptance", "A guest gets a confirmation")
        self.assertIn("added #4", out)
        self.assertIn("A guest gets a confirmation", self.status())

    def test_resume_is_short_and_has_commands(self):
        _, out = run(self.root, "resume")
        self.assertIn("Commands:", out)
        self.assertIn("TODO", out)
        self.assertLess(ctx.approx_tokens(out), 300)

    def test_check_catches_hand_edited_problems(self):
        path = self.root / ".ai-dev-office" / "STATUS.md"
        text = path.read_text(encoding="utf-8").replace("| 1 | Set up the project | Slice 1 works for a user | todo |  |", "| 1 | Set up the project | Slice 1 works for a user | verified |  |")
        path.write_text(text, encoding="utf-8")
        self.assertIn("verified |  |", path.read_text(encoding="utf-8"), "the hand edit must actually apply")
        code, out = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("no evidence", out)

    def test_check_flags_oversize_files(self):
        proj = self.root / ".ai-dev-office" / "PROJECT.md"
        proj.write_text(proj.read_text(encoding="utf-8") + "x" * 7000, encoding="utf-8")
        _, out = run(self.root, "check")
        self.assertIn("PROJECT.md is", out)


class Phases(Base):
    PLAN_OK = "# Plan\n## 2. Requirements & Acceptance Criteria\nR1. A guest can book.\n## 6. Implementation Steps\n1. Booking (R1)\n2. Admin list\n"

    def setUp(self):
        super().setUp()
        (self.root / "PLAN.md").write_text(self.PLAN_OK, encoding="utf-8")
        run(self.root, "init", "--from-plan", "PLAN.md")

    def phase(self):
        return ctx.get_header(ctx.parse_status(self.status_text())[0], "Phase")

    def status_text(self):
        return (self.root / ".ai-dev-office" / "STATUS.md").read_text(encoding="utf-8")

    def ready_for_build(self):
        for n in (1, 2):
            run(self.root, "set", str(n), "todo", "--acceptance", f"Slice {n} works")
        run(self.root, "stack", "node")

    def test_init_from_plan_starts_in_design(self):
        self.assertEqual(self.phase(), "design")

    def test_build_gate_names_every_missing_thing(self):
        code, out = run(self.root, "phase", "build")
        self.assertEqual(code, 1)
        self.assertIn("without an acceptance sentence: #1, #2", out)
        self.assertIn("Stack is empty or TODO", out)
        self.assertIn("Commands are empty or TODO", out)
        self.assertEqual(self.phase(), "design")

    def test_build_gate_passes_when_ready_and_walks_the_lifecycle(self):
        self.ready_for_build()
        self.assertEqual(run(self.root, "phase", "build")[0], 0)
        code, out = run(self.root, "phase", "verify")
        self.assertEqual(code, 1)
        self.assertIn("slices not built yet", out)
        for n in (1, 2):
            run(self.root, "set", str(n), "verified", "--evidence", "tests pass")
        self.assertEqual(run(self.root, "phase", "verify")[0], 0)
        self.assertEqual(run(self.root, "phase", "release")[0], 0)
        self.assertEqual(run(self.root, "phase", "maintain")[0], 0)
        _, out = run(self.root, "phase")
        self.assertIn("final phase", out)

    def test_built_but_unverified_work_cannot_be_released(self):
        self.ready_for_build()
        run(self.root, "phase", "build")
        run(self.root, "set", "1", "verified", "--evidence", "ok")
        run(self.root, "set", "2", "built", "--evidence", "not verified: no browser available")
        self.assertEqual(run(self.root, "phase", "verify")[0], 0)
        code, out = run(self.root, "phase", "release")
        self.assertEqual(code, 1)
        self.assertIn("slices not verified: #2", out)

    def test_release_blocked_by_unverified_or_blocked_slices(self):
        self.ready_for_build()
        run(self.root, "phase", "build")
        run(self.root, "set", "1", "verified", "--evidence", "ok")
        run(self.root, "set", "2", "blocked")
        run(self.root, "phase", "verify")
        code, out = run(self.root, "phase", "release")
        self.assertEqual(code, 1)
        self.assertIn("blocked slices", out)

    def test_cannot_skip_a_phase_without_force(self):
        self.ready_for_build()
        code, out = run(self.root, "phase", "release")
        self.assertEqual(code, 1)
        self.assertIn("skips ahead", out)

    def test_force_needs_a_reason_and_records_the_waiver(self):
        self.assertEqual(run(self.root, "phase", "build", "--force")[0], 2)
        code, out = run(self.root, "phase", "build", "--force", "--reason", "prototype for a demo")
        self.assertEqual(code, 0)
        self.assertIn("waived", out)
        text = self.status_text()
        self.assertIn("Gate waived", text)
        self.assertIn("prototype for a demo", text)
        self.assertNotIn("None yet", text)
        self.assertEqual(self.phase(), "build")

    def test_going_back_is_always_allowed(self):
        run(self.root, "phase", "build", "--force", "--reason", "x")
        self.assertEqual(run(self.root, "phase", "requirements")[0], 0)

    def test_plan_without_requirements_blocks_design(self):
        (self.root / "PLAN.md").write_text("# Plan\n## Implementation Steps\n1. a\n", encoding="utf-8")
        run(self.root, "phase", "requirements", "--force", "--reason", "back")
        code, out = run(self.root, "phase", "design")
        self.assertEqual(code, 1)
        self.assertIn("no Requirements section", out)

    def test_unknown_phase(self):
        self.assertEqual(run(self.root, "phase", "launch")[0], 2)

    def test_status_without_phase_line_gets_one_next_to_the_other_headers(self):
        path = self.root / ".ai-dev-office" / "STATUS.md"
        path.write_text(path.read_text(encoding="utf-8").replace("Phase: design\n", ""), encoding="utf-8")
        run(self.root, "phase", "requirements")
        head = self.status_text().split("| # |")[0]
        self.assertRegex(head, r"Updated: .*\nResume: .*\nPhase: requirements\n")


class Stacks(Base):
    def setUp(self):
        super().setUp()
        run(self.root, "init")

    def project(self):
        return (self.root / ".ai-dev-office" / "PROJECT.md").read_text(encoding="utf-8")

    def test_detection(self):
        cases = {
            "laravel": {"artisan": "", "composer.json": '{"require": {"laravel/framework": "^12"}}', "package.json": "{}"},
            "django": {"manage.py": "import django"},
            "nextjs": {"package.json": '{"dependencies": {"next": "1"}}'},
            "node": {"package.json": '{"dependencies": {"express": "1"}}'},
            "static": {"index.html": "<html>"},
        }
        for expected, files in cases.items():
            with tempfile.TemporaryDirectory() as tmp:
                for name, text in files.items():
                    Path(tmp, name).write_text(text, encoding="utf-8")
                self.assertEqual(ctx.detect_stacks(Path(tmp))[0], expected, expected)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ctx.detect_stacks(Path(tmp)), [])

    def test_apply_fills_todo_placeholders_only(self):
        proj = self.root / ".ai-dev-office" / "PROJECT.md"
        proj.write_text(proj.read_text(encoding="utf-8").replace("- Test: TODO", "- Test: make check"), encoding="utf-8")
        code, out = run(self.root, "stack", "laravel")
        self.assertEqual(code, 0)
        text = self.project()
        self.assertIn("- Laravel (PHP)", text)
        self.assertIn("- Run: composer run dev", text)
        self.assertIn("- Test: make check", text, "a customized line must be kept")
        self.assertNotIn("TODO", text.split("## Conventions")[0])

    def test_apply_is_idempotent(self):
        run(self.root, "stack", "node")
        first = self.project()
        run(self.root, "stack", "node")
        self.assertEqual(self.project(), first)
        self.assertEqual(first.count("Node.js"), 1)

    def test_unknown_stack_lists_what_exists(self):
        code, out = run(self.root, "stack", "cobol")
        self.assertEqual(code, 1)
        for sid in ("laravel", "node", "nextjs", "django", "static"):
            self.assertIn(sid, out)

    def test_every_shipped_stack_applies_cleanly(self):
        for sid in ctx.available_stacks():
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run(root, "init")
                self.assertEqual(run(root, "stack", sid)[0], 0, sid)
                text = (root / ".ai-dev-office" / "PROJECT.md").read_text(encoding="utf-8")
                self.assertNotIn("TODO", text.split("## Conventions")[0], sid)

    def test_resume_points_at_the_stack_notes_once_detected(self):
        (self.root / "artisan").write_text("", encoding="utf-8")
        (self.root / "composer.json").write_text('{"require": {"laravel/framework": "^12"}}', encoding="utf-8")
        _, out = run(self.root, "resume")
        self.assertIn("references/stacks/laravel.md", out)


class RepoMap(Base):
    def setUp(self):
        super().setUp()
        run(self.root, "init")
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("def run(): pass\nclass Server: pass\ndef _hidden(): pass\n", encoding="utf-8")
        (self.root / "web").mkdir()
        (self.root / "web" / "main.js").write_text("export function render(){}\nexport const config = 1\n", encoding="utf-8")
        (self.root / "node_modules" / "x").mkdir(parents=True)
        (self.root / "node_modules" / "x" / "i.js").write_text("export function nope(){}", encoding="utf-8")

    def project(self):
        return (self.root / ".ai-dev-office" / "PROJECT.md").read_text(encoding="utf-8")

    def test_map_lists_symbols_and_skips_noise(self):
        code, out = run(self.root, "map")
        self.assertEqual(code, 0)
        text = self.project()
        self.assertIn("app.py — run, Server", text)
        self.assertIn("main.js — render, config", text)
        self.assertNotIn("_hidden", text)
        self.assertNotIn("node_modules", text)

    def test_map_is_idempotent_and_keeps_other_sections(self):
        proj = self.root / ".ai-dev-office" / "PROJECT.md"
        proj.write_text(proj.read_text(encoding="utf-8").replace("- Run: TODO", "- Run: make run"), encoding="utf-8")
        run(self.root, "map")
        run(self.root, "map")
        text = self.project()
        self.assertEqual(text.count(ctx.MAP_START), 1)
        self.assertIn("- Run: make run", text)

    def test_map_appends_section_when_markers_missing(self):
        proj = self.root / ".ai-dev-office" / "PROJECT.md"
        proj.write_text("# Project\n", encoding="utf-8")
        run(self.root, "map")
        self.assertIn("## Structure map", self.project())

    def test_line_cap_with_many_files(self):
        big = self.root / "many"
        for d in range(30):
            (big / f"d{d}").mkdir(parents=True)
            for f in range(5):
                (big / f"d{d}" / f"f{f}.txt").write_text("x", encoding="utf-8")
        run(self.root, "map", "--max-lines", "40")
        block = self.project().split(ctx.MAP_START)[1].split(ctx.MAP_END)[0]
        self.assertLessEqual(len(block.splitlines()), 40 + 8)

    def test_stale_detection(self):
        run(self.root, "map")
        self.assertIsNone(ctx.stale_reason(self.root, self.project()))
        time.sleep(1.1)
        (self.root / "src" / "app.py").write_text("def other(): pass\n", encoding="utf-8")
        self.assertIn("changed since", ctx.stale_reason(self.root, self.project()))
        run(self.root, "map")
        (self.root / "src" / "extra.py").write_text("x = 1\n", encoding="utf-8")
        self.assertIn("file count changed", ctx.stale_reason(self.root, self.project()))

    def test_no_map_yet(self):
        self.assertIn("no repo map", ctx.stale_reason(self.root, "# Project\n"))

    def test_respects_gitignore_when_in_a_git_repo(self):
        try:
            subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git not available")
        (self.root / ".gitignore").write_text("private/\n", encoding="utf-8")
        (self.root / "private").mkdir()
        (self.root / "private" / "secret_notes.py").write_text("def hide(): pass\n", encoding="utf-8")
        run(self.root, "map")
        self.assertNotIn("secret_notes", self.project())
        self.assertIn("app.py", self.project())


if __name__ == "__main__":
    unittest.main()
