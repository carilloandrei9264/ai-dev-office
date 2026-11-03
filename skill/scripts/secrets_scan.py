#!/usr/bin/env python3
"""Pattern-based scan of a project for secrets that should not be committed.

Usage (from the project root):  python secrets_scan.py [--root DIR]

Exit code 0 = nothing found, 1 = findings. Matches are masked in the output.
Limits: this finds well-known token formats and obvious hard-coded credentials only. It does not read git
history. If a secret was ever committed, rotate it; deleting the line is not enough.
Add `secretscan:ignore` to a line to silence a false positive. Standard library only.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next", "target", "vendor", ".ai-dev-office"}
MAX_BYTES = 1_000_000
PATTERNS = [
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("API key (sk- style)", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}\b")),
    ("Hard-coded credential", re.compile(r"""(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d|private[_-]?key)\b\s*[:=]\s*["']([^"'\s]{8,})["']""")),
]
ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASS)[A-Z0-9_]*)\s*=\s*(\S{8,})\s*$")
PLACEHOLDER = re.compile(r"(?i)example|your[_-]|xxxx|<|\$\{|\{\{|changeme|placeholder|dummy|\*{4}|process\.env|os\.environ|getenv")
ENV_SAMPLE_SUFFIX = (".example", ".sample", ".template", ".dist")


def mask(value: str) -> str:
    return value[:4] + "…" if len(value) > 4 else "…"


def list_files(root: Path):
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True, timeout=30)
        if r.returncode == 0:
            names = [n for n in r.stdout.decode("utf-8", "replace").split("\0") if n]
            return sorted(n for n in names if not any(p in SKIP_DIRS for p in Path(n).parts[:-1]) and (root / n).is_file())
    except (OSError, subprocess.SubprocessError):
        pass
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        out += [os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/") for f in filenames]
    return sorted(out)


def scan_text(name: str, text: str):
    findings = []
    is_env = Path(name).name.startswith(".env") and not Path(name).name.endswith(ENV_SAMPLE_SUFFIX)
    for i, line in enumerate(text.splitlines(), 1):
        if "secretscan:ignore" in line:
            continue
        for label, rx in PATTERNS:
            m = rx.search(line)
            if m:
                value = m.group(1) if m.groups() else m.group(0)
                if PLACEHOLDER.search(value) or PLACEHOLDER.search(line) and label == "Hard-coded credential":
                    continue
                findings.append((i, label, mask(value)))
                break
        else:
            if is_env:
                m = ENV_LINE.match(line)
                if m and not PLACEHOLDER.search(m.group(2)):
                    findings.append((i, f"Secret in env file ({m.group(1)})", mask(m.group(2))))
    return findings


def gitignore_covers_env(root: Path) -> bool:
    gi = root / ".gitignore"
    if not gi.exists():
        return False
    rules = {l.strip() for l in gi.read_text(encoding="utf-8", errors="replace").splitlines()}
    return bool(rules & {".env", ".env*", "*.env", "/.env", ".env.*", ".env.local"})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    root = Path(ap.parse_args(argv).root).resolve()
    files, findings, scanned = list_files(root), [], 0
    for rel in files:
        path = root / rel
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:2048]:
            continue
        scanned += 1
        for line, label, masked in scan_text(rel, data.decode("utf-8", errors="replace")):
            findings.append((rel, line, label, masked))
    for rel, line, label, masked in findings:
        print(f"{rel}:{line}: {label}: {masked}")
    has_env = any(Path(f).name == ".env" for f in files) or (root / ".env").exists()
    if has_env and not gitignore_covers_env(root):
        print("WARN: a .env file exists but .gitignore does not ignore it.")
        findings.append((".gitignore", 0, ".env not ignored", ""))
    print(f"Scanned {scanned} files. " + ("FOUND issues above. Rotate any real secret; deleting it is not enough." if findings else "Nothing found (pattern-based check, not a guarantee)."))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
