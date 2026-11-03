"""Tests for the Streamlit app's non-UI code, using stand-ins for crewai/litellm/dotenv/fpdf so no AI is called.

They prove the wiring: prompts load from skill/, routing works, providers behave, the pipeline runs end to end
(including provider auto-switch) and PLAN.md is produced.
"""
import importlib
import json
import os
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
_STUBBED = ["crewai", "crewai.tools", "litellm", "dotenv", "fpdf"]
_saved = {}
LLM_CALLS = []


def _install_stubs():
    for name in _STUBBED + [m for m in list(sys.modules) if m == "office" or m.startswith("office.")]:
        _saved[name] = sys.modules.pop(name, None)

    crewai = types.ModuleType("crewai")

    class LLM:
        def __init__(self, **kw):
            self.kw = kw
            LLM_CALLS.append(kw)

    class Agent:
        def __init__(self, role, goal, backstory, llm, tools, **kw):
            self.role, self.goal, self.backstory, self.llm, self.tools = role, goal, backstory, llm, tools

    class Task:
        def __init__(self, description, expected_output, agent):
            self.description, self.agent = description, agent

    class Process:
        sequential = "sequential"

    class Crew:
        def __init__(self, agents, tasks, **kw):
            self.agent, self.task = agents[0], tasks[0]

        def kickoff(self):
            if getattr(self.agent.llm, "kw", {}).get("model", "").startswith("groq/") and FAIL_GROQ:
                raise RuntimeError("429 rate limit")
            if self.agent.role == "Project Dispatcher":
                return json.dumps({"advisors": [{"id": "db", "reason": "stores data"}, {"id": "sec", "reason": "has login"}]})
            return f"[{self.agent.role}] " + self.task.description[:40].replace("\n", " ")

    crewai.LLM, crewai.Agent, crewai.Task, crewai.Crew, crewai.Process = LLM, Agent, Task, Crew, Process
    tools = types.ModuleType("crewai.tools")

    def tool(name):
        def deco(fn):
            fn.tool_name = name
            return fn
        return deco

    tools.tool = tool
    crewai.tools = tools
    litellm = types.ModuleType("litellm")
    litellm.completion = lambda *a, **k: None
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *a, **k: None
    fpdf = types.ModuleType("fpdf")
    fpdf.FPDF = type("FPDF", (), {})
    for name, mod in [("crewai", crewai), ("crewai.tools", tools), ("litellm", litellm), ("dotenv", dotenv), ("fpdf", fpdf)]:
        sys.modules[name] = mod
    sys.path.insert(0, str(APP))


FAIL_GROQ = False


def setUpModule():
    _install_stubs()


def tearDownModule():
    sys.path.remove(str(APP))
    for name in [m for m in list(sys.modules) if m == "office" or m.startswith("office.")] + _STUBBED:
        sys.modules.pop(name, None)
    for name, mod in _saved.items():
        if mod is not None:
            sys.modules[name] = mod


class FakeStatus:
    def __init__(self):
        self.lines, self.labels = [], []

    def write(self, text):
        self.lines.append(text)

    def update(self, label=None, **kw):
        self.labels.append(label)


class LoaderAndAgents(unittest.TestCase):
    def test_advisors_load_in_order_with_all_fields(self):
        from office.agents import SPECIALISTS
        self.assertEqual(list(SPECIALISTS), ["ux", "db", "sec", "devops", "qa"])
        for spec in SPECIALISTS.values():
            for field in ("label", "section", "role", "goal", "backstory", "focus", "when"):
                self.assertTrue(spec[field], field)
            self.assertIsInstance(spec["tools"], list)
        self.assertEqual([t.tool_name for t in SPECIALISTS["ux"]["tools"]], ["web_search", "check_color_contrast"])

    def test_roles_and_core_tools(self):
        from office.agents import AGENT_SPECS, CORE_TOOLS
        self.assertEqual(set(AGENT_SPECS), {"researcher", "writer", "router", "reviewer"})
        self.assertEqual([t.tool_name for t in CORE_TOOLS["researcher"]], ["web_search", "read_webpage"])
        self.assertEqual(CORE_TOOLS["writer"], [])

    def test_plan_sections(self):
        from office.skill_loader import plan_sections
        sections = plan_sections()
        self.assertEqual(len(sections), 7)
        self.assertEqual(sections[:2], ["Project Overview", "Requirements & Acceptance Criteria"])


