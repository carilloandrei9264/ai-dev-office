#!/usr/bin/env python3
"""Install the ai-dev-office skill (and optionally the pinned helper skills) into an AI assistant's skills folder.

    python scripts/install.py --host claude                       preview only (changes nothing)
    python scripts/install.py --host claude --apply               install the skill
    python scripts/install.py --host claude --profile core --apply   ...and the helper skills in profile `core`
    python scripts/install.py --dest <folder> --apply             any assistant that reads skill folders

Options: --host claude|codex  --scope user|project (project = current folder)  --dest <skills folder>
         --profile core|web|backend|postgres|lean|all (comma-separate)  --allow-unreviewed
An existing copy is backed up to ~/.ai-dev-office/backups (outside the skills folder, so assistants never see
it) and restored if the install fails. Nothing from any skill is executed. See scripts/skills.py for helper skills.
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skills  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skill"
NAME = "ai-dev-office"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def install_own(dest_root: Path, apply: bool) -> int:
    target = dest_root / NAME
    files = sorted(p.relative_to(SOURCE) for p in SOURCE.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    print(f"Skill:       {NAME} ({len(files)} files)")
    print(f"Install to:  {target}")
    print("Existing:    " + ("yes, will be backed up outside the skills folder first" if target.exists() else "no"))
    if not apply:
        return 0
    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    staging = dest_root / f".{NAME}.new-{stamp}"
    backup = None
    try:
        shutil.copytree(SOURCE, staging, ignore=IGNORE)
        if target.exists():
            backup = skills.backup_root() / f"{NAME}-{stamp}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup))
        staging.rename(target)
    except Exception as e:  # noqa: BLE001
        print(f"Install failed: {e}")
        shutil.rmtree(staging, ignore_errors=True)
        if backup and backup.exists() and not target.exists():
            shutil.move(str(backup), str(target))
            print("Previous version restored.")
        return 1
    print("Installed." + (f" Previous copy kept at {backup}" if backup else ""))
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", choices=["claude", "codex"], default="claude")
    ap.add_argument("--scope", choices=["user", "project"], default="user")
    ap.add_argument("--dest", help="skills folder to install into (overrides --host/--scope)")
    ap.add_argument("--profile", help="also install the pinned helper skills of these profiles")
    ap.add_argument("--allow-unreviewed", action="store_true")
    ap.add_argument("--apply", action="store_true", help="actually install (default is a preview)")
    args = ap.parse_args(argv[1:])

    if not (SOURCE / "SKILL.md").exists():
        print(f"Cannot find {SOURCE / 'SKILL.md'}. Run this from a full clone of the repository.")
        return 1
    dest_root = Path(args.dest).expanduser() if args.dest else skills.default_dest(args.host, args.scope)
    code = install_own(dest_root, args.apply)
    if code:
        return code
    if args.profile:
        print()
        code = skills.sync(args.profile, dest_root, args.apply, args.allow_unreviewed)
        if code:
            return code
    if not args.apply:
        print("\nPreview only. Add --apply to install.")
        return 0
    print(f"\nCheck it:    python scripts/doctor.py --path \"{dest_root / NAME}\"")
    print("Restart or refresh your assistant so it picks the skill up.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
