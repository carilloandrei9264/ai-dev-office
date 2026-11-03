#!/usr/bin/env python3
"""Project memory for AI assistants: a small, cheap-to-read record of the project so each session starts fast.

Run from the project root. Files live in .ai-dev-office/ (PROJECT.md and STATUS.md).

  ctx.py init [--from-plan PLAN.md]      create the files (never overwrites); optionally seed slices from a plan
  ctx.py resume                          one short summary to read at session start
  ctx.py status                          slice counts and the next slice
  ctx.py set N STATE [--acceptance TEXT] [--evidence TEXT] [--resume TEXT]    STATE: todo|building|built|verified|blocked
                                         (building and verified need an acceptance sentence; verified needs evidence)
  ctx.py add "Slice" [--acceptance TEXT]
  ctx.py phase [NAME] [--force --reason TEXT]   show the lifecycle phase and its next gate, or move (requirements|design|build|verify|release|maintain)
  ctx.py stack [ID]                      detect the stack, or fill PROJECT.md Stack and Commands from references/stacks/ID.md
  ctx.py map [--depth N] [--max-lines N] regenerate the Structure map in PROJECT.md
  ctx.py check                           find stale or missing context and oversized files

Global option: --root DIR (default: current directory). Standard library only.
"""
import argparse
import ast
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DIR = ".ai-dev-office"
STATES = ("todo", "building", "built", "verified", "blocked")
CAP_PROJECT = 6000   # bytes, about 1.5k tokens
CAP_STATUS = 4000    # bytes
MAX_SLICES = 20
MAX_FILES = 5000
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next", ".nuxt", "target",
             ".idea", ".vscode", "coverage", ".pytest_cache", ".mypy_cache", ".gradle", "vendor", DIR}
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
STACK_DIR = Path(__file__).resolve().parents[1] / "references" / "stacks"
PHASES = ("requirements", "design", "build", "verify", "release", "maintain")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillfmt  # noqa: E402
MAP_START, MAP_END = "<!-- map:start -->", "<!-- map:end -->"


def approx_tokens(text: str) -> int:
    return len(text) // 4  # rough estimate (about 4 characters per token), not a billing figure


def today() -> str:
    return dt.date.today().isoformat()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8", newline="\n")


def cell(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("|", "/")).strip()


