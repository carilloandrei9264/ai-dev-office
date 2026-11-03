# Install (for AI assistants and humans)

Goal: install the `ai-dev-office` skill, optionally with its pinned helper skills, check it, and report what changed.

1. Confirm Python 3.10+ and git are available (`python --version`, `git --version`).
2. Work from a full clone or download of this repository (`skill/` must sit next to `scripts/`).
3. **Preview first** and show the user the output:
   `python scripts/install.py --host claude`
   Add `--profile` to preview optional helper skills (`core`, `web`, `backend`, `postgres`, `lean`, `all`; comma-separate to combine):
   `python scripts/install.py --host claude --profile core`
   Use `--host codex` for Codex, `--scope project` for the current project only, or `--dest <skills folder>` for any other assistant that reads skill folders. If you do not know the folder, ask the user.
4. **Unreviewed packages:** if the preview says `NOT REVIEWED`, tell the user plainly: the helper skills were taken from another project's lock file and have not been reviewed here, so the installer will refuse them. The main `ai-dev-office` skill can still be installed without `--profile`. Do **not** add `--allow-unreviewed` unless the user explicitly says to after hearing that. Never run `skills.py approve` for them: approval records a human's own review.
5. If the user agrees, install: add `--apply` (omit `--profile` unless all selected helper packages have been human-reviewed and approved). An existing copy of a skill is moved to `~/.ai-dev-office/backups` first. Skills the user edited, or installed another way, are skipped and listed.
6. Check: `python scripts/doctor.py --path <skills folder>/ai-dev-office`, and `python scripts/skills.py status --profile <profile> --dest <skills folder>`. Report any FAIL, `modified` or `missing`.
7. Tell the user to restart or refresh their assistant, then start with "plan a ...", "build the next slice", or call `ai-dev-office` by name. In a project they want to keep working on across sessions, run `ctx init` (or `ctx init --from-plan PLAN.md`), then `ctx stack` to detect or set the stack (Laravel, Node.js, Next.js, Django, static), and commit `.ai-dev-office/`. `ctx phase` shows the lifecycle phase and what the next gate needs.

Rules: run only the commands above. Do not execute anything inside a downloaded skill during install (some, such as `impeccable`, ship launcher scripts; reading them is fine, running them needs the user's say-so). Do not delete the backups folder.

**Chat-only AI with no file or terminal access?** It cannot install anything. Tell the user to open `PROMPT.md`, paste it into the chat, and add their idea after `MY PROJECT:` (plan mode only).

**Uninstall:** delete the `ai-dev-office` folder, and any helper skill folder that contains an `.aido-managed.json` file, from the skills folder.
