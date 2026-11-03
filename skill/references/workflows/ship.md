# Ship mode

Decide what applies to this project, check it, and report only what was actually checked. Skip items that do not apply and say why ("static site: no login").

## 1. Before checking

`ctx resume`, then `ctx phase release`. If the gate fails, a slice is not verified: say which, and fix or drop it. Do not use `--force` unless the user accepts shipping with it and gives a reason.

## 2. Checklist

Run each item, then mark it pass, fail, partial or not run, with the evidence.

**Always**
- Project checks pass: tests, lint, type check, build (commands in PROJECT.md).
- `python <skill>/scripts/secrets_scan.py` is clean, and `.env` is ignored by git. A secret that was ever committed must be rotated, not just deleted.
- Dependencies: run the ecosystem's audit (`npm audit`, `pip-audit`, ...) if installed. Report not run if not.
- README says how to install, configure (env variable names only, never values), run and test.
- Errors are handled and shown plainly; nothing leaks stack traces to users.
- Anything stateful has backups and one tested restore.

**Accounts, personal data, payments, public API**
- Walk `references/security-checklist.md` and keep what applies. Permissions are enforced on the server.
- Privacy policy and terms match what the product really does. Cookie consent only where needed.

**Websites and apps people look at**
- Walk `references/web-quality.md` end to end for every page and flow, and the stack notes' Release section.
- Worst-case content tried (very long names, empty lists, other languages) and no broken links.

## 3. Release

Deploy, publish or tag only if the user asked in this conversation. Add a short user-facing entry to `CHANGELOG.md`. Afterwards check the deployed behavior, not just that the deploy command succeeded. Note how to roll back. Then `ctx phase maintain`.

## 4. Report

One short table: item, result (pass, fail, partial, not run), evidence. Then blockers, top fixes in order, and what was not run and how to run it. No invented score: only counts of what passed, failed and was not run.
