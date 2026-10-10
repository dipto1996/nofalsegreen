"""Assemble the arXiv source package for docs/PAPER.md (processor: xelatex, available at arXiv
since November 2025). The fonts are loaded by file name from TeX Live, which ships Libertinus
and Latin Modern, so no font files are uploaded. Writes paper_arxiv/ and paper_arxiv.tar.gz and
test-compiles the package with Tectonic.

    python3 scripts/build_latex.py && python3 scripts/build_arxiv.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "paper", ROOT / "paper_arxiv"

if __name__ == "__main__":
    tex = (SRC / "main.tex").read_text()
    tex = tex.replace("Path=fonts/,", "")  # TeX Live provides LibertinusSerif-*.otf and LibertinusSans-*.otf
    used = sorted(set(re.findall(r"figures/([\w.-]+\.pdf)", tex)))
    inputs = sorted(set(re.findall(r"\\input\{tex/([\w-]+)\}", tex)))
    if OUT.exists():  # never delete a previous build: set it aside under a timestamped name
        import time
        shutil.move(str(OUT), str(ROOT / f".paper_arxiv_prev_{time.strftime('%Y%m%d%H%M%S')}"))
    (OUT / "figures").mkdir(parents=True)
    (OUT / "tex").mkdir()
    (OUT / "main.tex").write_text(tex)
    for f in used:
        shutil.copy(SRC / "figures" / f, OUT / "figures" / f)
    for f in inputs:
        shutil.copy(SRC / "tex" / f"{f}.tex", OUT / "tex" / f"{f}.tex")
    (OUT / "00README").write_text("main.tex xelatex\n")
    r = subprocess.run(["tectonic", "--keep-logs", "main.tex"], cwd=OUT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise SystemExit("test compile failed")
    pdf = OUT / "main.pdf"
    shutil.move(str(pdf), str(ROOT / "paper_arxiv_preview.pdf"))
    for f in OUT.glob("main.*"):  # the test compile's own log and aux files, generated just above
        if f.name != "main.tex":
            f.unlink()
    with tarfile.open(ROOT / "paper_arxiv.tar.gz", "w:gz") as t:
        for p in sorted(x for x in OUT.rglob("*") if x.is_file()):
            t.add(p, arcname=str(p.relative_to(OUT)))
    print(f"package: {len(used)} figures, {len(inputs)} TikZ inputs; preview paper_arxiv_preview.pdf")
