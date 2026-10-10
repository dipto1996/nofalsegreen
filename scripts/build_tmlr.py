"""Build the anonymised TMLR submission from docs/PAPER.md: the official TMLR style
(paper/tmlr_style, unmodified), its title block, abstract and section formatting, single column,
with Latin Modern in OpenType so the paper's Unicode symbols typeset. Uses the anonymised text
of scripts/build_anonymous.py (run it first). Writes paper_tmlr/main.tex and main.pdf.

    python3 scripts/build_anonymous.py && python3 scripts/build_tmlr.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_latex import convert  # noqa: E402

OUT = ROOT / "paper_tmlr"
PRE = r"""\documentclass[10pt]{article}
\PassOptionsToPackage{table}{xcolor}
\usepackage{tmlr}
\usepackage{fontspec}
\usepackage{unicode-math}
\setmainfont{lmroman10}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]
\setsansfont{lmsans10}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-oblique]
\setmonofont{lmmonolt10}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-oblique,BoldItalicFont=*-boldoblique,Scale=0.9]
\setmathfont{latinmodern-math.otf}
\usepackage{newunicodechar}
\newunicodechar{≤}{\ensuremath{\leq}}  % Latin Modern text fonts lack U+2264
\newunicodechar{≥}{\ensuremath{\geq}}
\usepackage{microtype}
\usepackage{booktabs,array,adjustbox,tabularx}
\usepackage{rotating}
\usepackage{placeins}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,calc,shapes.misc}
\usepackage{enumitem}
\setlist{itemsep=1pt,topsep=2pt,parsep=0pt,leftmargin=1.2em}
\usepackage[font=small,labelfont={bf},labelsep=period,skip=4pt]{caption}
\usepackage{fvextra}
\usepackage{url}
\def\UrlBreaks{\do\/\do\.\do\_\do\-\do\:}
\definecolor{linkblue}{HTML}{1D5C9E}
\usepackage[colorlinks=true,linkcolor=linkblue,citecolor=linkblue,urlcolor=linkblue]{hyperref}
\renewcommand{\arraystretch}{1.1}
\newcommand{\code}[1]{\path{#1}}
\definecolor{fgorange}{HTML}{C8553D}
\definecolor{fgblue}{HTML}{1D5C9E}
\definecolor{fggray}{HTML}{8A8984}
\definecolor{fgaqua}{HTML}{2A9D8F}
"""

if __name__ == "__main__":
    md = (ROOT / "paper_anon" / "PAPER_ANON.md").read_text()
    tex = convert(md)
    title = re.search(r"\\title\{\\Large\\bfseries (.*?)\}\n", tex).group(1)
    body = tex.split("\\maketitle\n", 1)[1].replace("\\thispagestyle{empty}\n", "", 1)
    head = (PRE + "\\title{" + title + "}\n"
            "\\author{\\name Anonymous authors}\n"  # not printed: the style shows "Anonymous authors" until [accepted]
            "\\begin{document}\n\\maketitle\n")
    if OUT.exists():
        shutil.move(str(OUT), str(ROOT / f".paper_tmlr_prev_{time.strftime('%Y%m%d%H%M%S')}"))
    OUT.mkdir()
    for f in ("tmlr.sty", "fancyhdr.sty"):
        shutil.copy(ROOT / "paper" / "tmlr_style" / f, OUT / f)
    shutil.copytree(ROOT / "paper" / "figures", OUT / "figures")
    shutil.copytree(ROOT / "paper" / "tex", OUT / "tex")
    (OUT / "main.tex").write_text(head + body)
    r = subprocess.run(["tectonic", "--keep-logs", "main.tex"], cwd=OUT, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-3000:])
        raise SystemExit("compile failed")
    print("wrote paper_tmlr/main.pdf")
