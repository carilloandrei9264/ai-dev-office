"""Export a plan as a PDF (fpdf2) and build safe file names."""
import re
from datetime import datetime

from fpdf import FPDF

_PDF_REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2022": "-", "\u2026": "...",
    "\u00a0": " ", "\u2192": "->",
}


def _pdf_text(text: str) -> str:
    """Helvetica only supports latin-1: swap common symbols, drop the rest (emoji etc.)."""
    for old, new in _PDF_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)   # bold
    text = re.sub(r"`([^`]*)`", r"\1", text)        # inline code
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)     # stray asterisks
    return text.encode("latin-1", "ignore").decode("latin-1")


class PlanPDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)


def create_pdf(content: str, project_name: str) -> bytes:
    pdf = PlanPDF()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    def write(text: str, h: float = 6.5):
        try:
            pdf.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")
        except Exception:
            pdf.multi_cell(0, h, text[:150], new_x="LMARGIN", new_y="NEXT")

    # Title block
    pdf.set_font("Helvetica", "B", 20)
    write("AI Dev Office - Project Plan", h=11)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(110, 110, 110)
    write(_pdf_text(f"Project: {project_name}"), h=6)
    write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", h=6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    for raw in content.splitlines():
        line = raw.rstrip()
        pdf.set_x(pdf.l_margin)

        if not line.strip():
            pdf.ln(3)
            continue
        if re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", line):  # markdown table separator
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)", line)
        if heading:
            size = {1: 17, 2: 14, 3: 12, 4: 11}[len(heading.group(1))]
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", size)
            write(_pdf_text(heading.group(2)), h=size * 0.55 + 2)
            pdf.set_font("Helvetica", "", 11)
            continue

        pdf.set_font("Helvetica", "", 11)
        bullet = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        if bullet:
            indent = len(bullet.group(1)) // 2
            pdf.set_x(pdf.l_margin + 4 + 5 * indent)
            write("- " + _pdf_text(bullet.group(2)))
        else:
            write(_pdf_text(line))

    return bytes(pdf.output())


def safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text.strip())[:40].strip("_") or "project"
