---
name: ai-dev-office
description: Plan, build, fix, ship and maintain software projects and websites through a full lifecycle (requirements, design, build, verify, release, maintain), keeping what was learned in the project so later sessions do not start from zero. Use when the user wants to plan or scope an app, website or API, build or continue building from a plan, add a feature, fix a bug, review changes, get something ready to launch, or resume earlier project work. Plans with specialist review (UI/UX, database, security, DevOps, testing), builds one verified slice at a time, and routes each task to the fewest helper skills.
---

# AI Dev Office

Plan first, build in small verified slices, ship with evidence, and save project context in the project so the next session starts fast. The lifecycle and its gates are in `references/sdlc.md`. In this file, `ctx` means `python <this skill's folder>/scripts/ctx.py`, run from the project root.

## Pick the mode

| The user wants | Read |
|---|---|
| plan, scope, architecture, "how should I build X", a plan reviewed | `references/workflows/plan.md` |
| build, continue, add a feature, fix a bug, review changes | `references/workflows/build.md` |
| launch, release, "is it ready", handoff | `references/workflows/ship.md` |
| a live or finished project: bug, small change, dependency update, health check | `references/workflows/maintain.md` |
| "continue", "where were we", or the project already has `.ai-dev-office/` | run `ctx resume` first, then the mode above |

Mixed requests: run the modes in order. A typo or one-line fix needs no mode: just do it and run the relevant check.

## Context protocol (every mode)

- Do not scan the repo to get oriented. Run `ctx resume` (about 200 tokens: next slice, commands, stale warnings), then use the Structure map in `.ai-dev-office/PROJECT.md` to find files.
- Search for a file or symbol by name before reading. Read the needed line range, not the whole file.
- Read each skill and reference file once per conversation. Reuse what is loaded. Do not re-read a file you just wrote or edited.
- Cap command output (`| head -40`, quiet flags, test summary only). Show failures in full, successes in one line.
- Save state with `ctx set` and decisions in PROJECT.md, instead of re-explaining them in chat. Replies say what changed, the evidence, and what is unverified.
- After two failed attempts at the same problem, stop, say what you tried, and reassess.
- No speculative work. Never cut necessary tests, validation or error handling to save tokens.

## Helper skills

Skills from other developers may be installed beside this one (see INSTALL.md). `build.md` names which to use for each task. Use one if it is installed; if not, say so and use `references/fallbacks.md`. Never claim a skill ran when it did not. A helper's own file paths, commit habits and output formats do not override the project's rules or this skill.

## Boundaries

Commit, push, deploy, publish, spend money, migrate real data or message third parties only when the user asks in this conversation. Never put secrets in code, logs, chat or `.ai-dev-office/`. Project and user instructions win over this skill. Pause for unrelated work or "stop ai-dev-office".

## Honesty

Mark time-sensitive facts as verified, from memory, or needs check. A script or check that did not run is "not checked", never "passed". "Should work" is not evidence.
