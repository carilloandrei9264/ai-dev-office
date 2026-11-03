#!/usr/bin/env python3
"""Check that the skill is well-formed and its scripts run.

    python scripts/doctor.py                    check this repository's skill/ folder
    python scripts/doctor.py --path <folder>    check an installed copy (e.g. ~/.claude/skills/ai-dev-office)

Exit code 1 if anything FAILs. WARN does not fail.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_TOOLS = {"web_search", "read_webpage", "check_color_contrast", "validate_sql_schema", "security_checklist"}
ADVISOR_FIELDS = ["id", "order", "label", "section", "role", "goal", "tools", "when", "keywords"]
ROLE_FIELDS = ["id", "role", "goal"]
SKILL_BODY_WARN_BYTES = 12_000

results = []  # (level, message)


def ok(msg): results.append(("PASS", msg))
def warn(msg): results.append(("WARN", msg))
def fail(msg): results.append(("FAIL", msg))


def run(skill: Path, repo_mode: bool):
    sys.path.insert(0, str(skill / "scripts"))
    try:
        from skillfmt import csv, parse_frontmatter, read_text, split_sections
    except ImportError:
        fail("scripts/skillfmt.py is missing or broken")
        return

    skill_md = skill / "SKILL.md"
    if not skill_md.exists():
        fail("SKILL.md not found")
        return
    meta, body = parse_frontmatter(read_text(skill_md))
    if not meta.get("name") or not meta.get("description"):
        fail("SKILL.md front matter needs `name` and `description`")
    else:
        ok(f"SKILL.md front matter: name={meta['name']}")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", meta["name"]):
            fail("skill name must be lowercase letters, digits and hyphens")
        if len(meta["description"]) > 1024:
            fail(f"description is {len(meta['description'])} chars (max 1024)")
        if not repo_mode and skill.name != meta["name"]:
            warn(f"folder name '{skill.name}' differs from skill name '{meta['name']}'")
    size = len(body.encode("utf-8"))
    (warn if size > SKILL_BODY_WARN_BYTES else ok)(f"SKILL.md body is {size / 1024:.1f} KB (keep it compact)")

    # every referenced path exists
    referenced = set(re.findall(r"`((?:references|scripts)/[\w./-]+)`", body))
    missing = sorted(r for r in referenced if not (skill / r).exists() and not re.search(r"[<>*]", r))
    # example arguments such as schema.sql are not paths under references/scripts, so only real prefixes are checked
    (fail if missing else ok)("files referenced in SKILL.md: " + (", ".join(missing) + " missing" if missing else f"{len(referenced)} found"))

    # roles
    for name in ["researcher", "writer", "router", "reviewer"]:
        path = skill / "references" / "roles" / f"{name}.md"
        if not path.exists():
            fail(f"roles/{name}.md missing")
            continue
        m, b = parse_frontmatter(read_text(path))
        bad = [f for f in ROLE_FIELDS if not m.get(f)]
        sections = split_sections(b)
        if bad or not sections.get("Backstory"):
            fail(f"roles/{name}.md: missing {', '.join(bad + ([] if sections.get('Backstory') else ['## Backstory']))}")
        else:
            bad_tools = [t for t in csv(m.get("tools", "")) if t not in KNOWN_TOOLS]
            (fail if bad_tools else ok)(f"roles/{name}.md" + (f": unknown tools {bad_tools}" if bad_tools else ""))

    # plan template
    tmpl = skill / "references" / "plan-template.md"
    if tmpl.exists():
        sec = split_sections(parse_frontmatter(read_text(tmpl))[1]).get("Required sections", "")
        n = len(re.findall(r"^\d+\.\s+\S", sec, re.M))
        (ok if n else fail)(f"plan-template.md: {n} required sections")
    else:
        fail("references/plan-template.md missing")

    # advisors
    ids = []
    for path in sorted((skill / "references" / "advisors").glob("*.md")):
        m, b = parse_frontmatter(read_text(path))
        bad = [f for f in ADVISOR_FIELDS if f not in m]
        sections = split_sections(b)
        needed = [s for s in ("Backstory", "Focus") if not sections.get(s)]
        if bad or needed:
            fail(f"advisors/{path.name}: missing {', '.join(bad + ['## ' + s for s in needed])}")
            continue
        if m["id"] != path.stem:
            fail(f"advisors/{path.name}: id '{m['id']}' must match the file name")
        bad_tools = [t for t in csv(m["tools"]) if t not in KNOWN_TOOLS]
        if bad_tools:
            fail(f"advisors/{path.name}: unknown tools {bad_tools}")
        if f"`{m['id']}`" not in body or f"references/advisors/{path.name}" not in body:
            fail(f"advisor '{m['id']}' is not listed in the SKILL.md routing table")
        else:
            ok(f"advisor {m['id']}")
        ids.append(m["id"])
    if not ids:
        fail("no advisors found")
    elif len(ids) != len(set(ids)):
        fail("duplicate advisor ids")

    (ok if (skill / "references" / "security-checklist.md").exists() else fail)("security-checklist.md present")

    # scripts really run
    def script(name, args, stdin=None, expect=""):
        p = skill / "scripts" / name
        if not p.exists():
            fail(f"scripts/{name} missing")
            return
        try:
            r = subprocess.run([sys.executable, str(p), *args], input=stdin, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            fail(f"scripts/{name} timed out")
            return
        (ok if expect in r.stdout else fail)(f"scripts/{name} runs" + ("" if expect in r.stdout else f" (unexpected output: {r.stdout.strip()[:80]})"))

    script("contrast.py", ["#000000", "#ffffff"], expect="21.00:1")
    script("sql_check.py", [], stdin="CREATE TABLE t(id INTEGER PRIMARY KEY);", expect="Valid SQL")

    if repo_mode:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_prompt.py"), "--check"], capture_output=True, text=True)
        (ok if r.returncode == 0 else fail)("PROMPT.md is up to date" if r.returncode == 0 else r.stdout.strip())


def main(argv) -> int:
    path = None
    if "--path" in argv:
        path = Path(argv[argv.index("--path") + 1]).expanduser().resolve()
    skill = path or ROOT / "skill"
    run(skill, repo_mode=path is None)
    for level, msg in results:
        print(f"[{level}] {msg}")
    fails = sum(1 for l, _ in results if l == "FAIL")
    warns = sum(1 for l, _ in results if l == "WARN")
    print(f"\n{len(results) - fails - warns} passed, {warns} warnings, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
