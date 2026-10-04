"""Compare generator labels with the independent reference checker.

labelcheck/reference_checker.py was written from the regulations by a separate
agent that never saw the generator code or any label (labelcheck/INTERPRETATIONS.md).
This script renders every generated firm used or audited in the paper, runs the
checker on it, and writes docs/labelcheck_results.json.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nofalsegreen import study2, study3  # noqa: E402
from nofalsegreen.generator import FirmGenerator  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firms = [("study2", f) for f in study2.load_firms(rb)]
    firms += [(f"study3_{a}", f) for a in study3.ARMS for f in study3.load_firms(rb, a)]
    gen = FirmGenerator(rb)
    for s in range(101, 111):
        d = ROOT / "data" / "labelcheck" / f"s{s}"
        f = gen.generate(s, d)
        firms.append(("audit_seeds", f))
    dirs = {group + "|" + f.firm_id: Path(next(iter(f.sources.values()))).parent
            if Path(next(iter(f.sources.values()))).is_absolute()
            else ROOT / "data" / "labelcheck" / f"s{f.provenance['seed']}" for group, f in firms}
    out = json.loads(subprocess.run(
        [sys.executable, str(ROOT / "labelcheck" / "reference_checker.py"), *map(str, dirs.values())],
        capture_output=True, text=True, check=True).stdout)
    by_dir = {str(Path(k).resolve()): v for k, v in out.items()}
    res, dis = Counter(), []
    for group, f in firms:
        ref = by_dir[str(dirs[group + "|" + f.firm_id].resolve())]
        for l in f.labels:
            ok = ref.get(l.pair_id) == l.verdict.value
            res[(group, ok)] += 1
            if not ok:
                dis.append({"firm": f.firm_id, "pair": l.pair_id, "label": l.verdict.value,
                            "reference": ref.get(l.pair_id)})
    doc = {"n_pairs": sum(res.values()), "n_agree": sum(v for (g, ok), v in res.items() if ok),
           "by_group": {g: {"agree": res[(g, True)], "n": res[(g, True)] + res[(g, False)]}
                        for g in sorted({g for g, _ in res})},
           "disagreements": dis}
    (ROOT / "docs" / "labelcheck_results.json").write_text(json.dumps(doc, indent=2))
    print(json.dumps({k: v for k, v in doc.items() if k != "disagreements"}, indent=1), len(dis), "disagreements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
