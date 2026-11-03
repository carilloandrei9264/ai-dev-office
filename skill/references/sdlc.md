# Lifecycle (SDLC)

Every project passes through the same phases. The size of the project decides how much paperwork each one gets, never whether it happens. `ctx phase` tracks the current phase and checks the gate before moving on.

| Phase | Mode | Produces | Gate to enter the next phase |
|---|---|---|---|
| 1. Requirements | plan | Problem, users and roles, requirements with acceptance criteria, out of scope | A plan file exists with a Requirements section |
| 2. Design | plan | Stack, architecture, data model, screens, security and test approach, slices | Slices exist, each with an acceptance sentence; Stack and Commands filled in |
| 3. Build | build | Working slices, one at a time, tests first | No slice left `todo` or `building` |
| 4. Verify | build | Evidence per slice: command and result, or what was done and seen | Every slice `verified` (or `blocked` and explained) |
| 5. Release | ship | Checklist report, secrets scan, changelog, deploy only if asked | All slices are verified before entering release; run and report the checklist and deployed behavior (if deployed) in ship mode |
| 6. Maintain | maintain | Bug fixes, small changes, dependency updates, each as a tracked slice | All slices are verified; a change that grows becomes a new Requirements pass |

Moving back is always allowed (rework). Skipping forward, or moving past a failing gate, needs `--force --reason "..."`; the waiver is recorded in STATUS.md.

## Right-size the process

| Size | Typical project | How much |
|---|---|---|
| Light | Portfolio, brochure site, landing page: no accounts, no money, no stored personal data | Requirements in about 5 bullets. Slices per page or section. Verify in a real browser, contrast and links. Ship with the website items only. |
| Standard | Small business site or app with accounts, forms or a database | The full plan. Slices per user flow. A test for each slice. Security and QA advisors. Full ship checklist. |
| Heavy | Payments, sensitive personal data, several roles, third-party integrations | Standard, plus: security advisor is mandatory, the data model is reviewed before any code, a migration plan, a backup and tested restore, staged release with a rollback plan, monitoring. |

When unsure, ask one question about accounts, money and personal data, then pick the size and say which.

## Requirements and acceptance

- A requirement says what a user can do or what the system must guarantee, in one sentence. Non-functional requirements (speed, accessibility, browser support, privacy) count too.
- Each requirement gets an acceptance criterion that can be checked: "a visitor can book a room and receives a confirmation email", not "booking works well".
- A slice's acceptance sentence comes from one or more requirements. `ctx` will not start a slice without one.

## Definition of ready and done

- A slice is **ready** when it has an acceptance sentence, its dependencies are done, and you know how it will be checked.
- A slice is **done** when the acceptance sentence holds in the real flow (including a denied, an invalid and a failure case), project checks pass, and the evidence is recorded with `ctx set N verified`.

## Traceability

Requirement → slice acceptance → test → evidence. Keep it as one line per slice in STATUS.md; do not build a separate matrix.

## Changes during the build

A new request is a change request, not a silent addition: add it as a slice (`ctx add`), say what it displaces or delays, and note in `PROJECT.md` Decisions if it changes scope. If it changes the data model, permissions or payments, return to Design for that slice first.

## Where things live

| Artifact | Location |
|---|---|
| Plan (requirements, design) | `PLAN.md` in the project root |
| Stack, commands, decisions, code map | `.ai-dev-office/PROJECT.md` |
| Phase, slices, evidence, open issues | `.ai-dev-office/STATUS.md` |
| What changed per release | `CHANGELOG.md` (short, user-facing) |
| How to run it | `README.md` |
