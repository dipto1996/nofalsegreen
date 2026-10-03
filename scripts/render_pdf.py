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


def figure1(width: float):
    """Figure 1 drawn natively (no SVG dependency), from the same points as
    scripts/make_figure.py. Each model's two conditions are joined by a line, so
    the move from offered (filled) to withheld (open) is visible."""
    from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Rect, String

    sys.path.insert(0, str(ROOT / "scripts"))
    from make_figure import collect

    pts = collect()
    W, H = width, width * 0.62
    L, R, T, B = 46, 150, 14, 36
    pw, ph = W - L - R, H - T - B
    X = lambda r: L + r * pw  # noqa: E731
    Y = lambda f: B + f * ph  # noqa: E731
    d = Drawing(W, H)
    grey = colors.HexColor("#d8d8de")
    for k in range(6):
        v = k / 5
        d.add(Line(X(v), B, X(v), B + ph, strokeColor=grey, strokeWidth=0.4))
        d.add(Line(L, Y(v), L + pw, Y(v), strokeColor=grey, strokeWidth=0.4))
        d.add(String(X(v), B - 11, f"{v:.1f}", fontSize=7, textAnchor="middle"))
        d.add(String(L - 4, Y(v) - 2.5, f"{v:.1f}", fontSize=7, textAnchor="end"))
    d.add(Rect(L, B, pw, ph, fillColor=None, strokeColor=colors.HexColor("#555"), strokeWidth=0.6))
    d.add(String(L + pw / 2, 6, "Violation recall", fontSize=8, textAnchor="middle"))
    ylab = Group(String(0, 0, "False-green rate", fontSize=8, textAnchor="middle"))
    ylab.transform = (0, 1, -1, 0, 14, B + ph / 2)  # rotate 90 degrees
    d.add(ylab)
    blue = colors.HexColor("#1a4d7a")
    corners: dict[tuple, list] = {}
    for q in pts:
        if q["kind"] == "baseline":
            corners.setdefault((round(q["recall"], 3), round(q["fgr"], 3)), []).append(q["label"])
    for (rc, fg), names in corners.items():
        x, y = X(rc), Y(fg)
        d.add(Rect(x - 3, y - 3, 6, 6, fillColor=colors.HexColor("#8a8a8a"), strokeColor=None))
        right = rc > 0.5  # labels on the right edge go inside the plot
        d.add(String(x - 5 if right else x + 5, y + 4, " / ".join(sorted(names)), fontSize=6.5,
                     fillColor=colors.HexColor("#666"), textAnchor="end" if right else "start"))
    models: dict[str, dict] = {}
    for q in pts:
        if q["kind"] == "model":
            name, cond = q["label"].rsplit(" (", 1)
            models.setdefault(name, {})[cond.rstrip(")")] = q
    ly = B + ph - 4
    for i, (name, c) in enumerate(sorted(models.items())):
        num = str(i + 1)
        if "offered" in c and "withheld" in c:
            d.add(Line(X(c["offered"]["recall"]), Y(c["offered"]["fgr"]),
                       X(c["withheld"]["recall"]), Y(c["withheld"]["fgr"]),
                       strokeColor=colors.HexColor("#9fb4c8"), strokeWidth=0.7))
        if "offered" in c:
            d.add(Circle(X(c["offered"]["recall"]), Y(c["offered"]["fgr"]), 3.2,
                         fillColor=blue, strokeColor=None))
        if "withheld" in c:
            x, y = X(c["withheld"]["recall"]), Y(c["withheld"]["fgr"])
            d.add(Circle(x, y, 3.2, fillColor=colors.white, strokeColor=blue, strokeWidth=1))
            d.add(String(x + 5, y - 2.5, num, fontSize=7, fillColor=blue))
        d.add(String(L + pw + 10, ly - i * 11, f"{num}  {name}", fontSize=7))
    ly2 = ly - len(models) * 11 - 8
    d.add(Circle(L + pw + 14, ly2 + 2.5, 3.2, fillColor=blue, strokeColor=None))
    d.add(String(L + pw + 22, ly2, "abstention offered", fontSize=7))
    d.add(Circle(L + pw + 14, ly2 - 9, 3.2, fillColor=colors.white, strokeColor=blue, strokeWidth=1))
    d.add(String(L + pw + 22, ly2 - 11.5, "abstention withheld", fontSize=7))
    d.add(Rect(L + pw + 11, ly2 - 23, 6, 6, fillColor=colors.HexColor("#8a8a8a"), strokeColor=None))
    d.add(String(L + pw + 22, ly2 - 22.5, "trivial baseline", fontSize=7))
    return d


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

        if stripped.startswith("![Figure 1]"):
            flush_para()
            flow.append(figure1(width))
            flow.append(Spacer(1, 6))
            i += 1
            continue
        if stripped.startswith("```"):
            flush_para()
            # A fence closes only on a line of the same backtick run, so a block
            # that itself contains ```csv fences (Appendix B) can use ````.
            fence = stripped[: len(stripped) - len(stripped.lstrip("`"))]
            i += 1
            buf = []
            while i < len(lines) and lines[i].strip() != fence:
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
                    if st and lines[i].startswith(("  ", "\t")) and items:
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
    canvas.drawString(0.9 * inch, 0.55 * inch, "No False Green — complete draft for review")
    canvas.drawRightString(LETTER[0] - 0.9 * inch, 0.55 * inch, f"{doc.page}")
    canvas.restoreState()


def main() -> int:
    # Generated-region markers are for scripts/fill_results.py, not for readers.
    md = re.sub(r"^<!--[^\n]*-->[ \t]*\n", "", SRC.read_text(), flags=re.M)
    doc = SimpleDocTemplate(
        str(OUT), pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="No False Green — complete draft",
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