class Tools(unittest.TestCase):
    def test_wrappers_use_the_shared_scripts(self):
        from office import tools
        self.assertIn("17.74:1", tools.check_color_contrast("#111827", "#ffffff"))
        self.assertTrue(tools.validate_sql_schema("CREATE TABLE t(id INTEGER);").startswith("Valid SQL"))
        self.assertIn("Software Supply Chain", tools.security_checklist("api"))

    def test_private_hosts_are_blocked(self):
        from office import tools
        self.assertFalse(tools._is_public_host("localhost"))
        self.assertFalse(tools._is_public_host("127.0.0.1"))
        self.assertFalse(tools._is_public_host("169.254.169.254"))
        self.assertFalse(tools._is_public_host("0.0.0.0"))


class Router(unittest.TestCase):
    def test_parse_json(self):
        from office.router import parse_routing
        out = parse_routing('Sure! {"advisors": [{"id": "db", "reason": "r"}, {"id": "bogus"}, {"id": "qa"}]}', 3)
        self.assertEqual(out, {"db": "r", "qa": ""})

    def test_parse_respects_max(self):
        from office.router import parse_routing
        out = parse_routing('{"advisors": [{"id": "ux"}, {"id": "db"}, {"id": "sec"}]}', 2)
        self.assertEqual(list(out), ["ux", "db"])

    def test_parse_falls_back_to_ids_in_text(self):
        from office.router import parse_routing
        self.assertEqual(list(parse_routing("I would pick sec and then qa", 3)), ["sec", "qa"])

    def test_keyword_routing(self):
        from office.router import keyword_routing
        out = keyword_routing("online shop with login and payment, deploy to the cloud", 3)
        self.assertIn("sec", out)
        self.assertLessEqual(len(out), 3)
        self.assertEqual(list(keyword_routing("zzz", 2)), ["sec", "qa"])

    def test_prompt_lists_all_advisors(self):
        from office.router import build_routing_prompt
        prompt = build_routing_prompt("p", "", "draft", 3)
        for k in ("ux", "db", "sec", "devops", "qa"):
            self.assertIn(f"- {k}:", prompt)


