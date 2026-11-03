"""AI Dev Office - entry point.  Run with:  streamlit run main.py"""
import streamlit as st

# Must be the first Streamlit command
st.set_page_config(page_title="AI Dev Office", page_icon="🤖", layout="centered")

from office import ui  # noqa: E402  (importing the package also loads .env and applies the Groq workaround)
from office.pipeline import friendly_error, run_pipeline  # noqa: E402
from office.providers import PROVIDERS, default_model, get_base_url, get_key, in_fallback, needs_key  # noqa: E402


def build_candidates(settings: dict) -> list:
    """Chosen provider first, then any other provider that has a key (used for auto-switch)."""
    candidates = [{
        "provider": settings["provider"],
        "model": settings["model_name"],
        "key": settings["api_key"],
        "base_url": settings["base_url"],
    }]
    if settings["auto_fallback"]:
        for name in PROVIDERS:
            if name != settings["provider"] and in_fallback(name) and default_model(name):
                candidates.append({
                    "provider": name,
                    "model": default_model(name),
                    "key": get_key(name),
                    "base_url": get_base_url(name),
                })
    return candidates


def start_planning(settings: dict, form: dict):
    # Validate first
    if not form["project"].strip():
        st.warning("Please describe your project idea first.", icon="✍️")
        return
    if not settings["model_name"]:
        st.warning("Enter a custom model ID in the sidebar, or pick one from the list.", icon="🧩")
        return
    if needs_key(settings["provider"]) and not settings["api_key"]:
        st.error(f"No {settings['provider']} API key found. Add it to your .env file and restart the app.", icon="🔑")
        return
    if PROVIDERS[settings["provider"]].get("needs_base_url") and not settings["base_url"]:
        st.error("Enter the server's Base URL in the sidebar (or set CUSTOM_BASE_URL in your .env file).", icon="🔌")
        return

    candidates = build_candidates(settings)
    result, error = None, None

    with st.status(f"The AI team is working ({settings['provider']})...", expanded=True) as status:
        try:
            result = run_pipeline(
                form["project"].strip(),
                candidates,
                settings["temperature"],
                form["level"],
                form["stack_pref"],
                form["detail"],
                form["advisors"],
                form["max_advisors"],
                settings["use_tools"],
                status,
            )
            status.update(label=f"Done in {result['elapsed']:.0f}s", state="complete", expanded=False)
        except Exception as e:  # noqa: BLE001
            error = e
            status.update(label="Something went wrong", state="error", expanded=False)

    if error:
        st.error(friendly_error(error), icon="⚠️")
        with st.expander("Technical details"):
            st.code(str(error))
    else:
        ui.save_result(result)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
ui.init_state()
ui.inject_styles()
settings = ui.render_sidebar()
ui.render_header()
form = ui.render_form()

if form["start"]:
    start_planning(settings, form)

ui.render_results()
