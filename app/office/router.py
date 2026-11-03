"""Dispatcher helpers: decide which specialist advisors a project needs."""
import json
import re

from .agents import SPECIALISTS

# Built from the advisor files in skill/references/advisors/ (the `when` and `keywords` fields)
ROUTER_BLURBS = {k: v["when"] for k, v in SPECIALISTS.items()}
ROUTER_KEYWORDS = {k: v["keywords"] for k, v in SPECIALISTS.items()}  # used only if the dispatcher's answer is unusable


def build_routing_prompt(project: str, prefs: str, draft: str, max_n: int) -> str:
    options = "\n".join(f"- {k}: {v}" for k, v in ROUTER_BLURBS.items())
    return (
        f"Project: {project}\n{prefs}\n"
        f"Start of the draft plan:\n{draft[:1500]}\n\n"
        f"Available specialists:\n{options}\n\n"
        f"Pick ONLY the specialists this project truly needs: at least 1 and at most {max_n}. "
        "Prefer fewer. Skip any that would add little value.\n"
        'Respond with ONLY JSON like: {"advisors": [{"id": "db", "reason": "one short sentence"}]}'
    )


def parse_routing(text: str, max_n: int) -> dict:
    """Turn the dispatcher's answer into {specialist_id: reason}. Tolerates messy output."""
    picked = {}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            for item in json.loads(match.group(0)).get("advisors", []):
                key, why = (item.get("id") or item.get("advisor"), item.get("reason", "")) if isinstance(item, dict) else (item, "")
                key = str(key).strip().lower()
                if key in SPECIALISTS and key not in picked:
                    picked[key] = str(why)
        except Exception:  # noqa: BLE001
            pass
    if not picked:  # last resort: look for specialist ids mentioned anywhere in the text
        ids = "|".join(re.escape(k) for k in SPECIALISTS)
        for key in re.findall(rf"\b({ids})\b", text.lower()):
            picked.setdefault(key, "")
    return dict(list(picked.items())[:max_n])


def keyword_routing(text: str, max_n: int) -> dict:
    lowered = text.lower()
    scores = {k: sum(w in lowered for w in words) for k, words in ROUTER_KEYWORDS.items()}
    ranked = [k for k, s in sorted(scores.items(), key=lambda kv: -kv[1]) if s > 0][:max_n]
    if not ranked:
        ranked = [k for k in ("sec", "qa") if k in SPECIALISTS][:max_n] or list(SPECIALISTS)[:max_n]
    return {k: "Matched by keywords" for k in ranked}
