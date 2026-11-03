# Build mode

Build one small, verified slice at a time. State lives in `.ai-dev-office/` (PROJECT.md and STATUS.md), managed with `ctx`, so you never re-derive it.

## 1. Before code

- Project already has `.ai-dev-office/`: `ctx resume`, then continue. Do not re-plan.
- The user named a stack, or `ctx stack` detects one: read its notes once (`references/stacks/`: `laravel`, `node`, `nextjs`, `django`, `static`) and apply them. Do not swap the stack. For any other stack, read the official quickstart, work out the run, test and lint commands, and mark what you could not verify.
- New project: needs `PLAN.md` (from plan mode or the Dev Office app). Without a plan, a task bigger than a small change gets a compact plan first (`references/workflows/plan.md`), or ask the user.
- `ctx init --from-plan PLAN.md` creates PROJECT.md and STATUS.md and turns the plan's implementation steps into slices. Write each slice's acceptance sentence from the plan's requirements (`ctx set N todo --acceptance "..."`); a slice cannot start without one. Run `ctx stack <id>` to fill PROJECT.md `Stack` and `Commands` from the stack notes (or edit them by hand for other stacks). Then `ctx phase build`; if a gate fails, fix what it names instead of forcing it.
- Existing code with no memory yet: `ctx init`, then `ctx map`, then read only entry points and config to fill `Stack` and `Commands`.

## 2. The slice loop

A slice is one user-visible outcome through every layer it needs (UI, API, data), small enough to finish and verify in one sitting.

1. Take the next slice from `ctx status`, then `ctx set N building`. For a first slice that needs scaffolding or a test runner, do that first, run the checks once, and record it.
2. Route (section 3): load the fewest helper skills.
3. If behavior changes, write a test that fails first, then the smallest change that passes it.
4. Run the checks from PROJECT.md `Commands`, with output capped.
5. Verify the real flow by running it, including a denied, an invalid and a failure case. A rendered control, a mock response or a success toast is not proof. For anything people look at, also meet the definition of done in `references/web-quality.md`.
6. `ctx set N verified --evidence "<command and result, or what you did and saw>"`. If you could not verify: `ctx set N built --evidence "not verified: <why>"`.
7. If files or structure changed, run `ctx map`. Record durable decisions in PROJECT.md `Decisions`.
8. Report in five lines or fewer: what changed, evidence, what is unverified, next slice.

When every slice is built, `ctx phase verify`; when all are verified, `ctx phase release` and continue in `ship.md`. Commit only when the user asks.

## 3. Route each task to the fewest skills

Use a skill only if it is installed (`references/fallbacks.md` otherwise). Rows combine for mixed work. Load at most one primary skill plus specialists for concrete gaps; no automatic agent fan-out.

| Task | Load | Do not load |
|---|---|---|
| Typo, label, config, copy supplied word for word | nothing | everything |
| Bug or failing test | `systematic-debugging`; `webapp-testing` to reproduce a UI bug | design skills |
| New feature in an existing project | `ponytail`; `test-driven-development` when behavior changes | a new design direction |
| Execute a written plan | `executing-plans` | re-planning |
| Independent tasks and the host can run subagents | `subagent-driven-development` or `dispatching-parallel-agents`, only if the user agrees | agents for small tasks |
| Review changes, or review feedback arrives | `requesting-code-review`, `receiving-code-review` | |
| Risky experiment, or wrapping up a branch | `using-git-worktrees`, `finishing-a-development-branch` | |
| About to say "done" | `verification-before-completion` | |
| New landing page, marketing page, portfolio | `design-taste-frontend`, then `impeccable` once at the end | `frontend-design` |
| App screens, dashboard, admin | `frontend-design`; `ui-ux-pro-max` for narrow lookups | `design-taste-frontend` |
| Component states, gestures, motion | `emil-design-eng` | a full redesign |
| Before launching UI | `break-ui` on main screens, `mobile-native` | |
| Click through a flow, screenshots, console errors | `webapp-testing` | |
| Slow pages, Core Web Vitals | `performance`, `core-web-vitals` | guesses without a measurement |
| Search and AI-answer visibility | `seo-aeo-best-practices` | design skills |
| Copy that sounds AI-written | `humanizer`, keeping the user's facts | design skills |
| API design | `api-design-principles` | design skills |
| Security review | `security-best-practices` and `references/security-checklist.md` | design skills |
| Postgres tables, queries, migrations, RLS | `supabase-postgres-best-practices` | |
| User asks for short replies | `caveman` | |

Alternatives on request: `prototype` for several rendered versions of a UI, `pick-ui-library` before hand-building a complex widget. Both only when asked.

## 4. Fixing a bug

Reproduce it first. Find the cause with evidence (a log, a failing assertion, a minimal case), not a guess. Make the smallest fix, add a regression test that fails without it, run the checks, then record it like any slice. If two attempts fail, stop and reassess.

## 5. Rules while building

- Reuse the project's existing patterns and tools. Add a dependency, service or abstraction only for a concrete need, and say why in the report. Ask first if it costs money, needs an account, or has an unclear license.
- Static sites get no invented backend. Systems with accounts or money need server-side validation and authorization before the feature counts as done.
- One design direction per project. Reuse the accepted one for new pages. After adding or moving UI, rerun the project's layout checks.
- Keep `PROJECT.md` `Decisions` to the non-obvious choices (date, decision, why), newest first.
- When the project uses a platform with an official agent skill from its publisher (for example Stripe, Shopify, WordPress, Laravel, Prisma, Supabase), mention it once and install only if the user agrees.
- `ctx check` before ending a long session. Fix what it reports.
