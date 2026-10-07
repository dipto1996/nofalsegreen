"""Cross-check Study 9 labels against the independently written checker, and verify
every certificate: each needs_evidence(unknown) label's two completions are written as
packets and must be judged pass and fail by labelcheck/contract_checker.py.
No API call. Writes docs/study9/label_verification.json."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "labelcheck"))

from contract_checker import check  # noqa: E402  (independent implementation)
from nofalsegreen import contracts as C  # noqa: E402
from nofalsegreen import study9  # noqa: E402


def write(tables, wf, d: Path):
    p = C.Packet("x", wf, tables, [], {}, {})
    C.write_canonical(p, d)


def main() -> int:
    out = {"labels": 0, "agree": 0, "disagreements": [], "certificates": 0, "certificates_verified": 0, "certificate_failures": []}
    tmp = Path(tempfile.mkdtemp())
    for part, seeds in (("A", study9.A_SEEDS), ("B", study9.B_SEEDS)):
        for wf in study9.WORKFLOWS:
            for s in seeds:
                p = study9.packet(part, wf, s)
                d = tmp / f"{part}-{wf}-{s}"
                write(p.tables, wf, d)
                ref = check(wf, str(d))
                for key, cert in p.labels.items():
                    out["labels"] += 1
                    if ref.get(key) == cert.label:
                        out["agree"] += 1
                    else:
                        out["disagreements"].append({"packet": f"{part}-{wf}-{s}", "pair": key, "ours": cert.label,
                                                     "checker": ref.get(key), "kind": cert.kind})
                    if cert.kind != "unknown":
                        continue
                    rule, e = key.split("::", 1)
                    c = C.CONTRACTS[rule]
                    for want, w in (("pass", cert.witness_pass), ("fail", cert.witness_fail)):
                        t = copy.deepcopy(p.tables)
                        for f in c.facts:
                            if C._resolve(f, p.tables, e)[0] != "unknown":
                                continue
                            v = w[f.name]
                            s0 = f.sources[0]
                            row = next((r for r in t[s0.table] if r.get(s0.key) == e), None)
                            if row is None:
                                row = {s0.key: e}
                                t[s0.table].append(row)
                            row[s0.column] = v.isoformat() if isinstance(v, date) else v
                        cd = tmp / f"cert-{part}-{wf}-{s}-{rule}-{e}-{want}"
                        write(t, wf, cd)
                        got = check(wf, str(cd)).get(key)
                        out["certificates"] += 1
                        if got == want:
                            out["certificates_verified"] += 1
                        else:
                            out["certificate_failures"].append({"pair": key, "want": want, "got": got})
    # Study 11 gap packets: labels must agree with the independent checker too
    for wf in study9.WORKFLOWS:
        for form in study9.GAP_FORMS:
            for s in study9.C_SEEDS:
                p = study9.gap_packet(wf, s, form)
                d = tmp / f"C-{wf}-{form}-{s}"
                write(p.tables, wf, d)
                ref = check(wf, str(d))
                for key, cert in p.labels.items():
                    out["labels"] += 1
                    if ref.get(key) == cert.label:
                        out["agree"] += 1
                    else:
                        out["disagreements"].append({"packet": f"C-{wf}-{form}-{s}", "pair": key, "ours": cert.label,
                                                     "checker": ref.get(key)})
    (ROOT / "docs" / "study9").mkdir(exist_ok=True)
    (ROOT / "docs" / "study9" / "label_verification.json").write_text(json.dumps(out, indent=1))
    print({k: (v if not isinstance(v, list) else len(v)) for k, v in out.items()})
    for x in out["disagreements"][:10]:
        print("DISAGREE", x)
    for x in out["certificate_failures"][:10]:
        print("CERT FAIL", x)
    return 0 if not out["disagreements"] and not out["certificate_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
