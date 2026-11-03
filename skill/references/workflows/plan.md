# Plan mode

Plan first, build later. You work as a small team, one role at a time, and hand the user one final plan they can build from. Do not write code in this mode.

## Stages

Run the stages in order. Read a file only when you reach the stage that needs it.

### 1. Intake
Capture the brief: the problem and who has it, the users and roles, the must-have features, the stack if the user named one, and constraints (budget, hosting, deadline, existing code). Ask at most three short questions, and only about what you cannot infer: experience level (beginner, intermediate, advanced), stack or hard limits, and detail level (concise, standard, detailed). If the user already answered or says "use defaults", skip the questions and state your assumptions in one line (intermediate, no stack preference, standard detail).

Size the process with `references/sdlc.md` (light, standard or heavy) and say which in one line. A user-named stack is a decision: plan with it, and say plainly if it is a poor fit instead of swapping it.

### 2. Research
Read `references/roles/researcher.md`. Cover: recommended stack (frontend, backend, database, hosting), architecture, key features and how to implement them, likely challenges, current best practices. If the user named a stack with notes in `references/stacks/` (`laravel`, `node`, `nextjs`, `django`, `static`), read that file and plan with its conventions. Use web search and page reading only to verify things that go stale (versions, pricing, documentation) and keep calls few. Never invent libraries or versions.

### 3. Draft
Read `references/roles/writer.md` and `references/plan-template.md`. Write the draft plan with the required sections from the template, scaled to the detail level and project size. Requirements come first: numbered, one sentence each, each with a checkable acceptance criterion.

### 4. Pick advisors
Read `references/roles/router.md`. Choose the fewest advisors that add real value: at least one, at most three by default (five only if the user asks for a full review). If nothing stands out, pick `sec` and `qa`. Say which you chose and why, one short line each.

| id | Load | Bring in when | Skip when |
|---|---|---|---|
| `ux` | `references/advisors/ux.md` | people look at or use screens, flows, forms | backend-only service, CLI, data pipeline |
| `db` | `references/advisors/db.md` | records, users, orders or relationships are stored | static content, no persistent data |
| `sec` | `references/advisors/sec.md` | accounts, roles, personal data, payments, public API, uploads | static site with no forms or login |
| `devops` | `references/advisors/devops.md` | it must be hosted, deployed, scaled or monitored | local script or throwaway prototype |
| `qa` | `references/advisors/qa.md` | real money, data or many user flows are at stake | throwaway prototype |

### 5. Advisor pass
For each chosen advisor, read its file and review the draft in that role. Give 4 to 6 concrete, prioritized suggestions specific to this project, about 200 words at most, as a Markdown bullet list. No generic filler. If your host can run subagents, give each advisor a fresh one with only the project, the preferences, the first ~6000 characters of the draft and that advisor's file. Otherwise do it in sequence as separate, labelled passes.

### 6. Review and merge
Read `references/roles/reviewer.md`. Check the draft for missing details, technical risks, security issues and clarity. Then write the improved final plan: keep the template's required sections, merge the useful advisor suggestions, drop generic ones, resolve conflicts between advisors, and add one section per consulted advisor (its `section` name). Do this as its own pass, not while drafting: a plan reviewed in the same breath it was written gets a weaker review.

### 7. Deliver
Return only the final plan in Markdown, ending with `## Review Notes` (what you improved, what risks remain). If you can write files and the user is working in a project folder, offer to save it as `PLAN.md`; do not write files unasked. Finish with which claims are verified, from memory, or still need a check, and offer the next step: building the first slice (build mode). Building starts with `ctx init --from-plan PLAN.md`, which turns the implementation steps into slices.

## Tools

Use your host's own equivalents. Where there is none, say so in the plan instead of guessing.

| Tool name | What to use |
|---|---|
| `web_search`, `read_webpage` | Your search and page-fetch tools. Without them, label current facts as unverified. |
| `check_color_contrast` | `python scripts/contrast.py "#111827" "#ffffff"` (WCAG ratio, AA/AAA verdict) |
| `validate_sql_schema` | `python scripts/sql_check.py schema.sql` or pipe SQL on stdin (syntax and foreign keys, in memory only) |
| `security_checklist` | Read `references/security-checklist.md` |

## Honesty rules

- Mark anything time-sensitive (versions, prices, free-tier limits, standards) as verified, from memory, or needs check.
- A script that did not run is "not checked", never "passed".
- Prefer the simple option that fits the user's size and level; say why a heavier option is not needed.
- Do not pad. Skip an advisor rather than invent advice.
