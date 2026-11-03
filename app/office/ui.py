"""Everything you see on screen: styles, header, sidebar, input form, and results."""
import streamlit as st

from .agents import SPECIALISTS
from .pdf_export import safe_filename
from .providers import CUSTOM, PROVIDERS, default_model, get_base_url, get_key, in_fallback, is_ready, needs_key

STYLES = """
<style>
/* Hide default footer / menu, keep header so the sidebar toggle works */
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 2.5rem; max-width: 820px;}

.hero h1 {
    font-size: 2.4rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;
    background: linear-gradient(90deg, #6366f1, #8b5cf6 50%, #ec4899);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p {opacity: 0.75; margin: 0.35rem 0 1rem 0; font-size: 1.05rem;}

.agents {display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-bottom: 1.5rem;}
.pill {
    padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.85rem; font-weight: 600;
    border: 1px solid rgba(128,128,128,0.35); background: rgba(128,128,128,0.08);
}
.arrow {opacity: 0.4;}

/* Primary button */
div.stButton > button[kind="primary"] {
    border-radius: 12px; font-weight: 700; padding: 0.65rem 1.2rem; border: none;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
}
div.stButton > button[kind="primary"]:hover {filter: brightness(1.1);}
div.stButton > button {border-radius: 10px;}

/* Cards / inputs */
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px;}
textarea {border-radius: 12px !important;}
</style>
"""

HEADER = """
<div class="hero">
    <h1>AI Dev Office</h1>
    <p>Plan any software or web project with a team of AI agents.</p>
</div>
<div class="agents">
    <span class="pill">🔎 Researcher</span><span class="arrow">→</span>
    <span class="pill">📝 Writer</span><span class="arrow">→</span>
    <span class="pill">🧩 Specialist Advisors (auto-picked)</span><span class="arrow">→</span>
    <span class="pill">🧐 Reviewer</span>
</div>
"""

NO_PREF = "No preference"
CUSTOM_PREF = "Custom…"
STACK_OPTIONS = [
    NO_PREF,
    "Python + React",
    "Python + Streamlit",
    "Django (full-stack Python)",
    "FastAPI + PostgreSQL",
    "JavaScript / Node.js + React",
    "Next.js (full-stack TypeScript)",
    "PHP + Laravel",
    "Mobile app (Flutter)",
    "Mobile app (React Native)",
    "Free hosting only",
    "Solo developer, keep it simple",
    "Low budget / minimal cost",
    CUSTOM_PREF,
]

EXAMPLES = [
    "Personal portfolio website with a blog",
    "Inventory management system for a small shop",
    "Habit tracker mobile app",
    "Online booking system for a salon",
]


# ---------------------------------------------------------------------------
# Session state + callbacks
# ---------------------------------------------------------------------------
def init_state():
    st.session_state.setdefault("history", [])      # list of finished plans
    st.session_state.setdefault("current", None)    # plan currently displayed
    st.session_state.setdefault("project_input", "")


def set_example(text: str):
    st.session_state.project_input = text


def load_history(index: int):
    st.session_state.current = st.session_state.history[index]


def clear_history():
    st.session_state.history = []
    st.session_state.current = None


def save_result(result: dict):
    st.session_state.history.append(result)
    st.session_state.current = result


# ---------------------------------------------------------------------------
# Page pieces
# ---------------------------------------------------------------------------
def inject_styles():
    st.markdown(STYLES, unsafe_allow_html=True)


def render_header():
    st.markdown(HEADER, unsafe_allow_html=True)


def _render_history():
    st.subheader("🕘 Past plans")
    if st.session_state.history:
        for i, item in enumerate(reversed(st.session_state.history)):
            real_index = len(st.session_state.history) - 1 - i
            label = item["project"] if len(item["project"]) <= 30 else item["project"][:28] + "…"
            st.button(label, key=f"hist_{real_index}", on_click=load_history, args=(real_index,))
        st.button("Clear history", on_click=clear_history)
    else:
        st.caption("Your generated plans will appear here.")


def render_sidebar() -> dict:
    """Draw the sidebar and return the chosen settings."""
    with st.sidebar:
        st.header("⚙️ AI Settings")

        provider = st.selectbox("Provider", list(PROVIDERS.keys()), help="Choose which AI service does the work.")
        cfg = PROVIDERS[provider]

        choice = st.selectbox("Model", cfg["models"] + [CUSTOM])
        if choice == CUSTOM:
            model_name = st.text_input(
                "Custom model ID",
                value=default_model(provider) if not cfg["models"] else "",
                placeholder=cfg["custom_hint"],
            ).strip()
        else:
            model_name = choice

        base_url = None
        if cfg.get("base_url_env"):
            base_url = st.text_input(
                "Base URL",
                value=get_base_url(provider) or "",
                placeholder="http://localhost:1234/v1",
                help=f"Where the server listens. Can also be set with {cfg['base_url_env']} in your .env file.",
            ).strip() or None
        st.caption(cfg["note"])

        temperature = st.slider("Creativity", 0.0, 1.0, 0.3, 0.1, help="Lower = more focused, higher = more creative.")

        api_key = get_key(provider)
        if not needs_key(provider):
            st.info("No API key needed for this provider." if provider.startswith("Ollama") else
                    "API key is optional here (set CUSTOM_API_KEY if your server needs one).", icon="🔑")
        elif api_key:
            st.success(f"{provider} key ready", icon="🔑")
        else:
            st.error(f"No {provider} key found. Add it to your .env file and restart.", icon="🔑")

        with st.expander("Providers ready"):
            for name in PROVIDERS:
                st.write(f"{'✅' if is_ready(name) else '❌'}  {name}" + ("  (auto-switch)" if in_fallback(name) else ""))
            st.caption("Auto-switch uses providers with a key. Ollama and custom servers join only if "
                       "OLLAMA_MODEL / CUSTOM_MODEL is set in .env.")

        auto_fallback = st.toggle(
            "Auto-switch provider on errors",
            value=True,
            help="If a provider hits a rate limit or fails, retry with another provider that is set up.",
        )
        use_tools = st.toggle(
            "Let agents use tools",
            value=True,
            help="Web search, page reading, color-contrast and SQL checks. Turn off if a model has trouble "
                 "with tools or you hit rate limits.",
        )

        st.divider()
        _render_history()

    return {
        "provider": provider,
        "model_name": model_name,
        "temperature": temperature,
        "api_key": api_key,
        "base_url": base_url,
        "auto_fallback": auto_fallback,
        "use_tools": use_tools,
    }


