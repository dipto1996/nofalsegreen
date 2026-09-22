"""Render docs/PAPER.md to a reviewable PDF.

A small purpose-built Markdown subset renderer: headings, paragraphs, bold and
italic and code spans, bullet and numbered lists, block quotes, fenced code,
tables, and horizontal rules. That is everything the paper uses.

Placeholders (`[TO RUN]`, `[…]`, `[INSERT: …]`) are highlighted so a reviewer
can see at a glance what is committed structure versus what is still empty.

    python3 scripts/render_pdf.py            # -> docs/PAPER.pdf
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "PAPER.md"
OUT = ROOT / "docs" / "PAPER.pdf"

ACCENT = colors.HexColor("#1a4d7a")
PLACEHOLDER_BG = colors.HexColor("#fff3cd")
CODE_BG = colors.HexColor("#f4f4f6")
MUTED = colors.HexColor("#5a5a5a")

ss = getSampleStyleSheet()

BODY = ParagraphStyle(
    "body", parent=ss["BodyText"], fontName="Times-Roman", fontSize=9.8, leading=13.4,
    alignment=TA_JUSTIFY, spaceBefore=0, spaceAfter=6.5, textColor=colors.black,
)
H1 = ParagraphStyle(
    "h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=15.5, leading=19,
    textColor=ACCENT, spaceBefore=4, spaceAfter=10, alignment=TA_LEFT,
)
H2 = ParagraphStyle(
    "h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.2, leading=15,
    textColor=ACCENT, spaceBefore=15, spaceAfter=6,
)
H3 = ParagraphStyle(
    "h3", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=10.4, leading=13,
    textColor=colors.HexColor("#25384a"), spaceBefore=11, spaceAfter=4,
)
TITLE = ParagraphStyle(
    "title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=17, leading=21,
    textColor=colors.black, spaceAfter=4, alignment=TA_LEFT,
)
STATUS = ParagraphStyle(
    "status", parent=BODY, fontName="Times-Roman", fontSize=9, leading=12.4, textColor=MUTED,
    leftIndent=9, borderPadding=6, backColor=colors.HexColor("#eef4fa"),
    borderColor=colors.HexColor("#c5d8ea"), borderWidth=0.6, spaceAfter=9,
)
QUOTE = ParagraphStyle(
    "quote", parent=BODY, leftIndent=14, rightIndent=8, textColor=MUTED,
    fontName="Times-Italic", spaceBefore=3, spaceAfter=7,
)
CODE = ParagraphStyle(
    "code", parent=ss["Code"], fontName="Courier", fontSize=7.9, leading=10.4,
    leftIndent=7, backColor=CODE_BG, borderPadding=5, spaceBefore=4, spaceAfter=8,
    textColor=colors.HexColor("#1c1c1c"),
)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.9, leading=10, alignment=TA_LEFT, spaceAfter=0)
CELL_H = ParagraphStyle("cellh", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
CAPTION = ParagraphStyle("cap", parent=BODY, fontSize=8.4, leading=11, textColor=MUTED, spaceBefore=3)

PLACEHOLDER_RE = re.compile(r"\[(?:TO RUN[^\]]*|INSERT:[^\]]*|…|[^\]]{0,24}(?:±\s*sd)?)\]")


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """Convert the inline Markdown the paper uses into reportlab markup."""
    t = esc(text)
    # code spans first, so their contents are not re-processed
    spans: list[str] = []

    def stash_code(m: re.Match) -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    t = re.sub(r"`([^`]+)`", stash_code, t)
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\*\w])\*([^*\n]+?)\*(?![\*\w])", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#1a4d7a">\1</link>', t)
    t = t.replace("$$", "").replace("\\", "")

    def unstash(m: re.Match) -> str:
        code = spans[int(m.group(1))]
        return (
            f'<font face="Courier" size="8.6" backColor="#f0f0f3">{code}</font>'
        )

    t = re.sub(r"\x00(\d+)\x00", unstash, t)
    # highlight remaining placeholders so empty structure is visible
    t = re.sub(
        r"(\[(?:TO RUN|INSERT:)[^\]]*\]|\[…\])",
        r'<font backColor="#ffe9a8"><b>\1</b></font>',
        t,
    )
    return t


def inline_header(text: str) -> str:
    """Header cells sit on a dark fill, so code spans must not carry a light
    background or the text renders white-on-white."""
    t = inline(text)
    t = re.sub(r'<font face="Courier" size="8.6" backColor="#f0f0f3">', '<font face="Courier" size="8.6">', t)
    return t


def table_flowable(rows: list[list[str]], width: float):
    header, *body = rows
    ncols = len(header)
    data = [[Paragraph(inline_header(c), CELL_H) for c in header]]
    for r in body:
        r = (r + [""] * ncols)[:ncols]
        data.append([Paragraph(inline(c), CELL) for c in r])

    # first column wider; the rest share what is left
    first = min(0.34 * width, max(1.25 * inch, width / ncols * 1.7)) if ncols > 2 else width / ncols
    rest = (width - first) / (ncols - 1) if ncols > 1 else width
    widths = [first] + [rest] * (ncols - 1)

    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b9c4cf")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f8fa")))
    t.setStyle(TableStyle(style))
    return t


def parse(md: str, width: float) -> list:
    flow: list = []
    lines = md.split("\n")
    i = 0
    first_h1 = True
    para: list[str] = []
    in_status = False

    def flush_para() -> None:
        nonlocal para, in_status
        if para:
            text = " ".join(para).strip()
            if text:
                flow.append(Paragraph(inline(text), STATUS if in_status else BODY))
            para = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_para()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(esc(lines[i]))
                i += 1
            i += 1
            if buf:
                flow.append(Paragraph("<br/>".join(b or "&nbsp;" for b in buf), CODE))
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and re.match(
            r"^\|[\s:\-|]+\|?$", lines[i + 1].strip()
        ):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw = lines[i].strip()
                if not re.match(r"^\|[\s:\-|]+\|?$", raw):
                    cells = [c.strip() for c in raw.strip("|").split("|")]
                    rows.append(cells)
                i += 1
            if rows:
                flow.append(Spacer(1, 3))
                flow.append(table_flowable(rows, width))
                flow.append(Spacer(1, 7))
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            flush_para()
            in_status = False
            level, text = len(m.group(1)), m.group(2)
            if level == 1 and first_h1:
                flow.append(Paragraph(inline(text), TITLE))
                first_h1 = False
            else:
                flow.append(Paragraph(inline(text), {1: H1, 2: H2, 3: H3, 4: H3}[level]))
            i += 1
            continue

        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            flush_para()
            in_status = False
            flow.append(Spacer(1, 2))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c8d2dc")))
            flow.append(Spacer(1, 6))
            i += 1
            continue

        if stripped.startswith(">"):
            flush_para()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            flow.append(Paragraph(inline(" ".join(buf)), QUOTE))
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        number = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if bullet or number:
            flush_para()
            ordered = bool(number)
            items = []
            while i < len(lines):
                st = lines[i].strip()
                b = re.match(r"^[-*]\s+(.*)$", st)
                n = re.match(r"^(\d+)\.\s+(.*)$", st)
                if not (b or n):
                    if st and lines[i].startswith(("   ", "\t")) and items:
                        items[-1] += " " + st
                        i += 1
                        continue
                    break
                items.append((b or n).group(1) if b else n.group(2))
                i += 1
            flow.append(
                ListFlowable(
                    [ListItem(Paragraph(inline(x), BODY), leftIndent=16) for x in items],
                    bulletType="1" if ordered else "bullet",
                    bulletFontSize=8, leftIndent=14, spaceAfter=6,
                )
            )
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        if stripped.startswith("**Status of this draft"):
            flush_para()
            in_status = True
        para.append(stripped)
        i += 1

    flush_para()
    return flow


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.9 * inch, 0.55 * inch, "No False Green — structural draft for review")
    canvas.drawRightString(LETTER[0] - 0.9 * inch, 0.55 * inch, f"{doc.page}")
    canvas.restoreState()


def main() -> int:
    md = SRC.read_text()
    doc = SimpleDocTemplate(
        str(OUT), pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="No False Green — structural draft",
        author="Diptopal Roy",
        subject="Benchmark for evidence-aware compliance verdicts",
    )
    flow = parse(md, doc.width)
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT}  ({kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
