"""Tiny parser for the skill's Markdown files (front matter + '## Section' blocks). Standard library only."""
import re


def parse_frontmatter(text: str):
    """Return (meta dict, body). Front matter is `key: value` lines between two `---` lines."""
    text = text.lstrip("\ufeff")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, match.group(2)


def split_sections(body: str) -> dict:
    """Split a body on level-2 headings (ignoring '## ' inside code fences). Returns {heading: text}."""
    sections, current, buf, in_fence = {}, None, [], False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        heading = None if in_fence else re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf = heading.group(1), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def csv(value: str) -> list:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def read_text(path) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()
