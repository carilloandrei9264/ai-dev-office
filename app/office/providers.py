"""AI providers: settings, API keys from .env, and the LLM factory.

Add a provider by adding an entry to PROVIDERS. Anything LiteLLM supports works: `prefix` is its provider name.
"""
import os

from crewai import LLM

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
# Optional fields:
#   needs_key (default True)      False = works without an API key
#   base_url_env / default_base_url / needs_base_url   for providers served from a URL you choose
#   default_model_env             env var that overrides the default model (and, for keyless providers,
#                                 opts that provider in to automatic fallback)
PROVIDERS = {
    "Groq": {
        "prefix": "groq",
        "env_keys": ["GROQ_API_KEY"],
        "key_url": "https://console.groq.com/keys",
        "default_model": "openai/gpt-oss-120b",
        "models": ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"],
        "custom_hint": "e.g. openai/gpt-oss-120b",
        "note": "Very fast, generous free tier.",
    },
    "Gemini": {
        "prefix": "gemini",
        "env_keys": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        "key_url": "https://aistudio.google.com/apikey",
        "default_model": "gemini-3.8-flash",
        "models": ["gemini-3.8-flash"],
        "custom_hint": "e.g. gemini-3.8-flash",
        "note": "Free tier available, but daily request limits can be low.",
    },
    "OpenRouter": {
        "prefix": "openrouter",
        "env_keys": ["OPENROUTER_API_KEY"],
        "key_url": "https://openrouter.ai/keys",
        "default_model": "openai/gpt-oss-120b:free",
        "default_model_env": "OPENROUTER_MODEL",
        "models": ["openai/gpt-oss-120b:free"],
        "custom_hint": "e.g. openai/gpt-oss-120b:free (see openrouter.ai/models)",
        "note": "One key, many models. Models ending in ':free' cost nothing but have their own limits; "
                "check openrouter.ai/models for what is available now.",
    },
    "Ollama (local)": {
        "prefix": "ollama",
        "env_keys": [],
        "needs_key": False,
        "base_url_env": "OLLAMA_BASE_URL",
        "default_base_url": "http://localhost:11434",
        "default_model": "llama3.1",
        "default_model_env": "OLLAMA_MODEL",
        "models": ["llama3.1", "qwen2.5", "mistral"],
        "custom_hint": "e.g. llama3.1 (any model you pulled with `ollama pull`)",
        "note": "Runs on your own computer: no key, no rate limits. Start Ollama first and download the model "
                "(`ollama pull <model>`). Small local models often struggle with tools, so turn "
                "'Let agents use tools' off if the plan comes out broken.",
    },
    "Custom (OpenAI-compatible)": {
        "prefix": "openai",
        "env_keys": ["CUSTOM_API_KEY"],
        "needs_key": False,  # many local servers (LM Studio, vLLM...) accept any key
        "base_url_env": "CUSTOM_BASE_URL",
        "needs_base_url": True,
        "default_base_url": "",
        "default_model": "",
        "default_model_env": "CUSTOM_MODEL",
        "models": [],
        "custom_hint": "the model ID your server expects",
        "note": "Any server that speaks the OpenAI API: LM Studio, vLLM, llama.cpp server, a company gateway... "
                "Set CUSTOM_BASE_URL (for example http://localhost:1234/v1), and CUSTOM_API_KEY if it needs one.",
    },
}
CUSTOM = "Custom…"


def needs_key(provider: str) -> bool:
    return PROVIDERS[provider].get("needs_key", True)


def get_key(provider: str):
    """API key from your .env file / environment. Keyless providers return a harmless placeholder."""
    for name in PROVIDERS[provider]["env_keys"]:
        value = os.getenv(name)
        if value:
            return value
    return None if needs_key(provider) else "not-needed"


def get_base_url(provider: str):
    cfg = PROVIDERS[provider]
    env = cfg.get("base_url_env")
    if not env:
        return None
    return os.getenv(env) or cfg.get("default_base_url") or None


def default_model(provider: str) -> str:
    cfg = PROVIDERS[provider]
    env = cfg.get("default_model_env")
    return (os.getenv(env) if env else None) or cfg["default_model"]


def is_ready(provider: str) -> bool:
    """Has everything it needs to be tried (key and/or base URL)."""
    cfg = PROVIDERS[provider]
    if cfg.get("needs_base_url") and not get_base_url(provider):
        return False
    return bool(get_key(provider))


def in_fallback(provider: str) -> bool:
    """May this provider be used automatically when another one fails?
    Key-based providers: yes if the key exists. Keyless ones (Ollama, custom): only if you set their *_MODEL
    variable, so the app never silently tries a server you did not set up."""
    if not is_ready(provider):
        return False
    if needs_key(provider):
        return True
    env = PROVIDERS[provider].get("default_model_env")
    return bool(env and os.getenv(env))


def build_llm(provider: str, model: str, temperature: float, api_key: str, base_url: str = None) -> LLM:
    cfg = PROVIDERS[provider]
    kwargs = dict(
        model=f"{cfg['prefix']}/{model}",
        api_key=api_key,
        temperature=temperature,
        drop_params=True,
    )
    if base_url:
        kwargs["base_url"] = base_url
    return LLM(**kwargs)
