# Working on this repository

For people and AI assistants contributing here.

## If you are an AI assistant asked to *use* this project
The skill is `skill/SKILL.md`. Read it and follow it. To install it, follow `INSTALL.md`.

## Rules for changes
- **Prompts live in `skill/references/` only.** Do not hardcode agent text in `app/office/*.py`. After changing anything under `skill/`, run `python scripts/build_prompt.py` (never edit `PROMPT.md` by hand).
- Keep `skill/SKILL.md` compact (about 5 KB; doctor warns above 12 KB). Details belong in `references/`, loaded only when needed.
- `skill/scripts/` use the Python standard library only, so they run anywhere.
- Time-sensitive facts (standards, prices, versions, free-tier limits) must say "verify before use" or name their edition.
- Never commit `.env`, keys, or real project data.
- A new advisor needs: its file in `skill/references/advisors/` with every front-matter field, and a row in the SKILL.md routing table.

## Before you open a pull request
```
python scripts/doctor.py
python -m unittest discover -s tests
python -m compileall -q app scripts skill/scripts
```
Include the output, and say what you could not check.
