#!/usr/bin/env python3
"""Build PROMPT.md (the single-paste, plan-only edition for chat-only AIs) from the files in skill/.

    python scripts/build_prompt.py           write PROMPT.md and prompts/web-*.md
    python scripts/build_prompt.py --check   exit 1 if any of them is out of date (used by doctor and CI)

PROMPT.md is the plan-only edition. prompts/web-<stack>.md are the full-lifecycle web development editions
(plan, build, ship, maintain), one per stack that has notes in skill/references/stacks/, plus web-generic.md.
Never edit these by hand: edit the files in skill/ and run this again.
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
Follow the plan-mode workflow below. Every file it refers to is included further down under its file name.
This edition only plans. Building, fixing and shipping need a coding assistant with file access (see the repository's INSTALL.md); if asked to build, say so and offer the plan instead.
You are in a plain chat, so you probably cannot run scripts or browse:
- Where the workflow mentions `scripts/contrast.py`, calculate the WCAG contrast ratio yourself and say it was not tool-checked.
- Where it mentions `scripts/sql_check.py`, say the SQL was not machine-checked.
- If you cannot search the web, label every time-sensitive fact (versions, prices, limits) as unverified.
The user's project idea is at the very end, after "MY PROJECT:".

---

"""


def build() -> str:
    workflow = read_text(SKILL / "references" / "workflows" / "plan.md")
    parts = [PREFACE, workflow.strip(), "\n\n---\n\n# Included files\n"]

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


WEB_PREFACE = """\
# AI Dev Office: web development edition ({label})

You are "AI Dev Office": you take a website or web app from idea to a launched, maintained product by following a lifecycle with checks (requirements, design, build, verify, release, maintain). Everything you need is below; every file it refers to is included further down under its file name.

How to work in this chat:
- You cannot run commands or save files here. So: (1) wherever the instructions mention `ctx`, keep a short STATUS table in your replies instead (columns: #, slice, acceptance, state, evidence) and show only the rows that changed; (2) give code as complete files with their paths, one slice at a time, never the whole project in one reply; (3) tell me the exact commands to run and ask me to paste the output: a slice is "verified" only when I paste passing output or tell you what I saw, otherwise mark it "built, not verified"; (4) never claim you ran, tested or deployed anything.
- Ignore the parts about installing skills, helper skills, subagents and scripts. Use `references/fallbacks.md`. If a script such as `scripts/contrast.py` is mentioned, calculate by hand and say it was not tool-checked.
- Start in plan mode: ask me at most three short questions, then write the plan. After the plan, stop and wait for me to say "go" before building. Then continue with build, ship and maintain as I ask.
- Stack: {stack_line}
- If you cannot search the web, label every time-sensitive fact (versions, prices, limits) as unverified.

---

"""

FORM = """
---

MY PROJECT (fill in what you can; leave a line blank if unsure)

Problem (who has it, what is hard today):
Users and roles:
Must-have features:
Stack: {stack}
Constraints (budget, hosting, deadline, existing code):
My experience level (beginner / intermediate / advanced):
"""


def stack_files() -> dict:
    out = {}
    for path in sorted((SKILL / "references" / "stacks").glob("*.md")):
        meta, body = parse_frontmatter(read_text(path))
        out[meta.get("id", path.stem)] = (meta.get("name", path.stem), path, body)
    return out


def build_web(stack_id=None) -> str:
    stacks = stack_files()
    if stack_id:
        name, _, _ = stacks[stack_id]
        label, stack_line, stack_form = name, f"{name}. Its notes are included below. Use this stack; do not swap it.", name
    else:
        label = "any stack"
        stack_line = ("not fixed yet. Use the one I name below, or recommend one after asking me. For a stack without notes here, "
                      "read its official quickstart and tell me what you could not verify.")
        stack_form = "(name it, e.g. Laravel + MySQL, or write: you recommend)"
    parts = [WEB_PREFACE.format(label=label, stack_line=stack_line), read_text(SKILL / "references" / "workflows" / "plan.md").strip(),
             "\n\n---\n\n# Included files\n"]

    def add(rel: str, body: str):
        parts.append(f"\n## File: `{rel}`\n\n{body.strip()}\n")

    for rel in ("references/sdlc.md", "references/workflows/build.md", "references/workflows/ship.md",
                "references/workflows/maintain.md", "references/web-quality.md", "references/fallbacks.md"):
        add(rel, read_text(SKILL / rel))
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
        add(f"references/advisors/{path.name}",
            f"Role: {meta.get('role', '')}\nGoal: {meta.get('goal', '')}\nReport section name: {meta.get('section', '')}\n\n" + body)
    _, sec = parse_frontmatter(read_text(SKILL / "references" / "security-checklist.md"))
    add("references/security-checklist.md", sec)
    if stack_id:
        _, path, body = stacks[stack_id]
        add(f"references/stacks/{path.name}", body)
    parts.append(FORM.format(stack=stack_form))
    return "".join(parts).replace("\r\n", "\n")


def targets() -> dict:
    out = {ROOT / "PROMPT.md": build(), ROOT / "prompts" / "web-generic.md": build_web()}
    for sid in stack_files():
        out[ROOT / "prompts" / f"web-{sid}.md"] = build_web(sid)
    return out


def main(argv) -> int:
    built = targets()
    if "--check" in argv:
        stale = []
        for path, text in built.items():
            current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else ""
            if current != text:
                stale.append(path.relative_to(ROOT).as_posix())
        known = {p for p in built}
        extra = [p.relative_to(ROOT).as_posix() for p in (ROOT / "prompts").glob("web-*.md") if p not in known] if (ROOT / "prompts").exists() else []
        if stale or extra:
            print("Out of date: " + ", ".join(stale + [f"{e} (no matching stack file)" for e in extra]) + ". Run: python scripts/build_prompt.py")
            return 1
        print(f"{len(built)} prompt files are up to date.")
        return 0
    (ROOT / "prompts").mkdir(exist_ok=True)
    for path, text in built.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {path.relative_to(ROOT).as_posix()} ({len(text.encode('utf-8')) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
