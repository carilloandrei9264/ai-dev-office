# AI Dev Office

Plan a software project the way a small team would, **before** any code is written: research, a structured draft, review by only the specialists the project needs (UI/UX, database, security, DevOps, testing), then one merged final plan with its open risks.

It comes in two versions that share the same prompts:

| | **Skill** (`skill/`) | **App** (`app/`) |
|---|---|---|
| What it is | Instructions your AI assistant reads | A Streamlit app that runs the team for you |
| You need | An assistant that reads skill folders, or any AI chat | Python, plus one AI provider (hosted key or a local model) |
| Runs | In your assistant, in one conversation | Locally, stage by stage, with a progress view and PDF export |
| Best for | Planning inside your normal workflow, then building from the plan | A guided form and downloadable plan without touching an assistant |

The instructions are free and open. The AI that follows them may have its own cost or free-tier limits.

## Use the skill

**In Claude Code, Codex or another assistant that can run commands**, paste:

```
install ai-dev-office from this repository by following INSTALL.md,
show me the preview first, and report what changed.
```

Or do it yourself from a clone (Python 3.10+):

```
python scripts/install.py --host claude            # preview, changes nothing
python scripts/install.py --host claude --apply    # install
python scripts/doctor.py --path ~/.claude/skills/ai-dev-office   # check
```

Use `--host codex`, or `--dest <skills folder>` for any other assistant. An existing copy is backed up first. Then describe a project, or call it by name.

**In a plain chat AI** (nothing to install): open [`PROMPT.md`](PROMPT.md), paste the whole file into the chat, and write your idea after `MY PROJECT:` at the bottom.

## Run the app

```
cd app
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # macOS/Linux: cp .env.example .env   then fill in what you use
streamlit run main.py
```

Providers: Groq, Gemini, OpenRouter, **Ollama (local, no key, no rate limits)** and **any OpenAI-compatible server** (LM Studio, vLLM, llama.cpp...). The app can switch to another set-up provider automatically if one fails. Small local models often struggle with tools; turn "Let agents use tools" off if a plan comes out broken.

When a plan is ready, download **PLAN.md** and drop it in your project folder so your AI coding assistant can build from it.

## One source of truth

Prompts live once, in `skill/references/`. The app reads those same Markdown files at startup, and `PROMPT.md` is generated from them. Improve a prompt there and all three improve.

| Path | What it holds |
|---|---|
| `skill/SKILL.md` | The compact workflow and advisor routing table |
| `skill/references/roles/` | Researcher, Writer, Dispatcher, Reviewer |
| `skill/references/advisors/` | The five specialists (UI/UX, DB, security, DevOps, QA) |
| `skill/references/plan-template.md` | The required plan sections |
| `skill/references/security-checklist.md` | OWASP baseline and per-project-type checks |
| `skill/scripts/` | Contrast and SQL checkers (standard library only), used by both versions |
| `scripts/install.py`, `doctor.py`, `build_prompt.py` | Installer, health check, PROMPT.md generator |
| `app/` | The Streamlit app (`main.py`, `office/`) |
| `tests/` | Skill, scripts and app-wiring tests (no real AI needed) |

## Common changes

- **Edit an agent or advisor:** change its file in `skill/references/`, then run `python scripts/build_prompt.py`.
- **New specialist advisor:** copy an advisor file, give it a new `id` and `order`, add a row to the routing table in `skill/SKILL.md`. The app picks it up automatically. `python scripts/doctor.py` tells you if something is missing.
- **New model for a provider, or a new provider:** `app/office/providers.py`.
- **New tool:** write it in `app/office/tools.py`, add its name to `TOOLBOX` in `agents.py`, and list it in the agent's `tools:` field.
- **Check everything:** `python scripts/doctor.py` and `python -m unittest discover -s tests`.

## Status and limits

Community preview. The scripts, installer, doctor and the app's wiring are covered by automated tests that use stand-in AI libraries. Two things have **not** been verified yet: the skill's behaviour across real assistants, and the app against real CrewAI, Streamlit and provider accounts. Model names in `providers.py` change often: check them against each provider's current list. Run three different sample projects through both versions before you publish, and keep the outputs as examples.

MIT licensed. See [LICENSE](LICENSE).
