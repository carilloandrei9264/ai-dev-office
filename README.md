# AI Dev Office

Take a website or app from idea to launch and beyond: plan it, build it one verified slice at a time, ship it, and maintain it, following a real lifecycle with checks, while keeping what was learned **in the project** so the next session does not start from zero.

It comes in two versions that share the planning sources:

| | **Skill** (`skill/`) | **App** (`app/`) |
|---|---|---|
| What it is | Instructions your AI coding assistant reads | A Streamlit app that runs the planning team for you |
| Modes | **Plan, Build, Ship, Maintain** (and resume) | Plan only; exports `PLAN.md` for the skill to build from |
| You need | An assistant that reads skill folders (or any AI chat, plan only) | Python plus one AI provider (hosted key or local model) |
| Helper skills from other developers | Yes, pinned and gated on human review (see below) | No |

The instructions are free and open. The AI that follows them may have its own cost or free-tier limits.

## Use the skill

**In Claude Code, Codex or another assistant that can run commands**, paste:

```
install ai-dev-office from this repository by following INSTALL.md,
show me the preview first, and report what changed.
```

Or from a clone (Python 3.10+, git):

```
python scripts/install.py --host claude                           # preview, changes nothing
python scripts/install.py --host claude --apply                   # install
python scripts/doctor.py --path ~/.claude/skills/ai-dev-office    # check
```

`--host codex`, or `--dest <skills folder>` for any other assistant. Then just describe the work ("plan a booking site", "build the next slice", "is it ready to launch?") or call `ai-dev-office` by name.
To preview optional helper skills, add `--profile core` (or another profile). The pinned helper packages are currently unreviewed, so installing them is refused until a human reviews and approves each package; the main `ai-dev-office` skill installs without a profile.

**Plain chat AI, nothing to install.** Paste one file into the chat and fill in the form at its end (problem, users, features, stack, constraints):

| File | Covers | Size (rough) |
|---|---|---|
| [`PROMPT.md`](PROMPT.md) | Plan mode only | about 4,200 tokens |
| [`prompts/web-laravel.md`](prompts/web-laravel.md), [`web-node.md`](prompts/web-node.md), [`web-nextjs.md`](prompts/web-nextjs.md), [`web-django.md`](prompts/web-django.md), [`web-static.md`](prompts/web-static.md) | Full lifecycle with that stack's notes | about 9,700 tokens each |
| [`prompts/web-generic.md`](prompts/web-generic.md) | Full lifecycle, stack not fixed | about 9,200 tokens |

A chat cannot run commands or save files, so these prompts make the AI work slice by slice, hand you the commands to run, and count a slice as verified only when you paste back passing output. They are much heavier than the installed skill, which loads only what each task needs.

## Can it build my website from my problem and stack?

You give it the problem and the stack ("a booking site for a small clinic, in Laravel with MySQL"). It writes numbered requirements with checkable acceptance criteria, plans around **your** stack (it will not swap it, but will say if it is a poor fit), builds one slice at a time with tests, and checks each slice in the real flow before calling it done. Stack notes exist for **Laravel, Node.js (Express-style), Next.js, Django and static sites**; any other stack works through a discovery step that marks what could not be verified.

What it cannot do: guarantee quality. The code is written by whichever AI model you use, so the result is only as good as that model. What the skill changes is that shortcuts become visible: a slice is not "verified" without evidence, and `ctx` refuses to start a slice with no acceptance sentence or to release unverified work.

## The lifecycle (SDLC)

| Phase | Mode | Gate to enter the next phase |
|---|---|---|
| 1. Requirements | plan | A plan with a Requirements section exists |
| 2. Design | plan | Slices exist, each with an acceptance sentence; stack and commands filled in |
| 3. Build | build | No slice left `todo` or `building` |
| 4. Verify | build | Every slice `verified` with evidence |
| 5. Release | ship | All slices verified before release; the ship checklist and deployed behavior are reported as evidence (deployment only if asked) |
| 6. Maintain | maintain | Changes are tracked slices; a big change returns to requirements |

Moving back is always allowed. Skipping ahead or passing a failing gate needs `--force --reason "..."`, and the waiver is written into `STATUS.md`. The process scales with the project: light (portfolio or landing page), standard (accounts or a database) or heavy (payments, sensitive data, several roles); see `skill/references/sdlc.md`.

