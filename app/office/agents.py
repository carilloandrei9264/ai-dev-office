"""The agents: core team (researcher, writer, dispatcher, reviewer) and the specialist advisors.

Their roles, goals, backstories and focus areas live in skill/references/ (shared with the installable skill).
To change what an agent says or add an advisor, edit those Markdown files, not this file.
"""
from crewai import Agent, LLM

from .skill_loader import load_advisors, load_roles
from .tools import (
    check_color_contrast,
    read_webpage,
    security_checklist,
    validate_sql_schema,
    web_search,
)

# Tool names used in the Markdown files -> the actual tool objects
TOOLBOX = {
    "web_search": web_search,
    "read_webpage": read_webpage,
    "check_color_contrast": check_color_contrast,
    "validate_sql_schema": validate_sql_schema,
    "security_checklist": security_checklist,
}


def _tools(names: list) -> list:
    unknown = [n for n in names if n not in TOOLBOX]
    if unknown:
        raise ValueError(f"Unknown tool(s) in skill files: {', '.join(unknown)}")
    return [TOOLBOX[n] for n in names]


_ROLES = load_roles()

AGENT_SPECS = {
    key: dict(role=r["role"], goal=r["goal"], backstory=r["backstory"]) for key, r in _ROLES.items()
}

# Tools for the core agents (only the researcher needs the web)
CORE_TOOLS = {key: _tools(r["tools"]) for key, r in _ROLES.items()}

# The specialist advisors. They read the draft plan and give suggestions;
# the Reviewer merges the useful ones into the final plan.
SPECIALISTS = {
    key: {**spec, "tools": _tools(spec["tools"])} for key, spec in load_advisors().items()
}


def make_agent(spec: dict, llm: LLM, tools=None) -> Agent:
    return Agent(
        role=spec["role"],
        goal=spec["goal"],
        backstory=spec["backstory"],
        llm=llm,
        tools=tools or [],
        verbose=False,
        allow_delegation=False,
        max_iter=6,  # keeps tool-using agents from looping for too long
    )
