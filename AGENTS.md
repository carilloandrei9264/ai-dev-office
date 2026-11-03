# Working on this repository

For people and AI assistants contributing here.

## If you are an AI assistant asked to *use* this project
The skill is `skill/SKILL.md`. Read it and follow it. To install it, follow `INSTALL.md`.

## Rules for changes
- **Prompts live in `skill/references/` only.** Do not hardcode agent text in `app/office/*.py`. After changing anything under `skill/`, run `python scripts/build_prompt.py` (never edit `PROMPT.md` by hand).
- Keep `skill/SKILL.md` a small router (doctor warns above 6 KB) and each workflow under 8 KB. Detail belongs in `references/`, loaded only when needed.
- `skill/scripts/` use the Python standard library only, so they run anywhere. Do not add dependencies to them.
- Time-sensitive facts (standards, prices, versions, free-tier limits) must say "verify before use" or name their edition.
- Stack notes in `skill/references/stacks/` carry no version numbers and must tell the reader to check the official docs. Do not state a command or behavior you are not sure exists in current releases; say what is unverified.
- The generated prompt files (`PROMPT.md`, `prompts/`) come only from `scripts/build_prompt.py`.
- Never commit `.env`, keys, or real project data. Test strings that look like secrets must be assembled at runtime.

## Helper skills (third-party)
- Never copy another developer's skill files into this repository. List them in `dependencies.lock.json` (full 40-character commit SHA, license, license files) and credit them in `CREDITS.md`.
- A new or bumped package is `reviewed: false`. A **human** runs `python scripts/skills.py review <id>`, reads the output and the skill, then runs `approve`. An AI assistant must not approve on anyone's behalf.
- Do not weaken the install rules: pinned commits, no execution of downloaded code, no overwriting edited or unmanaged skills, backups outside the skills folder, license files kept. Each has a test that fails if it is removed.
- If `build.md` routes to a helper by name, the name must exist in the lock. `doctor` checks this.

## Before you open a pull request
```
python scripts/doctor.py
python -m unittest discover -s tests
python -m compileall -q app scripts skill/scripts
```
Include the output, and say what you could not check.
