# Install (for AI assistants and humans)

Goal: install the `ai-dev-office` skill, check it, and report what changed.

1. Confirm Python 3.10+ is available (`python --version`).
2. Work from a full clone or download of this repository (the `skill/` folder must be next to `scripts/`).
3. Preview first, and show the user the output:
   `python scripts/install.py --host claude`
   Use `--host codex` for Codex, `--scope project` to install for the current project only, or `--dest <skills folder>` for any other assistant that reads skill folders. If you do not know the folder, ask the user.
4. If the user agrees, install: add `--apply`. An existing copy is moved to `ai-dev-office.bak-<time>` first and restored if the install fails.
5. Check it: `python scripts/doctor.py --path <install folder>/ai-dev-office`. Report any FAIL.
6. Tell the user to restart or refresh their assistant so it finds the skill, and that they can start with "plan a ..." or call `ai-dev-office` by name.

Rules: only run the commands above; never execute other files from the repository during install; do not delete the `.bak` folder yourself.

**Chat-only AI with no file or terminal access?** It cannot install anything. Tell the user to open `PROMPT.md`, paste it into the chat, and add their idea after `MY PROJECT:`.

**Uninstall:** delete the `ai-dev-office` folder from the skills folder.
