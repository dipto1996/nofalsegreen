"""Build the LaTeX paper (paper/main.tex) from docs/PAPER.md and compile it.

docs/PAPER.md stays the single source: scripts/verify_paper.py checks every
number in it, and this script only typesets it. Figures are placed by HTML
comment markers in the Markdown, which the Markdown renderer ignores:

    <!-- FIGURE: name | width | Caption text -->       a PDF from paper/figures/
    <!-- TEXFIGURE: name | Caption text -->            a LaTeX figure body from paper/tex/name.tex

A bold "**Table N — title.** rest" paragraph immediately before a table (or a
generated-table block) becomes that table's caption.

    python3 scripts/build_latex.py           # writes paper/main.tex and paper/main.pdf
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "PAPER.md"
OUT = ROOT / "paper"

PREAMBLE = r"""\documentclass[10pt,twocolumn]{article}
\usepackage[letterpaper,top=0.9in,bottom=0.9in,left=0.75in,right=0.75in,columnsep=0.27in]{geometry}
\usepackage{fontspec}
\usepackage{unicode-math}
\setmainfont{LibertinusSerif}[Path=fonts/,Extension=.otf,UprightFont=*-Regular,BoldFont=*-Bold,ItalicFont=*-Italic,BoldItalicFont=*-BoldItalic]
\setsansfont{LibertinusSans}[Path=fonts/,Extension=.otf,UprightFont=*-Regular,BoldFont=*-Bold,ItalicFont=*-Italic]
\setmathfont{LibertinusMath-Regular.otf}
\setmonofont{lmmonolt10}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-oblique,BoldItalicFont=*-boldoblique,Scale=0.9]
\usepackage{microtype}
\usepackage{booktabs,array,adjustbox,tabularx}
\usepackage{rotating}
\usepackage{placeins}
\usepackage{graphicx}
\usepackage[table]{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,calc,shapes.misc}
\usepackage{enumitem}
\setlist{itemsep=1pt,topsep=2pt,parsep=0pt,leftmargin=1.2em}
\usepackage[font=small,labelfont={bf,sf},labelsep=period,skip=4pt,justification=justified,singlelinecheck=false]{caption}
\usepackage{fvextra}
\usepackage{url}
\def\UrlBreaks{\do\/\do\.\do\_\do\-\do\:}
\definecolor{linkblue}{HTML}{1D5C9E}
\usepackage[colorlinks=true,linkcolor=linkblue,citecolor=linkblue,urlcolor=linkblue]{hyperref}
\usepackage{titlesec}
\titleformat{\section}{\sffamily\large\bfseries}{\thesection}{0.55em}{}
\titleformat{\subsection}{\sffamily\normalsize\bfseries}{\thesubsection}{0.55em}{}
\titlespacing*{\section}{0pt}{10pt}{4pt}
\titlespacing*{\subsection}{0pt}{7pt}{3pt}
\setlength{\parskip}{0pt}
\setlength{\parindent}{1em}
\renewcommand{\topfraction}{0.9}\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.07}\renewcommand{\floatpagefraction}{0.85}
\renewcommand{\dbltopfraction}{0.9}\renewcommand{\dblfloatpagefraction}{0.85}
\setcounter{topnumber}{3}\setcounter{bottomnumber}{2}\setcounter{totalnumber}{5}\setcounter{dbltopnumber}{2}
\renewcommand{\arraystretch}{1.1}
\newcommand{\code}[1]{\path{#1}}
\definecolor{fgorange}{HTML}{C8553D}
\definecolor{fgblue}{HTML}{1D5C9E}
\definecolor{fggray}{HTML}{8A8984}
\definecolor{fgaqua}{HTML}{2A9D8F}
\pagestyle{plain}
\makeatletter
\renewcommand\maketitle{\twocolumn[{\centering
  {\sffamily\LARGE\bfseries\@title\par}\vskip 10pt
  {\large\@author\par}\vskip 14pt}]}
\makeatother
\renewenvironment{abstract}{\noindent{\sffamily\bfseries Abstract.}\ \small}{\par\vskip 6pt}
"""

SPECIALS = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
            "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(t: str) -> str:
    return "".join(SPECIALS.get(ch, ch) for ch in t)


ROBUST = False


def code(t: str) -> str:
    if ROBUST:  # inside captions and table cells: no \path (fragile in moving arguments)
        e = esc(t)
        for ch in ("/", "\\_", ".", "-"):
            e = e.replace(ch, ch + r"\allowbreak{}")
        return r"\texttt{" + e + "}"
    # \path breaks at / . _ - and needs a delimiter absent from the text.
    for d in "|!+@=;":
        if d not in t:
            return r"\texttt{\path" + d + t + d + "}"
    return r"\texttt{" + esc(t) + "}"


def cap(t: str) -> str:
    global ROBUST
    ROBUST = True
    try:
        return inline(t)
    finally:
        ROBUST = False


def inline(t: str) -> str:
    """Markdown inline -> LaTeX. Code spans are protected first."""
    keep: list[str] = []

    def stash(s: str) -> str:
        keep.append(s)
        return f"\x00{len(keep) - 1}\x00"

    t = re.sub(r"\$\$(.+?)\$\$", lambda m: stash(r"\[" + m.group(1) + r"\]"), t)
    t = re.sub(r"(?<![\\$])\$(?=\S)([^$]+?)(?<=\S)\$", lambda m: stash("$" + m.group(1) + "$"), t)
    t = re.sub(r"`([^`]+)`", lambda m: stash(code(m.group(1))), t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               lambda m: stash(r"\href{" + m.group(2).replace("%", r"\%").replace("#", r"\#") + "}{"
                               + esc(m.group(1)) + "}"), t)
    t = re.sub(r"(?<![\w/])(https?://[^\s)]+[^\s).,;])", lambda m: stash(r"\url{" + m.group(1) + "}"), t)
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\\emph{\1}", t)
    t = t.replace('"', "\x01")
    # typographic quotes
    out, opened = [], False
    for ch in t:
        if ch == "\x01":
            out.append("``" if not opened else "''")
            opened = not opened
        else:
            out.append(ch)
    t = "".join(out)
    t = t.replace("...", r"\ldots{}").replace("…", r"\ldots{}")
    t = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], t)
    return t


APPENDIX = False


def table(rows: list[str], caption: str | None, label: str | None, notes: str | None,
          placement: str = "tbp") -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    ncol = len(head)
    # Left-align the first column and text-like columns; right-align numeric columns.
    def numeric(j):
        vals = [r[j] for r in body if j < len(r)]
        return sum(bool(re.match(r"^[-+—]?[\d.]", v.replace("**", "").strip())) for v in vals) > len(vals) / 2
    longest = [max(len(r[j]) if j < len(r) else 0 for r in body) for j in range(ncol)]
    natural = sum(max(len(r[j]) if j < len(r) else 0 for r in cells) for j in range(ncol))
    span = APPENDIX or ncol > 4 or natural > 70        # body tables: full width or one column
    W = r"\textwidth" if span else r"\columnwidth"
    wide_text = max(longest) > (48 if span else 30)
    if wide_text:
        spec = "".join(r">{\raggedright\arraybackslash}X" if longest[j] > 24 else "l" for j in range(ncol))
        env_open, env_close = r"\begin{tabularx}{" + W + "}{" + spec + "}", r"\end{tabularx}"
    else:
        spec = "".join("r" if j and numeric(j) else "l" for j in range(ncol))
        env_open, env_close = r"\begin{tabular}{" + spec + "}", r"\end{tabular}"
    lines = [env_open, r"\toprule",
             " & ".join(r"\textbf{" + cap(h) + "}" for h in head) + r" \\", r"\midrule"]
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        lines.append(" & ".join(cap(c) for c in r) + r" \\")
    lines += [r"\bottomrule", env_close]
    tab = "\n".join(lines)
    rotate = APPENDIX and not wide_text and natural > 150
    env = "sidewaystable" if rotate else ("table*" if span and not APPENDIX else "table")
    out = [r"\begin{" + env + "}" + ("" if rotate else "[t]"),
           r"\centering\footnotesize\setlength{\tabcolsep}{4pt}"]
    if caption:
        out.append(r"\caption{" + caption + "}")
    if label:
        out.append(r"\label{" + label + "}")
    mw = r"\textheight" if rotate else W
    out.append(tab if wide_text else r"\begin{adjustbox}{max width=" + mw + "}" + "\n" + tab + "\n" + r"\end{adjustbox}")
    if notes:
        out.append(r"\par\vspace{3pt}\begin{minipage}{" + (r"\textheight" if rotate else W)
                   + r"}\scriptsize " + notes + r"\end{minipage}")
    out.append(r"\end{" + env + "}")
    return "\n".join(out)


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    title = lines[0].lstrip("# ").strip()
    author = ""
    in_abstract = False
    appendix = False
    para: list[str] = []
    pending_caption: tuple[str, str] | None = None  # (caption, label)
    table_no = 0

    def flush():
        nonlocal para
        if para:
            out.append(inline(" ".join(s.strip() for s in para)) + "\n")
            para = []

    i = 1
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        # author line
        if not author and s and not s.startswith("#") and s != "---" and "Settle AI" in s:
            author = s
            i += 1
            continue

        m = re.match(r"<!--\s*FIGURE:\s*(\S+)\s*\|\s*([^|]+)\|\s*(.*?)-->\s*$", s)
        if m:
            flush()
            name, width, capt = m.group(1), m.group(2).strip(), m.group(3).strip()
            star = "*" if width.startswith("wide") and not appendix else ""
            w = r"\textwidth" if width.startswith("wide") else (width if appendix else r"\columnwidth")
            out.append(r"\begin{figure" + star + "}[t]\\centering" + "\n"
                       + r"\includegraphics[width=" + w + "]{figures/" + name + ".pdf}\n"
                       + r"\caption{" + cap(capt) + "}\\label{fig:" + name + "}\n" + r"\end{figure" + star + "}" + "\n")
            i += 1
            continue
        m = re.match(r"<!--\s*TEXFIGURE:\s*(\S+)\s*\|\s*(.*?)-->\s*$", s)
        if m:
            flush()
            out.append(r"\begin{figure*}[t]\centering" + "\n" + r"\begin{adjustbox}{max width=\textwidth}\input{tex/" + m.group(1) + r"}\end{adjustbox}" + "\n"
                       + r"\caption{" + cap(m.group(2)) + "}\\label{fig:" + m.group(1) + "}\n"
                       + r"\end{figure*}" + "\n")
            i += 1
            continue
        if s.startswith("<!--"):
            # skip comments (single or multi-line), keep generated table contents
            if "BEGIN GENERATED" in s or "END GENERATED" in s:
                i += 1
                continue
            while "-->" not in lines[i]:
                i += 1
            i += 1
            continue

        if s == "---":
            flush()
            i += 1
            continue

        if s.startswith("## "):
            flush()
            if in_abstract:
                out.append(r"\end{abstract}" + "\n")
                in_abstract = False
            h = s[3:].strip()
            if h == "Abstract":
                out.append(r"\begin{abstract}")
                in_abstract = True
            elif h == "References":
                out.append(r"\FloatBarrier" + "\n" + r"\section*{References}\label{sec:refs}" + "\n" + r"\begingroup\small"
                           + r"\raggedright\setlength{\parindent}{-1.2em}\setlength{\leftskip}{1.2em}\setlength{\parskip}{2pt}")
                refs = []
                i += 1
                while i < len(lines) and not lines[i].startswith("## "):
                    if lines[i].strip():
                        refs.append(lines[i].strip())
                    i += 1
                out.extend(inline(r) + "\n" for r in refs)
                out.append(r"\endgroup" + "\n")
                continue
            elif h.startswith("Appendix"):
                if not appendix:
                    out.append(r"\clearpage" + "\n" + r"\onecolumn" + "\n" + r"\appendix")
                    appendix = True
                    global APPENDIX
                    APPENDIX = True
                ht = re.sub(r"^Appendix [A-Z]:\s*", "", h)
                out.append(r"\section{" + inline(ht) + "}\\label{app:" + h.split()[1].rstrip(":") + "}")
            else:
                num = re.match(r"(\d+)\.\s+(.*)", h)
                out.append((r"\section{" if (num or appendix) else r"\section*{") + inline(num.group(2) if num else h) + "}"
                           + (r"\label{sec:" + num.group(1) + "}" if num else ""))
            i += 1
            continue
        if s.startswith("### "):
            flush()
            h = s[4:].strip()
            num = re.match(r"([A-Z\d]+\.\d+)\s+(.*)", h)
            out.append(r"\subsection{" + inline(num.group(2) if num else h) + "}"
                       + (r"\label{sec:" + num.group(1) + "}" if num else ""))
            i += 1
            continue
        if s.startswith("# "):
            # a stray level-1 heading inside an appendix sample prompt: treat as text
            para.append(s)
            i += 1
            continue

        if s.startswith("```"):
            flush()
            fence = s[:len(s) - len(s.lstrip("`"))]
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != fence:
                body.append(lines[i])
                i += 1
            i += 1
            out.append(r"\begin{Verbatim}[breaklines,breakanywhere,fontsize=\scriptsize,frame=single,framerule=0.3pt,rulecolor=\color{fggray}]"
                       + "\n" + "\n".join(body) + "\n" + r"\end{Verbatim}" + "\n")
            continue

        if s.startswith("> "):
            flush()
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip().lstrip("> "))
                i += 1
            out.append(r"\begin{quote}\small " + inline(" ".join(q)) + r"\end{quote}" + "\n")
            continue

        # caption paragraph for a following table or image
        mcap = re.match(r"\*\*(Table|Figure) ([\dA-Z]+[a-z]?)\s*[—-]\s*(.+?)\*\*\s*(.*)", s)
        if mcap:
            flush()
            capl = [s]
            j = i + 1
            while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith(("|", "<!--", "![")):
                capl.append(lines[j].strip())
                j += 1
            full = " ".join(capl)
            mc = re.match(r"\*\*(Table|Figure) ([\dA-Z]+[a-z]?)\s*[—-]\s*(.+?)\*\*\s*(.*)", full)
            kind, num, ttl, rest = mc.groups()
            pending_caption = (cap(ttl.rstrip(".") + ". " + rest).strip(),
                               f"{'tab' if kind == 'Table' else 'fig'}:{num}")
            i = j
            continue

        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            # notes: a non-empty paragraph directly after the table inside a generated block
            notes = None
            k = i
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and lines[k].strip() and not lines[k].startswith(("<!-- END", "#", "|", "**")) \
                    and i < len(lines) and any("END GENERATED" in lines[x] for x in range(k, min(k + 3, len(lines)))):
                notes = cap(lines[k].strip())
                i = k + 1
            capn, lab = pending_caption if pending_caption else (None, None)
            pending_caption = None
            table_no += 1
            out.append(table(rows, capn, lab, notes) + "\n")
            continue

        if s.startswith("!["):
            flush()
            i += 1
            pending_caption = None  # replaced by FIGURE markers
            continue

        mlist = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", ln)
        if mlist and not para:
            env = "enumerate" if mlist.group(2)[0].isdigit() else "itemize"
            items = []
            while i < len(lines):
                ml = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", lines[i])
                if ml and len(ml.group(1)) <= 1:
                    items.append([ml.group(3)])
                    i += 1
                elif items and lines[i].startswith("  ") and lines[i].strip():
                    items[-1].append(lines[i].strip())
                    i += 1
                else:
                    break
            out.append(r"\begin{" + env + "}\n" + "\n".join(r"\item " + inline(" ".join(it)) for it in items)
                       + "\n" + r"\end{" + env + "}\n")
            continue

        if not s:
            flush()
            i += 1
            continue
        para.append(s)
        i += 1
    flush()
    if in_abstract:
        out.append(r"\end{abstract}")

    head = PREAMBLE + "\n" + r"\title{\Large\bfseries " + inline(title) + "}\n"
    au = re.sub(r"\s*See \*Competing interests\*.*", "", author).strip().rstrip(".")
    mm = re.match(r"(.+?),\s*(.+?)\s*\((.+?)\)", au)
    if mm:
        head += r"\author{" + inline(mm.group(1)) + r"\\ \normalsize " + inline(mm.group(2)) + r"\\ \normalsize\texttt{" + esc(mm.group(3)) + "}}\n"
    head += r"\date{}" + "\n" + r"\begin{document}" + "\n" + r"\maketitle" + "\n" + r"\thispagestyle{empty}" + "\n"
    return head + "\n".join(out) + "\n" + r"\end{document}" + "\n"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    tex = convert(SRC.read_text())
    (OUT / "main.tex").write_text(tex)
    r = subprocess.run(["tectonic", "--keep-logs", "main.tex"], cwd=OUT, capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-3000:])
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
