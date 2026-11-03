"""Workaround for a CrewAI + Groq bug.

Newer CrewAI versions add an internal "cache_breakpoint" key to messages, and Groq rejects it.
This strips the key before the request leaves the app. It is applied once, when the package is imported.
Safe to delete this file (and its import in __init__.py) once your CrewAI version fixes the bug upstream.
"""
import litellm

if not getattr(litellm, "_cb_patched", False):
    _orig_completion = litellm.completion

    def _completion_without_cb(*args, **kwargs):
        msgs = kwargs.get("messages")
        if msgs:
            kwargs["messages"] = [
                {k: v for k, v in m.items() if k != "cache_breakpoint"}
                if isinstance(m, dict)
                else m
                for m in msgs
            ]
        return _orig_completion(*args, **kwargs)

    litellm.completion = _completion_without_cb
    litellm._cb_patched = True  # Streamlit reruns the script; patch only once
