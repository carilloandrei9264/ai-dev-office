"""The planning pipeline: Researcher -> Writer -> Dispatcher -> Specialists -> Reviewer."""
import time
from datetime import datetime

from crewai import Agent, Crew, Process, Task

from .agents import AGENT_SPECS, CORE_TOOLS, SPECIALISTS, make_agent
from .pdf_export import create_pdf
from .providers import build_llm
from .skill_loader import plan_sections
from .router import build_routing_prompt, keyword_routing, parse_routing

def run_stage(agent: Agent, description: str, expected_output: str) -> str:
    """Run a single agent task in its own crew so the UI can show real progress."""
    task = Task(description=description, expected_output=expected_output, agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    return str(crew.kickoff())



DETAIL_HINTS = {
    "Concise": "Keep each section short and to the point.",
    "Standard": "Give a balanced level of detail.",
    "Detailed": "Be thorough: include specifics, examples, and concrete recommendations in every section.",
}


def _short(err: Exception, n: int = 90) -> str:
    return str(err).replace("\n", " ")[:n]


def run_stage_with_fallback(spec, tools, description, expected_output, candidates, temperature, status):
    """Try each candidate provider in order. Returns (text, candidate_used)."""
    last_error = None
    for i, cand in enumerate(candidates):
        try:
            llm = build_llm(cand["provider"], cand["model"], temperature, cand["key"], cand.get("base_url"))
            text = run_stage(make_agent(spec, llm, tools), description, expected_output)
            if i:  # stick with the provider that worked for the next stages
                candidates.insert(0, candidates.pop(i))
            return text, cand
        except Exception as e:  # noqa: BLE001
            last_error = e
            if i + 1 < len(candidates):
                status.write(f"⚠️ {cand['provider']} failed ({_short(e)}…). Switching to {candidates[i + 1]['provider']}…")
    raise last_error



def run_pipeline(project, candidates, temperature, level, stack_pref, detail, advisors, max_advisors, use_tools, status) -> dict:
    started = time.time()
    used = []

    sections = plan_sections()  # from skill/references/plan-template.md
    sections_text = "\n".join(f"{i}. {name}" for i, name in enumerate(sections, 1))

    prefs = (
        f"Target developer experience level: {level}.\n"
        f"{('Preferred stack/constraints: ' + stack_pref + chr(10)) if stack_pref.strip() else ''}"
        f"{DETAIL_HINTS[detail]}\n"
    )

    def stage(spec, tools, description, expected):
        text, cand = run_stage_with_fallback(
            spec, tools if use_tools else [], description, expected, candidates, temperature, status
        )
        label = f"{cand['provider']} ({cand['model']})"
        if label not in used:
            used.append(label)
        return text

    # 1) Research
    status.update(label="🔎 Researcher is investigating...")
    research = stage(
        AGENT_SPECS["researcher"],
        CORE_TOOLS["researcher"],
        (
            f"Research the best way to build this project: {project}\n\n{prefs}\n"
            "Focus on:\n"
            "- Recommended tech stack (frontend, backend, database, hosting)\n"
            "- Architecture recommendations\n"
            "- Key features and how to implement them\n"
            "- Potential challenges and how to solve them\n"
            "- Current best practices\n"
            "Use your search tools only when they help verify current information, and keep tool calls few."
        ),
        "A detailed research summary with recommended technologies and architecture.",
    )
    status.write("✅ Research complete")

    # 2) Draft
    status.update(label="📝 Writer is drafting the plan...")
    draft = stage(
        AGENT_SPECS["writer"],
        CORE_TOOLS["writer"],
        (
            f"Using the research below, create a clear and structured Project Plan for: {project}\n\n{prefs}\n"
            "Include these sections (use Markdown headings):\n"
            f"{sections_text}\n\n"
            f"RESEARCH:\n{research}"
        ),
        "A well-structured technical project plan in Markdown.",
    )
    status.write("✅ Draft complete")

    # 3) Specialist advisors: each reads the draft and gives suggestions
    # 3a) Dispatcher: decide which specialists are needed (auto mode)
    if advisors is None:
        status.update(label="🧭 Dispatcher is choosing specialists...")
        routing = {}
        try:
            routing_text = stage(
                AGENT_SPECS["router"],
                [],
                build_routing_prompt(project, prefs, draft, max_advisors),
                "A JSON object listing the chosen specialists with a short reason each.",
            )
            routing = parse_routing(routing_text, max_advisors)
        except Exception as e:  # noqa: BLE001
            status.write(f"⚠️ Dispatcher failed ({_short(e)}…). Using keyword matching instead.")
        if not routing:
            routing = keyword_routing(f"{project} {stack_pref}", max_advisors)
        advisors = list(routing)
        status.write("🧭 Specialists chosen: " + ", ".join(SPECIALISTS[k]["label"] for k in advisors))
    else:
        routing = {k: "Selected by you" for k in advisors}

    # 3b) Specialist advisors: each reads the draft and gives suggestions
    advice = {}
    for key in advisors:
        spec = SPECIALISTS[key]
        status.update(label=f"{spec['label']} is reviewing the draft...")
        try:
            advice[key] = stage(
                spec,
                spec["tools"],
                (
                    f"You are advising on a software project: {project}\n\n{prefs}\n"
                    f"Read the draft plan below and give 4-6 concrete, prioritized suggestions from your area of expertise: "
                    f"{spec['focus']}\n\n"
                    "Rules:\n"
                    "- Be specific to this project; no generic filler.\n"
                    "- Use your tools only when they genuinely help, and keep tool calls few.\n"
                    "- Maximum about 200 words, as a Markdown bullet list.\n\n"
                    f"DRAFT PLAN:\n{draft[:6000]}"
                ),
                "A short prioritized Markdown bullet list of suggestions.",
            )
            status.write(f"✅ {spec['label']} done")
        except Exception as e:  # noqa: BLE001  (one failing advisor should not stop the whole plan)
            status.write(f"⚠️ {spec['label']} skipped ({_short(e)}…)")

    # 4) Review: merge draft + advice into the final plan
    status.update(label="🧐 Reviewer is polishing...")
    if advice:
        advice_block = "\n\n".join(f"### {SPECIALISTS[k]['label']}\n{t}" for k, t in advice.items())
        sections = ", ".join(f"'{SPECIALISTS[k]['section']}'" for k in advice)
        advice_rules = (
            "- Merge the specialist suggestions below into the plan. Keep the useful ones, drop generic ones, "
            "and resolve any conflicts between them.\n"
            f"- Add a dedicated section for each consulted area: {sections}.\n"
        )
        advice_text = f"\n\nSPECIALIST SUGGESTIONS:\n{advice_block}"
    else:
        advice_rules, advice_text = "", ""

    final = stage(
        AGENT_SPECS["reviewer"],
        CORE_TOOLS["reviewer"],
        (
            f"Review the project plan below for: {project}\n\n"
            "Check for missing details, technical risks, security issues, and clarity. "
            "Then output the improved FINAL plan.\n\n"
            "Rules:\n"
            "- Return ONLY the final plan in clean Markdown, with no preamble.\n"
            f"- Keep the original {len(sections)} sections.\n"
            f"{advice_rules}"
            "- End with a '## Review Notes' section: bullet list of what you improved and any remaining risks.\n\n"
            f"PLAN:\n{draft}{advice_text}"
        ),
        "The improved final project plan in Markdown, ending with Review Notes.",
    )
    status.write("✅ Review complete")

    return {
        "project": project,
        "created": datetime.now().strftime("%b %d, %Y %H:%M"),
        "elapsed": time.time() - started,
        "model_label": " → ".join(used),
        "research": research,
        "draft": draft,
        "advice": advice,
        "routing": routing,
        "final": final,
        "pdf": create_pdf(final, project),
        "plan_md": make_plan_md(final, project),
    }


def make_plan_md(final: str, project: str) -> str:
    """The plan as a PLAN.md you can drop into a project folder for an AI coding assistant to build from."""
    stamp = datetime.now().strftime("%Y-%m-%d")
    return f"<!-- Generated by AI Dev Office on {stamp}. Project: {project.strip()[:120]} -->\n\n{final.strip()}\n"


def friendly_error(err: Exception) -> str:
    msg = str(err).lower()
    if "rate" in msg and "limit" in msg or "429" in msg:
        return "You hit the provider's rate limit. Wait a minute and try again, switch provider, or enable auto-switch in the sidebar."
    if "api key" in msg or "authentication" in msg or "401" in msg:
        return "The API key looks invalid. Check the key in your .env file."
    if "cache_breakpoint" in msg:
        return "The provider rejected a CrewAI internal field. Run: pip install -U crewai litellm"
    if any(w in msg for w in ("connection refused", "connecterror", "cannot connect", "failed to connect", "connection error")):
        return "Could not reach the model server. If you use Ollama or a custom server, make sure it is running and the Base URL in the sidebar is right."
    if "not found" in msg or "does not exist" in msg:
        return "The model name wasn't found. Check the Model field in the sidebar."
    return "The AI team ran into a problem. Details are below."
