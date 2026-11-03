"""Tools the agents can use: web search, page reader, color contrast, SQL check, security checklist.

Contrast and SQL checks are thin wrappers over skill/scripts/, so the app and the installable skill behave the same."""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

from crewai.tools import tool

from .skill_loader import load_script, read_reference

# ---------------------------------------------------------------------------
# Tools the agents can use
# ---------------------------------------------------------------------------
def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


@tool("web_search")
def web_search(query: str) -> str:
    """Search the web (DuckDuckGo) and return the top results with title, link and a short snippet.
    Use it for current best practices, library versions, pricing, and documentation."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
    except ImportError:
        return "Web search is unavailable (pip install ddgs). Answer from your own knowledge and say it is unverified."
    try:
        results = list(DDGS().text(query, max_results=5))
    except Exception as e:  # noqa: BLE001
        return f"Search failed: {e}. Answer from your own knowledge and say it is unverified."
    if not results:
        return "No results found."
    return "\n".join(
        f"- {r.get('title', '')} ({r.get('href', '')}): {_clip(r.get('body', ''), 200)}" for r in results
    )


def _is_public_host(hostname: str) -> bool:
    """True only if EVERY address the host resolves to is a public one."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return bool(infos)


@tool("read_webpage")
def read_webpage(url: str) -> str:
    """Fetch a public web page and return its readable text (first ~3000 characters).
    Use it to read documentation or pricing pages found with web_search."""
    try:
        import requests

        current = url
        for _ in range(4):  # follow at most 3 redirects, checking each hop
            parsed = urlparse(current)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                return "Invalid URL. It must start with http:// or https://"
            if not _is_public_host(parsed.hostname):
                return "Blocked: private, local or unresolvable addresses are not allowed."
            resp = requests.get(current, timeout=10, allow_redirects=False,
                                headers={"User-Agent": "Mozilla/5.0 (AI-Dev-Office)"})
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    break
                current = urljoin(current, location)
                continue
            resp.raise_for_status()
            html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", resp.text)
            text = re.sub(r"(?s)<[^>]+>", " ", html)
            return _clip(re.sub(r"\s+", " ", text).strip(), 3000)
        return "Could not read the page: too many redirects."
    except Exception as e:  # noqa: BLE001
        return f"Could not read the page: {e}"


_contrast = load_script("contrast")
_sql_check = load_script("sql_check")


@tool("check_color_contrast")
def check_color_contrast(foreground_hex: str, background_hex: str) -> str:
    """Calculate the WCAG contrast ratio between a text color and a background color
    (hex values such as #111827 and #ffffff) and say whether it passes AA / AAA."""
    return _contrast.check(foreground_hex, background_hex)


@tool("validate_sql_schema")
def validate_sql_schema(sql: str) -> str:
    """Check CREATE TABLE / CREATE INDEX statements by running them in a temporary in-memory SQLite database.
    It verifies syntax and that every foreign key points at an existing table. SQLite is lenient with
    column types and does not cover PostgreSQL/MySQL-specific features."""
    return _sql_check.validate(sql)


@tool("security_checklist")
def security_checklist(project_type: str) -> str:
    """Return the OWASP Top 10 security checklist with one-line mitigations, plus extra checks
    for project types such as api, login, payments, file upload or AI features.
    Pass a short description of the project type."""
    return read_reference("security-checklist.md")