# ---------------------------------------------------------------------------
# STATUS.md
# ---------------------------------------------------------------------------
def parse_status(text: str):
    """Return (head_lines, rows, tail_lines). Rows are dicts: n, slice, acceptance, state, evidence."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r"^\|\s*#\s*\|", l)), None)
    if start is None:
        raise ValueError("STATUS.md has no table header line starting with '| # |'")
    head, rows, i = lines[:start], [], start + 2
    while i < len(lines) and lines[i].startswith("|"):
        parts = [p.strip() for p in lines[i].strip().strip("|").split("|")]
        parts += [""] * (5 - len(parts))
        if parts[0].isdigit():
            rows.append(dict(n=int(parts[0]), slice=parts[1], acceptance=parts[2], state=parts[3] or "todo", evidence=parts[4]))
        i += 1
    return head, rows, lines[i:]


def render_status(head, rows, tail) -> str:
    out = list(head) + ["| # | Slice | Acceptance | State | Evidence |", "|---|---|---|---|---|"]
    out += [f"| {r['n']} | {cell(r['slice'])} | {cell(r['acceptance'])} | {r['state']} | {cell(r['evidence'])} |" for r in rows]
    return "\n".join(out + tail).rstrip() + "\n"


def set_header(head, key, value):
    last = None
    for i, line in enumerate(head):
        if line.startswith(f"{key}:"):
            head[i] = f"{key}: {value}"
            return
        if re.match(r"^[A-Za-z]+:", line):
            last = i
    if last is None:
        head.append(f"{key}: {value}")
    else:
        head.insert(last + 1, f"{key}: {value}")


def get_header(head, key, default=""):
    return next((l.split(":", 1)[1].strip() for l in head if l.startswith(f"{key}:")), default)


def load_status(root: Path):
    path = root / DIR / "STATUS.md"
    if not path.exists():
        raise FileNotFoundError(f"{DIR}/STATUS.md not found. Run: ctx init")
    return path, *parse_status(read(path))


def summarize(rows) -> str:
    counts = {s: sum(1 for r in rows if r["state"] == s) for s in STATES}
    parts = [f"{counts['verified']}/{len(rows)} verified"] + [f"{counts[s]} {s}" for s in ("building", "built", "todo", "blocked") if counts[s]]
    return " · ".join(parts) if rows else "no slices yet"


def next_slice(rows):
    for wanted in ("building", "built", "todo"):
        for r in rows:
            if r["state"] == wanted:
                return r
    return None


# ---------------------------------------------------------------------------
# Plan -> slices
# ---------------------------------------------------------------------------
def plan_slices(text: str) -> list:
    """Top-level list items under the heading that mentions 'implementation' (or 'steps')."""
    lines = text.splitlines()
    level, start = None, None
    for i, l in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)", l)
        if m and re.search(r"implementation|build steps|roadmap", m.group(2), re.I):
            level, start = len(m.group(1)), i + 1
            break
    if start is None:
        return []
    items = []
    for l in lines[start:]:
        m = re.match(r"^(#{1,6})\s", l)
        if m and len(m.group(1)) <= level:
            break
        item = re.match(r"^(\d+[.)]|[-*+])\s+(.+?)\s*$", l)  # no indentation = top level only
        if item:
            items.append(re.sub(r"[*_`]", "", item.group(2)))
    return items[:MAX_SLICES]


# ---------------------------------------------------------------------------
# Repo map
# ---------------------------------------------------------------------------
def list_files(root: Path) -> list:
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
                           capture_output=True, timeout=30)
        if r.returncode == 0:
            names = [n for n in r.stdout.decode("utf-8", "replace").split("\0") if n]
            files = [n for n in names if not any(part in SKIP_DIRS for part in Path(n).parts[:-1]) and (root / n).is_file()]
            return sorted(files)[:MAX_FILES]
    except (OSError, subprocess.SubprocessError):
        pass
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in filenames:
            files.append(os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/"))
            if len(files) >= MAX_FILES:
                return sorted(files)
    return sorted(files)


_JS_DECL = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?|class)\s+([A-Za-z_$][\w$]*)", re.M)
_JS_CONST = re.compile(r"^export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)", re.M)


def symbols(path: Path, limit: int = 6) -> str:
    ext = path.suffix.lower()
    if ext not in CODE_EXT:
        return ""
    try:
        if path.stat().st_size > 200_000:
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        if ext == ".py":
            names = [n.name for n in ast.parse(text).body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_")]
        else:
            names = _JS_DECL.findall(text) + _JS_CONST.findall(text)
    except (OSError, SyntaxError, ValueError):
        return ""
    seen, uniq = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    shown = ", ".join(uniq[:limit]) + (f", +{len(uniq) - limit}" if len(uniq) > limit else "")
    return f" — {shown}" if shown else ""


def _tree(files):
    root = {"files": [], "dirs": {}}
    for f in files:
        node = root
        *dirs, name = f.split("/")
        for d in dirs:
            node = node["dirs"].setdefault(d, {"files": [], "dirs": {}})
        node["files"].append(name)
    return root


def _count(node) -> int:
    return len(node["files"]) + sum(_count(c) for c in node["dirs"].values())


def render_map(root: Path, files, depth: int, max_lines: int):
    tree = _tree(files)

    def walk(node, prefix, level, limit, out):
        indent = "  " * level
        shown = sorted(node["files"])
        for name in shown[:12]:
            out.append(f"{indent}{name}{symbols(root / prefix / name)}")
        if len(shown) > 12:
            out.append(f"{indent}… +{len(shown) - 12} more files")
        for d in sorted(node["dirs"]):
            child = node["dirs"][d]
            if level + 1 > limit:
                out.append(f"{indent}{d}/ ({_count(child)} files)")
            else:
                out.append(f"{indent}{d}/")
                walk(child, f"{prefix}/{d}" if prefix else d, level + 1, limit, out)

    limit = depth
    while True:
        out = []
        walk(tree, "", 0, limit, out)
        if len(out) <= max_lines or limit <= 1:
            break
        limit -= 1
    if len(out) > max_lines:
        extra = len(out) - max_lines
        out = out[:max_lines] + [f"… {extra} more lines (raise --max-lines or lower --depth)"]
    return out


def map_block(lines, nfiles, now=None) -> str:
    stamp = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (f"{MAP_START}\n_Generated: {stamp} by `ctx map`. Files: {nfiles}. Do not edit by hand._\n\n```\n"
            + "\n".join(lines) + f"\n```\n{MAP_END}")


def map_info(project_text: str):
    m = re.search(r"_Generated: (\S+) by `ctx map`\. Files: (\d+)", project_text)
    if not m:
        return None
    ts = dt.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    return ts, int(m.group(2))


def stale_reason(root: Path, project_text: str):
    info = map_info(project_text)
    if not info:
        return "no repo map yet (run: ctx map)"
    ts, count = info
    files = list_files(root)
    if len(files) != count:
        return f"repo map is stale: file count changed ({count} → {len(files)}). Run: ctx map"
    newer = [f for f in files if (root / f).exists() and (root / f).stat().st_mtime > ts + 1]
    if newer:
        return f"repo map may be stale: {len(newer)} file(s) changed since it was generated. Run: ctx map"
    return None


# ---------------------------------------------------------------------------
# Lifecycle phases, gates and stacks
# ---------------------------------------------------------------------------
def plan_file(root: Path):
    for p in (root / "PLAN.md", root / DIR / "PLAN.md"):
        if p.exists():
            return p
    return None


def section_body(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def project_text(root: Path) -> str:
    p = root / DIR / "PROJECT.md"
    return read(p) if p.exists() else ""


def gate_problems(root: Path, target: str, current: str, rows) -> list:
    """What is missing before the project may ENTER `target`. Empty list = gate passes."""
    problems = []
    ci, ti = PHASES.index(current), PHASES.index(target)
    if ti > ci + 1:
        problems.append(f"skips ahead from {current} to {target}; move one phase at a time")
    if ti <= ci:
        return problems  # going back (rework) is always allowed
    if target in ("design", "build"):
        pf = plan_file(root)
        if not pf:
            problems.append("no PLAN.md (project root or .ai-dev-office/): run plan mode first")
        elif not re.search(r"(?im)^#{1,6}\s+.*requirement", read(pf)):
            problems.append("PLAN.md has no Requirements section")
    if target == "build":
        if not rows:
            problems.append("no slices yet (ctx init --from-plan PLAN.md, or ctx add)")
        missing = [r["n"] for r in rows if not r["acceptance"]]
        if missing:
            problems.append("slices without an acceptance sentence: " + ", ".join(f"#{n}" for n in missing))
        proj = project_text(root)
        stack = [l for l in section_body(proj, "Stack").splitlines() if l.strip().startswith("-")]
        cmds = commands_block(proj)
        if not stack or any("TODO" in l for l in stack):
            problems.append("PROJECT.md Stack is empty or TODO (ctx stack <id>)")
        if not cmds or any("TODO" in l for l in cmds):
            problems.append("PROJECT.md Commands are empty or TODO (ctx stack <id>, or edit by hand)")
    if target == "verify":
        open_ = [r["n"] for r in rows if r["state"] in ("todo", "building")]
        if open_:
            problems.append("slices not built yet: " + ", ".join(f"#{n}" for n in open_))
    if target in ("release", "maintain"):
        unver = [r["n"] for r in rows if r["state"] in ("todo", "building", "built")]
        blocked = [r["n"] for r in rows if r["state"] == "blocked"]
        if target == "release" and not rows:
            problems.append("no slices to release")
        if unver:
            problems.append("slices not verified: " + ", ".join(f"#{n}" for n in unver))
        if blocked and target == "release":
            problems.append("blocked slices must be resolved or dropped: " + ", ".join(f"#{n}" for n in blocked))
    return problems


def add_issue(tail, text):
    for i, line in enumerate(tail):
        if line.strip() == "## Open issues":
            j = i + 1
            if j < len(tail) and tail[j].startswith("- None yet"):
                tail[j] = f"- {text}"
            else:
                tail.insert(j, f"- {text}")
            return
    tail += ["", "## Open issues", f"- {text}"]


def detect_stacks(root: Path) -> list:
    def text(name):
        try:
            return (root / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    found = []
    if (root / "artisan").exists() and "laravel/framework" in text("composer.json"):
        found.append("laravel")
    if (root / "manage.py").exists() and "django" in text("manage.py").lower():
        found.append("django")
    if not found and (root / "package.json").exists():
        try:
            data = json.loads(text("package.json") or "{}")
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        except ValueError:
            deps = {}
        found.append("nextjs" if "next" in deps else "node")
    if not found and (root / "index.html").exists():
        found.append("static")
    return found


def available_stacks() -> list:
    return sorted(p.stem for p in STACK_DIR.glob("*.md")) if STACK_DIR.exists() else []


def apply_stack(project: str, stack_id: str):
    """Fill TODO placeholders in PROJECT.md from references/stacks/<id>.md. Returns (new text, notes)."""
    meta, body = skillfmt.parse_frontmatter(read(STACK_DIR / f"{stack_id}.md"))
    name = meta.get("name", stack_id)
    stack_cmds = [l for l in skillfmt.split_sections(body).get("Commands", "").splitlines() if l.strip().startswith("-")]
    notes = []
    lines = project.split("\n")

    def bounds(heading):
        start = next((i for i, l in enumerate(lines) if l.startswith(f"## {heading}")), None)
        if start is None:
            return None, None
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        return start, end

    a, b = bounds("Stack")
    if a is not None:
        items = [i for i in range(a + 1, b) if lines[i].strip().startswith("-")]
        if items and all("TODO" in lines[i] for i in items):
            lines[items[0]] = f"- {name}"
            for i in reversed(items[1:]):
                del lines[i]
            notes.append("Stack set")
        elif not any(name in lines[i] for i in items):
            lines.insert(items[-1] + 1 if items else a + 1, f"- {name}")
            notes.append("Stack line added")
    a, b = bounds("Commands")
    changed = 0
    if a is not None:
        for sc in stack_cmds:
            label = sc.strip()[1:].split(":", 1)[0].strip()
            for i in range(a + 1, b):
                if lines[i].strip().startswith(f"- {label}:") and lines[i].split(":", 1)[1].strip() == "TODO":
                    lines[i] = sc.strip()
                    changed += 1
        notes.append(f"{changed} command(s) filled in" + ("" if changed else " (none were TODO; your own lines were kept)"))
    return "\n".join(lines), notes


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_init(root: Path, args) -> int:
    d = root / DIR
    d.mkdir(exist_ok=True)
    for name in ("PROJECT.md", "STATUS.md"):
        target = d / name
        if target.exists():
            print(f"kept   {DIR}/{name} (already exists)")
        else:
            write(target, read(TEMPLATES / name).replace("YYYY-MM-DD", today()))
            print(f"wrote  {DIR}/{name}")
    if args.from_plan:
        plan = Path(args.from_plan)
        if not plan.is_absolute():
            plan = root / plan
        if not plan.exists():
            print(f"Plan file not found: {plan}")
            return 1
        slices = plan_slices(read(plan))
        path, head, rows, tail = load_status(root)
        if rows:
            print("STATUS.md already has slices; not adding from the plan.")
        elif not slices:
            print("No implementation steps found in the plan; add slices with: ctx add \"...\"")
        else:
            rows = [dict(n=i, slice=s, acceptance="", state="todo", evidence="") for i, s in enumerate(slices, 1)]
            set_header(head, "Updated", today())
            set_header(head, "Phase", "design")
            set_header(head, "Resume", "Write each slice's acceptance sentence, then ctx stack <id>, then ctx phase build.")
            write(path, render_status(head, rows, tail))
            print(f"added  {len(rows)} slices from {plan.name}; phase is now design")
    found = detect_stacks(root)
    if found:
        print(f"Detected stack: {found[0]}. Fill in Stack and Commands with: ctx stack {found[0]}")
    print("Next: fill in Stack and Commands in PROJECT.md (or ctx stack <id>), then run: ctx map")
    return 0


def cmd_status(root: Path, args) -> int:
    _, head, rows, _ = load_status(root)
    print(summarize(rows))
    nxt = next_slice(rows)
    if nxt:
        print(f"Next: #{nxt['n']} {nxt['slice']} [{nxt['state']}]" + (f" — {nxt['acceptance']}" if nxt["acceptance"] else ""))
    phase = get_header(head, "Phase")
    if phase:
        print(f"Phase: {phase}")
    resume = get_header(head, "Resume")
    if resume:
        print(f"Resume: {resume}")
    return 0


def commands_block(project_text: str, limit: int = 12) -> list:
    m = re.search(r"^## Commands\s*\n(.*?)(?=^## |\Z)", project_text, re.M | re.S)
    if not m:
        return []
    return [l for l in m.group(1).splitlines() if l.strip().startswith("-")][:limit]


def cmd_resume(root: Path, args) -> int:
    if not (root / DIR / "STATUS.md").exists():
        print(f"No {DIR}/ here. For a new project run: ctx init   (add --from-plan PLAN.md if you have a plan)")
        return 0
    cmd_status(root, args)
    project = read(root / DIR / "PROJECT.md") if (root / DIR / "PROJECT.md").exists() else ""
    cmds = commands_block(project)
    if cmds:
        print("Commands:")
        for c in cmds:
            print("  " + c)
    if "TODO" in "\n".join(cmds):
        print("WARN: Commands still has TODO. Fill them in once the stack is known.")
    reason = stale_reason(root, project) if project else None
    if reason:
        print("WARN: " + reason)
    found = detect_stacks(root)
    if found and (STACK_DIR / f"{found[0]}.md").exists():
        print(f"Stack notes: references/stacks/{found[0]}.md (read once)")
    return 0


def cmd_set(root: Path, args) -> int:
    if args.state not in STATES:
        print(f"State must be one of: {', '.join(STATES)}")
        return 2
    path, head, rows, tail = load_status(root)
    row = next((r for r in rows if r["n"] == args.n), None)
    if not row:
        print(f"No slice #{args.n}. Slices: {', '.join(str(r['n']) for r in rows) or 'none'}")
        return 1
    evidence = cell(args.evidence) if args.evidence is not None else row["evidence"]
    acceptance = cell(args.acceptance) if args.acceptance is not None else row["acceptance"]
    if args.state in ("building", "verified") and not acceptance:
        print(f"Slice #{args.n} has no acceptance sentence. Write one first: ctx set {args.n} {args.state} --acceptance \"<what a user can do, checkably>\"")
        return 1
    if args.state == "verified" and not evidence:
        print("A slice can only be 'verified' with evidence: --evidence \"<command and result, or what you did and saw>\"")
        return 1
    if args.state == "building":
        busy = [r["n"] for r in rows if r["state"] == "building" and r["n"] != args.n]
        if busy:
            print(f"WARN: slice(s) {busy} are already 'building'. Finish or park them first.")
    row["state"], row["evidence"], row["acceptance"] = args.state, evidence, acceptance
    set_header(head, "Updated", today())
    if args.resume is not None:
        set_header(head, "Resume", cell(args.resume))
    else:
        nxt = next_slice(rows)
        set_header(head, "Resume", f"Continue with #{nxt['n']} {nxt['slice']}." if nxt else "All slices verified. Run ship mode.")
    text = render_status(head, rows, tail)
    write(path, text)
    print(f"#{args.n} → {args.state}. {summarize(rows)}")
    if len(text.encode("utf-8")) > CAP_STATUS:
        print(f"WARN: STATUS.md is over {CAP_STATUS} bytes; shorten evidence or archive finished slices.")
    return 0


def cmd_phase(root: Path, args) -> int:
    path, head, rows, tail = load_status(root)
    current = get_header(head, "Phase") or "requirements"
    if current not in PHASES:
        print(f"STATUS.md has an unknown Phase '{current}'. Valid: {', '.join(PHASES)}")
        return 1
    if not args.name:
        print(f"Phase: {current}")
        if current == PHASES[-1]:
            print("maintain is the final phase. Changes go through maintain mode.")
            return 0
        nxt = PHASES[PHASES.index(current) + 1]
        problems = gate_problems(root, nxt, current, rows)
        print(f"Gate to {nxt}: " + ("all checks pass" if not problems else f"{len(problems)} to fix"))
        for p in problems:
            print("  ✗ " + p)
        return 0
    if args.name not in PHASES:
        print(f"Unknown phase '{args.name}'. Valid: {', '.join(PHASES)}")
        return 2
    problems = gate_problems(root, args.name, current, rows)
    if problems and not args.force:
        print(f"Cannot enter {args.name} yet:")
        for p in problems:
            print("  ✗ " + p)
        print("Fix these, or accept the risk with: ctx phase " + args.name + " --force --reason \"...\"")
        return 1
    if problems and args.force:
        if not (args.reason or "").strip():
            print("--force needs --reason \"why this is acceptable\"")
            return 2
        add_issue(tail, f"Gate waived {today()} entering {args.name}: {'; '.join(problems)} | reason: {cell(args.reason)}")
    set_header(head, "Phase", args.name)
    set_header(head, "Updated", today())
    write(path, render_status(head, rows, tail))
    print(f"Phase: {current} → {args.name}" + (" (gate waived and recorded)" if problems else ""))
    return 0


def cmd_stack(root: Path, args) -> int:
    found = detect_stacks(root)
    avail = available_stacks()
    if not args.id:
        print("Detected: " + (", ".join(found) if found else "no known stack"))
        print("Notes available for: " + ", ".join(avail))
        if found and found[0] in avail:
            print(f"Apply with: ctx stack {found[0]}")
        return 0
    if args.id not in avail:
        print(f"No notes for '{args.id}'. Available: {', '.join(avail)}. For other stacks, edit PROJECT.md by hand.")
        return 1
    pp = root / DIR / "PROJECT.md"
    if not pp.exists():
        print(f"{DIR}/PROJECT.md not found. Run: ctx init")
        return 1
    text, notes = apply_stack(read(pp), args.id)
    write(pp, text)
    print(f"{args.id}: " + "; ".join(notes) + f". Read references/stacks/{args.id}.md once for the conventions.")
    return 0


def cmd_add(root: Path, args) -> int:
    path, head, rows, tail = load_status(root)
    n = max([r["n"] for r in rows], default=0) + 1
    rows.append(dict(n=n, slice=args.slice, acceptance=args.acceptance or "", state="todo", evidence=""))
    set_header(head, "Updated", today())
    write(path, render_status(head, rows, tail))
    print(f"added #{n}. {summarize(rows)}")
    return 0


def cmd_map(root: Path, args) -> int:
    project_path = root / DIR / "PROJECT.md"
    if not project_path.exists():
        print(f"{DIR}/PROJECT.md not found. Run: ctx init")
        return 1
    files = list_files(root)
    block = map_block(render_map(root, files, args.depth, args.max_lines), len(files))
    text = read(project_path)
    if MAP_START in text and MAP_END in text:
        before = text.split(MAP_START)[0]
        after = text.split(MAP_END, 1)[1]
        text = before + block + after
    else:
        text = text.rstrip() + "\n\n## Structure map\n" + block + "\n"
    write(project_path, text)
    size = len(text.encode("utf-8"))
    print(f"map updated: {len(files)} files, PROJECT.md is {size} bytes (~{approx_tokens(text)} tokens)")
    if size > CAP_PROJECT:
        print(f"WARN: PROJECT.md is over {CAP_PROJECT} bytes. Lower --depth or --max-lines.")
    return 0


def cmd_check(root: Path, args) -> int:
    problems, warns = [], []
    d = root / DIR
    sp, pp = d / "STATUS.md", d / "PROJECT.md"
    if not sp.exists() or not pp.exists():
        print(f"FAIL {DIR}/ is incomplete. Run: ctx init")
        return 1
    ptext, stext = read(pp), read(sp)
    for name, text, cap in (("PROJECT.md", ptext, CAP_PROJECT), ("STATUS.md", stext, CAP_STATUS)):
        size = len(text.encode("utf-8"))
        if size > cap:
            msg = f"{name} is {size} bytes (~{approx_tokens(text)} tokens, target {cap}): trim it"
            (warns if size <= cap * 1.5 else problems).append(msg)
    try:
        _, rows, _ = parse_status(stext)
    except ValueError as e:
        problems.append(str(e))
        rows = []
    for r in rows:
        if r["state"] not in STATES:
            problems.append(f"slice #{r['n']} has unknown state '{r['state']}'")
        if r["state"] == "verified" and not r["evidence"]:
            problems.append(f"slice #{r['n']} is verified but has no evidence")
    building = [r["n"] for r in rows if r["state"] == "building"]
    if len(building) > 1:
        warns.append(f"more than one slice is 'building': {building}")
    cmds = "\n".join(commands_block(ptext))
    if not cmds or "TODO" in cmds:
        warns.append("PROJECT.md Commands are empty or still TODO")
    reason = stale_reason(root, ptext)
    if reason:
        warns.append(reason)
    for p in problems:
        print("FAIL " + p)
    for w in warns:
        print("WARN " + w)
    if not problems and not warns:
        print("OK: context is current.")
    return 1 if problems else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--from-plan")
    sub.add_parser("resume"); sub.add_parser("status"); sub.add_parser("check")
    p = sub.add_parser("set"); p.add_argument("n", type=int); p.add_argument("state"); p.add_argument("--acceptance"); p.add_argument("--evidence"); p.add_argument("--resume")
    p = sub.add_parser("phase"); p.add_argument("name", nargs="?"); p.add_argument("--force", action="store_true"); p.add_argument("--reason")
    p = sub.add_parser("stack"); p.add_argument("id", nargs="?")
    p = sub.add_parser("add"); p.add_argument("slice"); p.add_argument("--acceptance")
    p = sub.add_parser("map"); p.add_argument("--depth", type=int, default=3); p.add_argument("--max-lines", type=int, default=120)
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    handlers = dict(init=cmd_init, resume=cmd_resume, status=cmd_status, set=cmd_set, add=cmd_add, map=cmd_map, check=cmd_check, phase=cmd_phase, stack=cmd_stack)
    try:
        return handlers[args.cmd](root, args)
    except (FileNotFoundError, ValueError) as e:
        print(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
