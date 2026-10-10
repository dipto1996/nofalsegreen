"""Build an anonymous snapshot of the repository for double-blind review: the tracked files at
HEAD (no git history), with the anonymised paper in place of the named one, identity strings
scrubbed from text files, and files that only serve the named release removed. Writes
paper_review_snapshot/ and paper_review_snapshot.tar.gz. Run scripts/build_anonymous.py first.
Then run the verifier inside the snapshot to confirm it still reproduces everything."""

from __future__ import annotations

import io
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper_review_snapshot"
DROP = ["CITATION.cff", "docs/paper2", "scripts/build_anonymous.py", "scripts/build_review_snapshot.py"]
SCRUB = [("roydiptopal1996@gmail.com", "anonymous@review.invalid"), ("dipto1996", "anonymous"),
         ("/Users/roydi", "/home/anonymous"), ("roydi", "anonymous"), ("Diptopal Roy", "Anonymous"),
         ("Diptopal", "Anonymous"), ("diptopal@joinsettle.info", "anonymous@review.invalid"),
         ("joinsettle", "anonymous"), ("Settle AI Inc.", "the author's company"),
         ("Settle AI's", "the author's company's"), ("Settle AI", "the author's company")]
# Study 15's corrected code-generation records hold the exact repair prompts sent to the models,
# whose hashes the input audit checks; two of those prompts contain a local path in an error
# message. They are left as recorded so the audit reproduces.
KEEP = ("docs/study15/codegen_cache_r2/",)

if __name__ == "__main__":
    if OUT.exists():
        shutil.move(str(OUT), str(ROOT / f".paper_review_snapshot_prev_{time.strftime('%Y%m%d%H%M%S')}"))
    data = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=ROOT, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        t.extractall(OUT)
    for d in DROP:
        p = OUT / d
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    anon = ROOT / "paper_anon"
    shutil.copy(anon / "PAPER_ANON.md", OUT / "docs" / "PAPER.md")
    shutil.copy(anon / "main.pdf", OUT / "docs" / "PAPER.pdf")
    shutil.copy(anon / "main.tex", OUT / "paper" / "main.tex")
    shutil.copy(anon / "main.pdf", OUT / "paper" / "main.pdf")
    changed = kept = 0
    for p in OUT.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(OUT))
        try:
            text = p.read_text()
        except (UnicodeDecodeError, ValueError):
            continue
        new = text
        for a, b in SCRUB:
            new = new.replace(a, b)
        if new != text:
            if rel.startswith(KEEP):
                kept += 1
                continue
            p.write_text(new)
            changed += 1
    with tarfile.open(ROOT / "paper_review_snapshot.tar.gz", "w:gz") as t:
        for p in sorted(x for x in OUT.rglob("*") if x.is_file()):
            t.add(p, arcname="snapshot/" + str(p.relative_to(OUT)))
    print(f"scrubbed {changed} files; left {kept} recorded model-input files unchanged")
