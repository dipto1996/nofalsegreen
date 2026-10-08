"""Write the development packets given to the parsing baseline's author: layouts L1-L3 only,
seeds disjoint from the test packets, with canonical records and labels. No API call."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study13 as S  # noqa: E402

OUT = ROOT / "data" / "study13" / "parser_dev"

if __name__ == "__main__":
    for wf in S.WORKFLOWS:
        for seed in S.PARSER_DEV_SEEDS:
            p = S.make_packet(wf, seed)
            S.write_canonical(p, OUT / "canonical" / wf / f"s{seed}")
            for layout in S.DEV_LAYOUTS:
                S.write_packet(p, layout, OUT / layout / wf / f"s{seed}")
            (OUT / "labels" / wf).mkdir(parents=True, exist_ok=True)
            (OUT / "labels" / wf / f"s{seed}.json").write_text(
                json.dumps({k: v.label for k, v in sorted(p.labels.items())}, indent=1))
    print("wrote", OUT)