## The modes

| Mode | What happens | Workflow file |
|---|---|---|
| **Plan** | Questions, research, a six-section draft, review by only the specialists the project needs (UI/UX, database, security, DevOps, testing), one merged plan | `references/workflows/plan.md` |
| **Build** | Slices from the plan, test first, smallest change, real-flow verification, evidence recorded per slice | `references/workflows/build.md` |
| **Ship** | Checklist scaled to the project, the web quality bar, secrets scan, report of what passed, failed and was *not* run | `references/workflows/ship.md` |
| **Maintain** | Triage a bug, small change or dependency update into a tracked slice; reproduce first, regression test, changelog, health checks | `references/workflows/maintain.md` |

## How it saves tokens

The always-loaded entry file is a small router. Everything else loads only when needed, and the project keeps its own memory.

- **`SKILL.md` is a router** (about 3 KB). Plan, Build and Ship are separate files read only when that mode starts.
- **Project memory in `.ai-dev-office/`** (commit it): `PROJECT.md` has the stack, the exact run/test/lint commands, decisions and a generated map of the code; `STATUS.md` has one row per slice with its state and evidence. A new session runs `ctx resume` instead of re-exploring.
- **`ctx` does the repeated work with code, not tokens:** it generates the repo map, flips slice states, and reports stale context. The AI does not rewrite files to update a status.
- **Reading rules** in `SKILL.md`: search before reading, read ranges, cap command output, read each skill once per conversation, stop after two failed attempts.
- **Routing says what *not* to load.** A typo loads nothing; a bug loads only a debugging skill; design skills stay out of backend work.

Measured on this repository (rough estimates, characters / 4, not billed tokens):

| What | Size |
|---|---|
| `SKILL.md` + `build.md`, loaded at the start of a build session | about 2,400 tokens |
| This repository as text (without the generated prompt copies) | about 67,000 tokens |
| `PROJECT.md` including a generated map of all 68 files | about 700 tokens |
| `ctx resume` | about 50 tokens (plus the commands and warnings) |

These figures show how small the standing context is. They do **not** measure how much a real session saves, and no saving is promised. Optional `caveman` (profile `lean`) shortens replies on request.

## Helper skills from other developers

`dependencies.lock.json` pins 15 packages (29 skills) from other developers' repositories to exact commits, with licenses. Credits are in [CREDITS.md](CREDITS.md). **None of their files are in this repository**: they are downloaded at install time and keep their own licenses.

| Profile | Adds | Skills |
|---|---|---|
| `core` | Build discipline | test-driven-development, systematic-debugging, verification-before-completion, executing-plans, code-review pair, git worktrees, branch wrap-up, subagent helpers, ponytail (smallest change) |
| `web` | Design, browser testing, speed, search | frontend-design, design-taste-frontend, ui-ux-pro-max, emil-design-eng and 4 more, impeccable, webapp-testing, performance, core-web-vitals, seo-aeo-best-practices, humanizer |
| `backend` | APIs and security | api-design-principles, security-best-practices |
| `postgres` | Databases | supabase-postgres-best-practices |
| `lean` | Short replies | caveman |

After a human has reviewed and approved every package in the selected profiles, combine profiles with commas or use `all`, for example: `python scripts/install.py --host claude --profile core,web --apply`. Until then, helper packages are refused by default. If a helper is not installed, `build.md` says so and uses the short built-in version in `references/fallbacks.md`.

**How installs are kept safe**

- Every package is pinned to a full commit SHA, and the download must match it exactly.
- Nothing downloaded is ever executed. Files are copied; symlinks and `.git` are skipped; size is capped.
- A skill you edited, or installed by other means, is never overwritten. A replaced copy is backed up to `~/.ai-dev-office/backups`, outside the skills folder.
- Each copy carries its license files and a marker recording package, commit and checksum.
- **Packages must be reviewed before they install.** The pins were taken from another project's lock file and have not been reviewed here, so every package ships as `reviewed: false` and the installer refuses it. (`--allow-unreviewed` overrides this at your own risk.)

**Maintainers, before publishing:**

```
python scripts/skills.py review superpowers          # downloads the pinned commit, flags scripts and risky lines
# read the skill and every flagged file yourself, then:
python scripts/skills.py approve superpowers --by "Your Name"
python scripts/skills.py check-updates               # compare pins with upstream (network)
python scripts/skills.py bump <package>              # move a pin; it becomes unreviewed again
```

