"""Build the anonymised copy of docs/PAPER.md for double-blind review (TMLR). Every change is a
listed substitution, and the build fails if any identifying string survives. Writes
paper_anon/main.tex and paper_anon/main.pdf (fonts from TeX Live, no author metadata).

    python3 scripts/build_anonymous.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_latex import convert  # noqa: E402

OUT = ROOT / "paper_anon"
SUBS = [
    (r"https://github\.com/dipto1996/nofalsegreen \(release\n`v1\.0-paper`\)",
     "the anonymous supplementary archive\n(snapshot of release `v1.0-paper`)"),
    (r"Diptopal Roy, Independent researcher \(diptopal@joinsettle\.info\)",
     "Anonymous authors, Paper under double-blind review (anonymous@review.invalid)"),
    (r"This is the author's personal research\. The author is a co-founder of\nSettle AI Inc\., which builds",
     "The author is a co-founder of a\ncompany that builds"),
    (r"Settle AI's cloud credits", "that company's cloud credits"),
    (r"\(commits?\s+(`[0-9a-f]{7}`(,\s+|,\s+and\s+|\s+and\s+)?)+\)", "(commit hash withheld for review)"),
    (r"commits?\s+(`[0-9a-f]{7}`(,\s+|,\s+and\s+|\s+and\s+)?)+", "a commit (hash withheld for review)"),
]
FORBIDDEN = ["Settle", "Diptopal", "Roy,", "joinsettle", "github.com"]

if __name__ == "__main__":
    md = (ROOT / "docs" / "PAPER.md").read_text()
    for pat, rep in SUBS:
        md, n = re.subn(pat, rep, md)
        print(f"{n:3d}  {pat[:60]}")
    left = [w for w in FORBIDDEN if w in md] + re.findall(r"`[0-9a-f]{7}`", md)
    if left:
        raise SystemExit(f"identifying strings remain: {sorted(set(left))}")
    tex = convert(md).replace("Path=fonts/,", "")
    if OUT.exists():
        import time
        shutil.move(str(OUT), str(ROOT / f".paper_anon_prev_{time.strftime('%Y%m%d%H%M%S')}"))
    OUT.mkdir()
    shutil.copytree(ROOT / "paper" / "figures", OUT / "figures")
    shutil.copytree(ROOT / "paper" / "tex", OUT / "tex")
    (OUT / "main.tex").write_text(tex)
    (OUT / "PAPER_ANON.md").write_text(md)
    r = subprocess.run(["tectonic", "main.tex"], cwd=OUT, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2000:])
        raise SystemExit("compile failed")
    print("wrote paper_anon/main.pdf")
