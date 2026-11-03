#!/usr/bin/env python3
"""Build PROMPT.md (the single-paste edition for chat-only AIs) from the files in skill/.

    python scripts/build_prompt.py           write PROMPT.md
    python scripts/build_prompt.py --check   exit 1 if PROMPT.md is out of date (used by doctor and CI)

Never edit PROMPT.md by hand: edit the files in skill/ and run this again.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill"
sys.path.insert(0, str(SKILL / "scripts"))
from skillfmt import parse_frontmatter, read_text  # noqa: E402

PREFACE = """\
# AI Dev Office: single-message edition

You are about to act as "AI Dev Office": a small team that plans a software project before any code is written.
Follow the workflow below. Every file it refers to is included further down under its file name.
You are in a plain chat, so you probably cannot run scripts or browse:
- Where the workflow mentions `scripts/contrast.py`, calculate the WCAG contrast ratio yourself and say it was not tool-checked.
- Where it mentions `scripts/sql_check.py`, say the SQL was not machine-checked.
- If you cannot search the web, label every time-sensitive fact (versions, prices, limits) as unverified.
The user's project idea is at the very end, after "MY PROJECT:".

---

"""


def build() -> str:
    _, skill_body = parse_frontmatter(read_text(SKILL / "SKILL.md"))
    parts = [PREFACE, skill_body.strip(), "\n\n---\n\n# Included files\n"]

    def add(rel: str, body: str, title: str = ""):
        parts.append(f"\n## File: `{rel}`\n" + (f"*{title}*\n" if title else "") + "\n" + body.strip() + "\n")

    _, tmpl = parse_frontmatter(read_text(SKILL / "references" / "plan-template.md"))
    add("references/plan-template.md", tmpl)
    for path in sorted((SKILL / "references" / "roles").glob("*.md")):
        meta, body = parse_frontmatter(read_text(path))
        add(f"references/roles/{path.name}", f"Role: {meta.get('role', '')}\nGoal: {meta.get('goal', '')}\n\n" + body)
    advisors = []
    for path in (SKILL / "references" / "advisors").glob("*.md"):
        meta, body = parse_frontmatter(read_text(path))
        advisors.append((int(meta.get("order", 99)), path, meta, body))
    for _, path, meta, body in sorted(advisors, key=lambda a: (a[0], a[1].name)):
        add(
            f"references/advisors/{path.name}",
            f"Role: {meta.get('role', '')}\nGoal: {meta.get('goal', '')}\nReport section name: {meta.get('section', '')}\n\n" + body,
        )
    _, sec = parse_frontmatter(read_text(SKILL / "references" / "security-checklist.md"))
    add("references/security-checklist.md", sec)
    parts.append("\n---\n\nMY PROJECT:\n")
    return "".join(parts).replace("\r\n", "\n")


def main(argv) -> int:
    target = ROOT / "PROMPT.md"
    text = build()
    if "--check" in argv:
        current = target.read_text(encoding="utf-8").replace("\r\n", "\n") if target.exists() else ""
        if current != text:
            print("PROMPT.md is out of date. Run: python scripts/build_prompt.py")
            return 1
        print("PROMPT.md is up to date.")
        return 0
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {target} ({len(text.encode('utf-8')) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