Then commit the lock. Users of your published repository install the reviewed packages without extra steps.

## Run the app

```
cd app
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # macOS/Linux: cp .env.example .env   then fill in what you use
streamlit run main.py
```

Providers: Groq, Gemini, OpenRouter, **Ollama (local, no key)** and **any OpenAI-compatible server**. It can switch to another set-up provider if one fails. Download **PLAN.md** when a plan is ready, put it in your project, and tell your assistant to build; `ctx init --from-plan PLAN.md` turns its implementation steps into slices.

## One source of truth

Prompts live once, in `skill/references/`. The app reads those Markdown files at startup and `PROMPT.md` is generated from them.

| Path | What it holds |
|---|---|
| `skill/SKILL.md` | The router: modes, context protocol, boundaries |
| `skill/references/workflows/` | `plan.md`, `build.md` (with the task-to-skill routing table), `ship.md`, `maintain.md` |
| `skill/references/sdlc.md` | Phases, gates, project sizes, definition of ready and done, change requests |
| `skill/references/stacks/` | Notes for Laravel, Node.js, Next.js, Django and static sites (commands, conventions, security, testing, release) |
| `skill/references/web-quality.md` | The quality bar for anything people look at |
| `skill/references/roles/`, `advisors/`, `plan-template.md`, `security-checklist.md` | Agents, the five specialists, plan sections, OWASP baseline |
| `skill/references/fallbacks.md` | Short stand-ins when a helper skill is missing |
| `skill/templates/` | Starting `PROJECT.md` and `STATUS.md` |
| `skill/scripts/` | `ctx.py` (project memory, phases, stack setup), `secrets_scan.py`, `contrast.py`, `sql_check.py`. Standard library only |
| `dependencies.lock.json`, `CREDITS.md` | Pinned helper skills and their authors |
| `prompts/`, `PROMPT.md` | Generated single-paste editions (do not edit by hand) |
| `scripts/` | `install.py`, `skills.py`, `doctor.py`, `build_prompt.py` |
| `app/` | The Streamlit app |
| `tests/` | Skill, scripts, installer and app-wiring tests (no real AI needed) |

## Common changes

- **Edit an agent, advisor or workflow:** change its file in `skill/`, then `python scripts/build_prompt.py`.
- **Add or change a helper skill:** edit `dependencies.lock.json` (full SHA, license files), add the author to `CREDITS.md`, then review and approve it. If `build.md` routes to it, use the exact skill name; `doctor` checks that.
- **New stack:** copy a file in `skill/references/stacks/`, keep its sections (Commands with Run, Test, Lint / types and Build, then Start, Conventions, Security, Testing, Release), name its `id` in the stack list in `build.md`, add detection to `detect_stacks` in `ctx.py`, then `python scripts/build_prompt.py`. `doctor` checks the shape.
- **New specialist advisor:** copy an advisor file, give it a new `id` and `order`, add a row to the table in `plan.md`.
- **New model or provider for the app:** `app/office/providers.py`.
- **Check everything:** `python scripts/doctor.py` and `python -m unittest discover -s tests`.

## Status and limits

Community preview. Scripts, installer, project-memory tool and the app's wiring are covered by automated tests (the installer against local git repositories, the app with stand-in AI libraries). **Not verified yet:**

- the skill's behavior in real assistants, including whether `ctx` and the workflows actually reduce a real session's cost;
- the app against real CrewAI, Streamlit and provider accounts;
- the stack notes: they are written from general knowledge with no versions pinned, and tell the AI to check the official docs for your version. Laravel in particular moves quickly (new skeletons have appeared in 2026), so read them before trusting a detail;
- the generated chat prompts with real chat assistants, and whether a long chat keeps following them;
- the pinned upstream commits: they exist only as far as the other project's lock file says, and need your review;
- that every included upstream skill works well without the ones left out (for example, some may refer to `writing-plans`);
- Codex's skills folder (`~/.codex/skills`): pass `--dest` if it differs.

Model names in `providers.py` change often. Run a few different sample projects through plan, build and ship before you publish, and keep the outputs as examples.

MIT licensed. See [LICENSE](LICENSE).