def render_form() -> dict:
    """Draw the input form and return what the user entered."""
    with st.container(border=True):
        st.markdown("##### What do you want to build?")
        project = st.text_area(
            "Project idea",
            key="project_input",
            placeholder="Example: A personal portfolio website with a blog",
            height=100,
            label_visibility="collapsed",
        )

        st.caption("Need inspiration? Try one:")
        cols = st.columns(2)
        for i, example in enumerate(EXAMPLES):
            cols[i % 2].button(example, key=f"ex_{i}", on_click=set_example, args=(example,))

        with st.expander("Plan preferences (optional)"):
            c1, c2 = st.columns(2)
            level = c1.selectbox("Your experience level", ["Beginner", "Intermediate", "Advanced"], index=1)
            detail = c2.selectbox("Level of detail", ["Concise", "Standard", "Detailed"], index=1)
            choice = st.selectbox(
                "Preferred stack or constraints",
                STACK_OPTIONS,
                help="Pick one, or choose 'Custom…' to type your own.",
            )
            if choice == CUSTOM_PREF:
                stack_pref = st.text_input(
                    "Your stack or constraints",
                    placeholder="e.g. Python + React, free hosting only, solo developer",
                )
            elif choice == NO_PREF:
                stack_pref = ""
            else:
                stack_pref = choice

        auto_advisors = st.toggle(
            "Pick specialist advisors automatically",
            value=True,
            help="A dispatcher agent reads your project and only calls the specialists it really needs.",
        )
        if auto_advisors:
            max_advisors = st.slider(
                "Maximum advisors", 1, 5, 3,
                help="Fewer advisors means a faster run and fewer rate-limit problems.",
            )
            advisors = None  # None = let the dispatcher decide
        else:
            max_advisors = 5
            advisors = st.multiselect(
                "Specialist advisors",
                options=list(SPECIALISTS.keys()),
                default=list(SPECIALISTS.keys()),
                format_func=lambda k: SPECIALISTS[k]["label"],
                help="Each advisor adds an extra AI call.",
            )

        start = st.button("🚀 Start Planning", type="primary")

    return {
        "project": project,
        "level": level,
        "detail": detail,
        "stack_pref": stack_pref,
        "advisors": advisors,
        "max_advisors": max_advisors,
        "start": start,
    }


def render_results():
    """Show the current plan. It lives in session_state so downloads don't wipe the page."""
    current = st.session_state.current
    if not current:
        return

    st.divider()
    st.subheader(current["project"])
    st.caption(
        f"{current['created']}  ·  {current['model_label']}  ·  "
        f"generated in {current['elapsed']:.0f}s"
    )

    d1, d2, d3 = st.columns([1, 1, 1.3])
    d1.download_button(
        "📄 Download PDF",
        data=current["pdf"],
        file_name=f"project_plan_{safe_filename(current['project'])}.pdf",
        mime="application/pdf",
    )
    d2.download_button(
        "📝 Download Markdown",
        data=current["final"],
        file_name=f"project_plan_{safe_filename(current['project'])}.md",
        mime="text/markdown",
    )
    d3.download_button(
        "📌 PLAN.md for your AI",
        data=current.get("plan_md", current["final"]),
        file_name="PLAN.md",
        mime="text/markdown",
        help="Drop this file into your project folder and tell your AI coding assistant to build from it.",
    )

    tab_final, tab_advice, tab_research, tab_draft = st.tabs(
        ["📋 Final plan", "🧩 Specialist advice", "🔎 Research", "📝 First draft"]
    )
    with tab_final:
        st.markdown(current["final"])
    with tab_advice:
        advice = current.get("advice", {})
        if not advice:
            st.caption("No specialist advisors were used for this plan.")
        for key, text in advice.items():
            with st.expander(SPECIALISTS[key]["label"], expanded=False):
                reason = current.get("routing", {}).get(key)
                if reason:
                    st.caption(f"Why: {reason}")
                st.markdown(text)
    with tab_research:
        st.markdown(current["research"])
    with tab_draft:
        st.markdown(current["draft"])