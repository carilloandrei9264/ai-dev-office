#!/usr/bin/env python3
"""Install, check and review the third-party skills pinned in dependencies.lock.json.

  skills.py list [--profile P]
  skills.py sync   --profile P [--host claude|codex] [--scope user|project] [--dest DIR] [--apply] [--allow-unreviewed]
  skills.py status --profile P [--host ...] [--dest DIR]
  skills.py review  PACKAGE            download the pinned commit and print what a human should read before approving
  skills.py approve PACKAGE --by NAME  mark a package as reviewed (edits the lock file)
  skills.py bump    PACKAGE [--ref SHA]  move a pin to a new commit (default: upstream HEAD); resets it to unreviewed
  skills.py check-updates              compare each pin with the upstream default branch (needs network)

Profiles: core, web, backend, postgres, lean, or all (comma-separate to combine).

Safety model
  * Every package is pinned to a full commit SHA; the downloaded checkout must match it exactly.
  * Nothing downloaded is ever executed. Files are copied; symlinks and .git are skipped; size is capped.
  * Packages marked reviewed=false are refused unless you pass --allow-unreviewed.
  * A skill you edited, or one installed by other means, is never overwritten. Replaced copies are backed up
    outside the skills folder (~/.ai-dev-office/backups, or $AI_DEV_OFFICE_HOME/backups).
  * Without --apply, sync only previews (and works offline).
Environment: AIDO_GIT_BASE overrides the git host (default https://github.com/), used by the tests.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "dependencies.lock.json"
MARKER = ".aido-managed.json"
KNOWN_PROFILES = ("core", "web", "backend", "postgres", "lean")
MAX_FILES, MAX_BYTES = 2000, 30 * 1024 * 1024
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SCRIPT_EXT = {".sh", ".bash", ".ps1", ".cmd", ".bat", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl"}
SUSPICIOUS = [re.compile(p, re.I) for p in (
    r"curl\s", r"wget\s", r"Invoke-WebRequest", r"\beval\s*\(", r"\bexec\s*\(", r"base64", r"rm\s+-rf", r"child_process",
    r"subprocess", r"os\.system", r"\|\s*(?:ba)?sh\b", r"chmod\s+\+x", r"\.ssh\b", r"id_rsa", r"\.aws\b", r"keychain",
    r"document\.cookie", r"localStorage", r"https?://(?!github\.com|raw\.githubusercontent\.com|docs\.)[^\s)\"']+")]


# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------
def load_lock(path=None) -> dict:
    with open(path or DEFAULT_LOCK, encoding="utf-8") as f:
        return json.load(f)


def save_lock(lock: dict, path=None):
    with open(path or DEFAULT_LOCK, "w", encoding="utf-8", newline="\n") as f:
        json.dump(lock, f, indent=2, ensure_ascii=False)
        f.write("\n")


def lock_problems(lock: dict) -> list:
    """Structural problems in the lock (used by doctor and tests)."""
    problems, seen_ids, seen_names = [], set(), {}
    for pkg in lock.get("packages", []):
        pid = pkg.get("id", "?")
        if pid in seen_ids:
            problems.append(f"duplicate package id {pid}")
        seen_ids.add(pid)
        if not REPO_RE.match(pkg.get("repo", "")):
            problems.append(f"{pid}: repo must look like owner/name")
        if not SHA_RE.match(pkg.get("ref", "")):
            problems.append(f"{pid}: ref must be a full 40-character commit SHA")
        if not pkg.get("license") or not pkg.get("license_files"):
            problems.append(f"{pid}: license and license_files are required")
        bad = [p for p in pkg.get("profiles", []) if p not in KNOWN_PROFILES]
        if bad or not pkg.get("profiles"):
            problems.append(f"{pid}: profiles must be a non-empty subset of {KNOWN_PROFILES} (got {pkg.get('profiles')})")
        if not pkg.get("skills"):
            problems.append(f"{pid}: no skills listed")
        for s in pkg.get("skills", []):
            name, path = s.get("name", ""), s.get("path", "")
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
                problems.append(f"{pid}: bad skill name '{name}'")
            if path.startswith("/") or ".." in Path(path).parts:
                problems.append(f"{pid}/{name}: path must be relative and stay inside the repository")
            if name in seen_names:
                problems.append(f"skill name '{name}' appears in both {seen_names[name]} and {pid}")
            seen_names[name] = pid
    return problems


def select(lock: dict, profiles) -> list:
    wanted = {p.strip() for p in (profiles if isinstance(profiles, (list, tuple)) else str(profiles).split(",")) if p.strip()}
    unknown = wanted - set(KNOWN_PROFILES) - {"all"}
    if unknown:
        raise ValueError(f"Unknown profile(s): {', '.join(sorted(unknown))}. Choose from: {', '.join(KNOWN_PROFILES)}, all")
    return [p for p in lock["packages"] if "all" in wanted or wanted & set(p["profiles"])]


def find_pkg(lock: dict, pid: str) -> dict:
    for p in lock["packages"]:
        if p["id"] == pid:
            return p
    raise ValueError(f"No package '{pid}'. Known: {', '.join(p['id'] for p in lock['packages'])}")


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------
def default_dest(host: str, scope: str) -> Path:
    base = Path.home() if scope == "user" else Path.cwd()
    return base / {"claude": ".claude/skills", "codex": ".codex/skills"}[host]


def backup_root() -> Path:
    return Path(os.getenv("AI_DEV_OFFICE_HOME") or Path.home() / ".ai-dev-office") / "backups"


# ---------------------------------------------------------------------------
# Git (download only; nothing from the repository is ever executed)
# ---------------------------------------------------------------------------
def git_url(repo: str) -> str:
    return f"{os.getenv('AIDO_GIT_BASE', 'https://github.com/')}{repo}.git"


def git(args, cwd=None, timeout=180):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    for key in list(env):
        if key == "GIT_CONFIG" or key.startswith("GIT_CONFIG_"):
            env.pop(key)
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM="1")
    try:
        r = subprocess.run(["git", "-c", "core.symlinks=false", "-c", "core.hooksPath=" + os.devnull, *args],
                           cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git timed out")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else "git failed")
    return r.stdout.strip()


def fetch(pkg: dict, workdir: Path) -> Path:
    """Download exactly pkg['ref'] into workdir and verify it. Returns the checkout path."""
    workdir.mkdir(parents=True, exist_ok=True)
    git(["init", "-q"], cwd=workdir)
    git(["remote", "add", "origin", git_url(pkg["repo"])], cwd=workdir)
    try:
        git(["fetch", "-q", "--depth", "1", "origin", pkg["ref"]], cwd=workdir)
    except RuntimeError:
        git(["fetch", "-q", "origin"], cwd=workdir, timeout=600)  # host does not allow fetching a bare SHA
    git(["-c", "advice.detachedHead=false", "checkout", "-q", "--detach", pkg["ref"]], cwd=workdir)
    head = git(["rev-parse", "HEAD"], cwd=workdir)
    if head != pkg["ref"]:
        raise RuntimeError(f"checked out {head}, expected {pkg['ref']}")
    return workdir


# ---------------------------------------------------------------------------
# Copying and hashing
# ---------------------------------------------------------------------------
def tree_hash(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in path.rglob("*") if x.is_file() and x.name != MARKER and not x.is_symlink()):
        h.update(p.relative_to(path).as_posix().encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def copy_skill(src: Path, dst: Path, exclude=()) -> dict:
    """Copy a skill folder without symlinks or .git, within size limits. Returns stats."""
    files = size = skipped = 0
    excl = [e.strip("/") for e in exclude]
    for dirpath, dirnames, filenames in os.walk(src):
        rel_dir = Path(dirpath).relative_to(src).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        keep = []
        for d in dirnames:
            rel = posixpath.join(rel_dir, d)
            if d == ".git" or os.path.islink(os.path.join(dirpath, d)) or any(rel == e or rel.startswith(e + "/") for e in excl):
                skipped += d != ".git"
                continue
            keep.append(d)
        dirnames[:] = keep
        for f in filenames:
            rel = posixpath.join(rel_dir, f)
            full = os.path.join(dirpath, f)
            if os.path.islink(full):
                skipped += 1
                continue
            if any(rel == e or rel.startswith(e + "/") for e in excl):
                continue
            files += 1
            size += os.path.getsize(full)
            if files > MAX_FILES or size > MAX_BYTES:
                raise ValueError(f"skill is too large (limit {MAX_FILES} files / {MAX_BYTES // (1024 * 1024)} MB)")
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(full, target)
    return {"files": files, "bytes": size, "symlinks_skipped": skipped}


def build_skill(checkout: Path, pkg: dict, skill: dict, stage: Path):
    """Create the finished skill folder in `stage` (does not touch the destination)."""
    src = (checkout / skill["path"]).resolve()
    if checkout.resolve() not in [src, *src.parents]:
        raise ValueError(f"{skill['name']}: path escapes the repository")
    if not (src / "SKILL.md").is_file():
        raise ValueError(f"{skill['name']}: no SKILL.md at {skill['path']}")
    copy_skill(src, stage, skill.get("exclude", ()))
    for rf in skill.get("required_files", ()):
        if not (stage / rf).exists():
            raise ValueError(f"{skill['name']}: required file {rf} is missing")
    base = posixpath.normpath(skill["path"])
    for lf in pkg["license_files"]:
        source = checkout / lf
        if not source.is_file():
            raise ValueError(f"license file {lf} not found in {pkg['repo']}@{pkg['ref'][:7]}; refusing to install without it")
        inside = lf[len(base) + 1:] if base != "." and lf.startswith(base + "/") else (lf if base == "." else None)
        if inside and (stage / inside).exists():
            continue
        shutil.copyfile(source, stage / f"UPSTREAM-{Path(lf).name}")
    marker = {"package": pkg["id"], "skill": skill["name"], "repo": pkg["repo"], "ref": pkg["ref"],
              "installed": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tree_sha256": tree_hash(stage)}
    (stage / MARKER).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def classify(dest: Path, pkg: dict, skill: dict) -> str:
    """new | unchanged | update | modified | unmanaged"""
    target = dest / skill["name"]
    if not target.exists():
        return "new"
    mfile = target / MARKER
    if not mfile.is_file():
        return "unmanaged"
    try:
        marker = json.loads(mfile.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unmanaged"
    if marker.get("package") != pkg["id"]:
        return "unmanaged"
    if marker.get("tree_sha256") != tree_hash(target):
        return "modified"
    return "unchanged" if marker.get("ref") == pkg["ref"] else "update"


LABELS = {"new": "will install", "unchanged": "up to date", "update": "will update (old copy is backed up)",
          "modified": "SKIPPED: you changed it", "unmanaged": "SKIPPED: not installed by ai-dev-office"}


def swap_in(stage: Path, target: Path, stamp: str, had_old: bool):
    backup = None
    try:
        if had_old:
            backup = backup_root() / f"{target.name}-{stamp}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup))
        stage.rename(target)
    except Exception:
        if backup and backup.exists() and not target.exists():
            shutil.move(str(backup), str(target))
        raise
    return backup


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def sync(profiles, dest: Path, apply: bool, allow_unreviewed: bool = False, lock_path=None, out=print) -> int:
    lock = load_lock(lock_path)
    problems = lock_problems(lock)
    if problems:
        out("The lock file has problems:\n  " + "\n  ".join(problems))
        return 1
    packages = select(lock, profiles)
    unreviewed = [p["id"] for p in packages if not p.get("reviewed")]
    out(f"Destination: {dest}")
    out(f"Profiles:    {profiles if isinstance(profiles, str) else ','.join(profiles)}  ({len(packages)} packages, {sum(len(p['skills']) for p in packages)} skills)")
    plan = []
    for pkg in packages:
        for skill in pkg["skills"]:
            action = classify(dest, pkg, skill)
            plan.append((pkg, skill, action))
            out(f"  {pkg['id']}/{skill['name']}: {LABELS[action]}")
    if unreviewed:
        out(f"\nNOT REVIEWED: {', '.join(unreviewed)}")
        out("  Run `python scripts/skills.py review <package>`, read the output and the skill, then `approve <package> --by <name>`.")
        out("  (Pass --allow-unreviewed to install anyway, at your own risk.)")
    if not apply:
        out("\nPreview only. Add --apply to install.")
        return 0
    if unreviewed and not allow_unreviewed:
        out("\nRefusing to install unreviewed packages.")
        return 2
    todo = [(p, s, a) for p, s, a in plan if a in ("new", "update")]
    if not todo:
        out("\nNothing to install or update.")
        return 0
    dest.mkdir(parents=True, exist_ok=True)
    stamp = time_stamp()
    failed = 0
    by_pkg = {}
    for p, s, a in todo:
        by_pkg.setdefault(p["id"], (p, []))[1].append((s, a))
    out("")
    for pid, (pkg, items) in by_pkg.items():
        tmp = Path(tempfile.mkdtemp(prefix="aido-fetch-"))
        try:
            checkout = fetch(pkg, tmp)
        except RuntimeError as e:
            out(f"  FAILED {pid}: could not download {pkg['repo']}@{pkg['ref'][:7]}: {e}")
            failed += len(items)
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        for skill, action in items:
            stage = dest / f".aido-stage-{stamp}-{skill['name']}"
            try:
                build_skill(checkout, pkg, skill, stage)
                backup = swap_in(stage, dest / skill["name"], stamp, action == "update")
                out(f"  {'updated  ' if action == 'update' else 'installed'} {pid}/{skill['name']}" + (f"  (backup: {backup})" if backup else ""))
            except Exception as e:  # noqa: BLE001
                out(f"  FAILED {pid}/{skill['name']}: {e}")
                failed += 1
            finally:
                if stage.exists():
                    shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
    out("\n" + (f"{failed} failed. Nothing was left half-installed." if failed else "Done. Restart or refresh your assistant so it finds the skills."))
    out("Nothing downloaded was executed. Some skills (for example impeccable) ship scripts: read them before running.")
    return 1 if failed else 0


def time_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def cmd_status(args) -> int:
    lock = load_lock(args.lock)
    dest = resolve_dest(args)
    rows = []
    for pkg in select(lock, args.profile):
        for skill in pkg["skills"]:
            state = classify(dest, pkg, skill)
            rows.append((pkg["id"], skill["name"], {"new": "missing"}.get(state, state), "yes" if pkg.get("reviewed") else "NO"))
    print(f"Destination: {dest}\n{'package':28} {'skill':36} {'state':10} reviewed")
    for r in rows:
        print(f"{r[0]:28} {r[1]:36} {r[2]:10} {r[3]}")
    return 0


def cmd_list(args) -> int:
    lock = load_lock(args.lock)
    pkgs = select(lock, args.profile)
    print(f"{'package':34} {'profiles':14} {'skills':>6}  reviewed  license")
    for p in pkgs:
        print(f"{p['id']:34} {','.join(p['profiles']):14} {len(p['skills']):>6}  {'yes' if p.get('reviewed') else 'NO ':8}  {p['license'][:48]}")
    print(f"\n{len(pkgs)} packages, {sum(len(p['skills']) for p in pkgs)} skills. Profiles: {', '.join(KNOWN_PROFILES)}, all")
    return 0


def cmd_review(args) -> int:
    lock = load_lock(args.lock)
    pkg = find_pkg(lock, args.package)
    tmp = Path(tempfile.mkdtemp(prefix="aido-review-"))
    try:
        try:
            checkout = fetch(pkg, tmp)
        except RuntimeError as e:
            print(f"Could not download {pkg['repo']}@{pkg['ref'][:7]}: {e}")
            return 1
        print(f"Package {pkg['id']}  {pkg['repo']} @ {pkg['ref']}\nDeclared license: {pkg['license']}")
        for lf in pkg["license_files"]:
            p = checkout / lf
            print(f"  license file {lf}: " + (f"present ({p.stat().st_size} bytes)" if p.is_file() else "MISSING"))
        if pkg.get("note"):
            print(f"Note: {pkg['note']}")
        flagged, hits = [], []
        for skill in pkg["skills"]:
            src = checkout / skill["path"]
            skill_md = src / "SKILL.md"
            print(f"\nSkill {skill['name']}  ({skill['path']})")
            if not skill_md.is_file():
                print("  PROBLEM: no SKILL.md at that path")
                continue
            files = [p for p in src.rglob("*") if p.is_file() and ".git" not in p.relative_to(src).parts]
            print(f"  {len(files)} files, {sum(p.stat().st_size for p in files) / 1024:.0f} KB")
            head = skill_md.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"(?m)^name:\s*(.+)$", head)
            if m and m.group(1).strip().strip("\"'") != skill["name"]:
                print(f"  note: SKILL.md says name '{m.group(1).strip()}', installed as '{skill['name']}'")
            d = re.search(r"(?ms)^description:\s*(.+?)(?:\n\w+:|\n---)", head)
            if d:
                print("  description: " + re.sub(r"\s+", " ", d.group(1))[:240])
            for p in files:
                rel = p.relative_to(checkout).as_posix()
                executable = os.name != "nt" and (p.stat().st_mode & 0o111)
                if p.suffix.lower() in SCRIPT_EXT or executable:
                    flagged.append(rel)
                if p.stat().st_size <= 200_000:
                    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        for rx in SUSPICIOUS:
                            if rx.search(line):
                                hits.append(f"{rel}:{i}: {line.strip()[:110]}")
                                break
        print(f"\nScripts or executables included ({len(flagged)}): " + (", ".join(flagged[:30]) or "none") + (" ..." if len(flagged) > 30 else ""))
        print(f"Lines worth reading ({len(hits)}):")
        for h in hits[:40]:
            print("  " + h)
        if len(hits) > 40:
            print(f"  ... {len(hits) - 40} more")
        print("\nThis is a checklist for a human, not a verdict. Read each SKILL.md and every flagged file.")
        print(f"If you are satisfied: python scripts/skills.py approve {pkg['id']} --by \"your name\"")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_approve(args) -> int:
    lock = load_lock(args.lock)
    pkg = find_pkg(lock, args.package)
    pkg["reviewed"], pkg["reviewed_by"], pkg["reviewed_on"] = True, args.by, dt.date.today().isoformat()
    save_lock(lock, args.lock)
    print(f"{pkg['id']} marked reviewed by {args.by} for commit {pkg['ref'][:7]}. Commit the lock file.")
    return 0


def remote_head(repo: str) -> str:
    out = git(["ls-remote", git_url(repo), "HEAD"], timeout=60)
    sha = out.split()[0] if out else ""
    if not SHA_RE.match(sha):
        raise RuntimeError("could not read the remote HEAD")
    return sha


def cmd_bump(args) -> int:
    lock = load_lock(args.lock)
    pkg = find_pkg(lock, args.package)
    try:
        ref = args.ref or remote_head(pkg["repo"])
    except RuntimeError as e:
        print(f"Could not look up {pkg['repo']}: {e}")
        return 1
    if not SHA_RE.match(ref):
        print("--ref must be a full 40-character commit SHA")
        return 2
    pkg["ref"], pkg["reviewed"] = ref, False
    pkg.pop("reviewed_by", None)
    pkg.pop("reviewed_on", None)
    save_lock(lock, args.lock)
    print(f"{pkg['id']} now pinned to {ref[:7]} and marked UNREVIEWED. Run review, then approve.")
    return 0


def cmd_check_updates(args) -> int:
    lock = load_lock(args.lock)
    seen = {}
    for pkg in lock["packages"]:
        try:
            head = seen.get(pkg["repo"]) or remote_head(pkg["repo"])
            seen[pkg["repo"]] = head
            print(f"{pkg['id']:34} " + ("up to date" if head == pkg["ref"] else f"newer upstream ({head[:7]}; pinned {pkg['ref'][:7]})"))
        except RuntimeError as e:
            print(f"{pkg['id']:34} could not check: {e}")
    return 0


def resolve_dest(args) -> Path:
    return Path(args.dest).expanduser() if args.dest else default_dest(args.host, args.scope)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lock", default=None, help="lock file (default: dependencies.lock.json in the repository)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def where(p):
        p.add_argument("--host", choices=["claude", "codex"], default="claude")
        p.add_argument("--scope", choices=["user", "project"], default="user")
        p.add_argument("--dest")

    p = sub.add_parser("list"); p.add_argument("--profile", default="all")
    p = sub.add_parser("sync"); p.add_argument("--profile", default="core"); where(p)
    p.add_argument("--apply", action="store_true"); p.add_argument("--allow-unreviewed", action="store_true")
    p = sub.add_parser("status"); p.add_argument("--profile", default="all"); where(p)
    p = sub.add_parser("review"); p.add_argument("package")
    p = sub.add_parser("approve"); p.add_argument("package"); p.add_argument("--by", required=True)
    p = sub.add_parser("bump"); p.add_argument("package"); p.add_argument("--ref")
    sub.add_parser("check-updates")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "sync":
            return sync(args.profile, resolve_dest(args), args.apply, args.allow_unreviewed, args.lock)
        handlers = {"list": cmd_list, "status": cmd_status, "review": cmd_review, "approve": cmd_approve,
                    "bump": cmd_bump, "check-updates": cmd_check_updates}
        return handlers[args.cmd](args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