class Providers(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        for k in ("GROQ_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_MODEL",
                  "OLLAMA_BASE_URL", "CUSTOM_BASE_URL", "CUSTOM_MODEL", "CUSTOM_API_KEY"):
            os.environ.pop(k, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_key_based_provider(self):
        from office import providers as p
        self.assertFalse(p.is_ready("Groq"))
        os.environ["GROQ_API_KEY"] = "k"
        self.assertTrue(p.is_ready("Groq"))
        self.assertTrue(p.in_fallback("Groq"))

    def test_ollama_ready_but_opt_in_for_fallback(self):
        from office import providers as p
        self.assertTrue(p.is_ready("Ollama (local)"))
        self.assertFalse(p.in_fallback("Ollama (local)"))
        os.environ["OLLAMA_MODEL"] = "llama3.1"
        self.assertTrue(p.in_fallback("Ollama (local)"))
        self.assertEqual(p.get_base_url("Ollama (local)"), "http://localhost:11434")

    def test_custom_needs_base_url(self):
        from office import providers as p
        name = "Custom (OpenAI-compatible)"
        self.assertFalse(p.is_ready(name))
        os.environ["CUSTOM_BASE_URL"] = "http://localhost:1234/v1"
        self.assertTrue(p.is_ready(name))
        self.assertFalse(p.in_fallback(name))
        os.environ["CUSTOM_MODEL"] = "m"
        self.assertTrue(p.in_fallback(name))
        self.assertEqual(p.default_model(name), "m")

    def test_build_llm_passes_base_url_and_prefix(self):
        from office import providers as p
        llm = p.build_llm("Ollama (local)", "llama3.1", 0.3, "x", "http://h:1")
        self.assertEqual(llm.kw["model"], "ollama/llama3.1")
        self.assertEqual(llm.kw["base_url"], "http://h:1")
        self.assertNotIn("base_url", p.build_llm("Groq", "m", 0.3, "k").kw)


class Pipeline(unittest.TestCase):
    def setUp(self):
        global FAIL_GROQ
        FAIL_GROQ = False
        LLM_CALLS.clear()
        import office.pipeline as pl
        pl.create_pdf = lambda *a, **k: b"%PDF"
        self.pl = pl

    def tearDown(self):
        global FAIL_GROQ
        FAIL_GROQ = False

    def run_it(self, candidates, advisors=None):
        return self.pl.run_pipeline("Salon booking app", candidates, 0.3, "Intermediate", "", "Standard",
                                    advisors, 3, True, FakeStatus())

    def test_full_run_auto_advisors(self):
        result = self.run_it([{"provider": "Groq", "model": "m", "key": "k", "base_url": None}])
        self.assertEqual(list(result["advice"]), ["db", "sec"])
        self.assertEqual(result["routing"]["db"], "stores data")
        self.assertTrue(result["plan_md"].startswith("<!-- Generated by AI Dev Office"))
        self.assertIn(result["final"].strip(), result["plan_md"])
        self.assertEqual(result["pdf"], b"%PDF")

    def test_manual_advisors(self):
        result = self.run_it([{"provider": "Groq", "model": "m", "key": "k", "base_url": None}], advisors=["qa"])
        self.assertEqual(list(result["advice"]), ["qa"])
        self.assertEqual(result["routing"], {"qa": "Selected by you"})

    def test_auto_switch_on_failure_and_sticks(self):
        global FAIL_GROQ
        FAIL_GROQ = True
        cands = [{"provider": "Groq", "model": "m", "key": "k", "base_url": None},
                 {"provider": "Ollama (local)", "model": "llama3.1", "key": "not-needed", "base_url": "http://localhost:11434"}]
        result = self.run_it(cands)
        self.assertIn("ollama", result["model_label"].lower())
        self.assertEqual(cands[0]["provider"], "Ollama (local)")  # the working provider moved to the front
        self.assertTrue(any(c.get("base_url") for c in LLM_CALLS))

    def test_all_providers_failing_raises(self):
        global FAIL_GROQ
        FAIL_GROQ = True
        with self.assertRaises(RuntimeError):
            self.run_it([{"provider": "Groq", "model": "m", "key": "k", "base_url": None}])

    def test_writer_prompt_uses_template_sections(self):
        from office.agents import AGENT_SPECS
        seen = []
        orig = self.pl.run_stage
        self.pl.run_stage = lambda agent, d, e: (seen.append((agent.role, d)) or orig(agent, d, e))
        try:
            self.run_it([{"provider": "Groq", "model": "m", "key": "k", "base_url": None}])
        finally:
            self.pl.run_stage = orig
        writer = [d for role, d in seen if role == AGENT_SPECS["writer"]["role"]][0]
        self.assertIn("7. Potential Challenges & Solutions", writer)
        self.assertIn("2. Requirements & Acceptance Criteria", writer)

    def test_friendly_errors(self):
        fe = self.pl.friendly_error
        self.assertIn("rate limit", fe(Exception("429 Too Many Requests")))
        self.assertIn("Ollama", fe(Exception("ConnectError: connection refused")))
        self.assertIn("API key", fe(Exception("401 invalid api key")))


if __name__ == "__main__":
    unittest.main()
