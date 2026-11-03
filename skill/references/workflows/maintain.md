# Maintain mode

For a project that is live or finished. Every change is a small tracked slice; nothing is "just a quick fix" without a check.

## 1. Start
`ctx resume`. If the phase is not `maintain`, run `ctx phase maintain` (or `ctx phase build` when the work is a new feature set).

## 2. Triage
Classify the request, add it as a slice (`ctx add "[bug] ..." --acceptance "..."`), and size it:

| Kind | Do |
|---|---|
| **Bug** | Reproduce first. Find the cause with evidence. Smallest fix. Add a regression test that fails without it. |
| **Urgent production bug** | Reproduce or confirm from logs, fix on its own branch, run the full checks, release only if the user asks, check the live behavior, then write down what happened in PROJECT.md `Decisions`. |
| **Small change** | One slice through the normal loop in `build.md`. |
| **Bigger change** | It is a new requirement: go to plan mode for that slice, then build. |
| **Dependency or platform update** | One package or one group at a time. Read its changelog for breaking changes. Run tests, build and the real flow. Run the ecosystem audit (`npm audit`, `composer audit`, `pip-audit`). Never mix an update with feature work. |
| **Chore** (docs, cleanup) | Smallest change; run the checks. |

## 3. After the change
- Verify like any slice and record the evidence.
- Update `CHANGELOG.md` with one user-facing line, and README or `.env.example` if setup changed.
- `ctx map` if structure changed. Add a PROJECT.md Decision for any non-obvious choice.
- Release only when the user asks (see `ship.md`), then check the deployed behavior.

## 4. Regular health checks (when asked, or on a schedule the user sets)
Dependency audit, expired certificates and secrets, backup restore test, error logs for new failures, broken links, slow pages. Report findings as slices; fix only what the user approves.

## Rules
- Do not refactor while fixing a bug unless the bug cannot be fixed otherwise.
- Do not change production data or infrastructure without an explicit request.
- Two failed attempts: stop, report what you tried and what you suspect.
