"""Reads the prompts from the skill/ folder so the app and the installable skill share ONE source of truth.

Edit an agent's role, an advisor's focus or the plan sections in `skill/references/`, not in Python.
No third-party imports here, so this file can be tested on its own.
"""
import importlib.util
import os
from pathlib import Path


def _find_skill_dir() -> Path:
    env = os.getenv("AI_DEV_OFFICE_SKILL_DIR")
    candidates = [Path(env)] if env else []
    here = Path(__file__).resolve()
    candidates += [here.parents[2] / "skill", here.parents[1] / "skill"]  # repo/skill, or app/skill
    for path in candidates:
        if (path / "SKILL.md").exists():
            return path
    raise FileNotFoundError(
        "Could not find the skill/ folder (the one containing SKILL.md). Run the app from a full clone of the "
        "repository, or set AI_DEV_OFFICE_SKILL_DIR to its location."
    )


SKILL_DIR = _find_skill_dir()


def _load_module(name: str):
    path = SKILL_DIR / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_skill_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_script(name: str):
    """Import one of skill/scripts/<name>.py (e.g. 'contrast', 'sql_check')."""
    return _load_module(name)


_fmt = _load_module("skillfmt")


def read_reference(relative: str) -> str:
    return _fmt.read_text(SKILL_DIR / "references" / relative)


def _read_doc(relative: str):
    meta, body = _fmt.parse_frontmatter(read_reference(relative))
    return meta, _fmt.split_sections(body)


def load_roles() -> dict:
    """{'researcher': {role, goal, backstory, tools: [names]}, ...}"""
    roles = {}
    for path in sorted((SKILL_DIR / "references" / "roles").glob("*.md")):
        meta, sections = _read_doc(f"roles/{path.name}")
        roles[meta["id"]] = {
            "role": meta["role"],
            "goal": meta["goal"],
            "backstory": sections["Backstory"],
            "tools": _fmt.csv(meta.get("tools", "")),
        }
    return roles


def load_advisors() -> dict:
    """{'ux': {label, section, role, goal, backstory, focus, tools: [names], when, keywords: [..]}, ...} in `order`."""
    found = []
    for path in (SKILL_DIR / "references" / "advisors").glob("*.md"):
        meta, sections = _read_doc(f"advisors/{path.name}")
        found.append((int(meta.get("order", 99)), meta["id"], {
            "label": meta["label"],
            "section": meta["section"],
            "role": meta["role"],
            "goal": meta["goal"],
            "backstory": sections["Backstory"],
            "focus": sections["Focus"],
            "tools": _fmt.csv(meta.get("tools", "")),
            "when": meta.get("when", ""),
            "keywords": _fmt.csv(meta.get("keywords", "")),
        }))
    return {key: spec for _, key, spec in sorted(found, key=lambda item: (item[0], item[1]))}


def plan_sections() -> list:
    """The required plan sections, in order, from references/plan-template.md."""
    import re

    _, sections = _read_doc("plan-template.md")
    items = re.findall(r"^\d+\.\s+(.+?)\s*$", sections.get("Required sections", ""), re.M)
    if not items:
        raise ValueError("plan-template.md has no numbered list under '## Required sections'")
    return items
