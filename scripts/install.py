#!/usr/bin/env python3
"""Install the skill into an AI coding assistant's skills folder.

    python scripts/install.py --host claude            preview only (changes nothing)
    python scripts/install.py --host claude --apply    install
    python scripts/install.py --dest <folder> --apply  any other assistant that reads skill folders

Options:  --host claude|codex   --scope user|project (project = current folder)   --dest <skills folder>
An existing copy is backed up first, and restored if the install fails. Nothing from the skill is executed.
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skill"
NAME = "ai-dev-office"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def default_dest(host: str, scope: str) -> Path:
    base = Path.home() if scope == "user" else Path.cwd()
    folder = {"claude": ".claude/skills", "codex": ".codex/skills"}[host]
    return base / folder


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", choices=["claude", "codex"], default="claude")
    ap.add_argument("--scope", choices=["user", "project"], default="user")
    ap.add_argument("--dest", help="skills folder to install into (overrides --host/--scope)")
    ap.add_argument("--apply", action="store_true", help="actually install (default is a preview)")
    args = ap.parse_args(argv[1:])

    if not (SOURCE / "SKILL.md").exists():
        print(f"Cannot find {SOURCE / 'SKILL.md'}. Run this from a full clone of the repository.")
        return 1
    dest_root = Path(args.dest).expanduser() if args.dest else default_dest(args.host, args.scope)
    target = dest_root / NAME
    files = sorted(p.relative_to(SOURCE) for p in SOURCE.rglob("*") if p.is_file() and "__pycache__" not in p.parts)

    print(f"Skill:       {NAME} ({len(files)} files)")
    print(f"Install to:  {target}")
    print("Existing:    " + ("yes, will be backed up first" if target.exists() else "no"))
    if not args.apply:
        print("\nPreview only. Add --apply to install.")
        return 0

    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    staging = dest_root / f".{NAME}.new-{stamp}"
    backup = dest_root / f"{NAME}.bak-{stamp}"
    try:
        shutil.copytree(SOURCE, staging, ignore=IGNORE)
        if target.exists():
            target.rename(backup)
        staging.rename(target)
    except Exception as e:  # noqa: BLE001
        print(f"Install failed: {e}")
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if backup.exists() and not target.exists():
            backup.rename(target)
            print("Previous version restored.")
        return 1
    print("\nInstalled." + (f" Previous copy kept at {backup}" if backup.exists() else ""))
    print(f"Check it:    python {Path('scripts/doctor.py')} --path \"{target}\"")
    print("Restart or refresh your assistant so it picks the skill up.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
